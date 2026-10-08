import os
import signal
import socket
import subprocess
import sys
from time import monotonic, sleep
from collections.abc import Iterator

import httpx
import jwt
import pytest
from datetime import UTC, datetime, timedelta

from tests.fixtures.identities import TEST_OWNER_ID

TEST_SIGNING_KEY = "test-only-signing-key-for-authentication-tests-0123456789abcdef"


class RunningApi:
    def __init__(
        self,
        database_url: str,
        schema_name: str,
        settings: dict[str, str] | None = None,
    ) -> None:
        self.database_url = database_url
        self.schema_name = schema_name
        self.settings = settings or {
            "JWT_SIGNING_KEY": TEST_SIGNING_KEY,
            "JWT_ISSUER": "task-manager-tests",
            "JWT_AUDIENCE": "task-manager-test-clients",
            "ENABLE_API_DOCS": "false",
        }
        with socket.socket() as port_probe:
            port_probe.bind(("127.0.0.1", 0))
            self.port = port_probe.getsockname()[1]
        self.client = httpx.Client(
            base_url=f"http://127.0.0.1:{self.port}", timeout=2.0
        )
        self.process: subprocess.Popen[bytes] | None = None
        self.start()

    def start(self) -> None:
        environment = os.environ.copy()
        environment["DATABASE_URL"] = self.database_url
        environment["DATABASE_SCHEMA"] = self.schema_name
        environment.update(self.settings)
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "task_manager.infrastructure.http.api:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = monotonic() + 10
        while monotonic() < deadline:
            if self.process.poll() is not None:
                pytest.fail("The isolated API process exited before becoming ready.")
            try:
                if self.client.get("/health").status_code == 200:
                    now: datetime = datetime.now(UTC)
                    test_token: str = jwt.encode(
                        {
                            "sub": str(TEST_OWNER_ID),
                            "iat": now,
                            "exp": now + timedelta(minutes=30),
                            "iss": self.settings["JWT_ISSUER"],
                            "aud": self.settings["JWT_AUDIENCE"],
                        },
                        self.settings["JWT_SIGNING_KEY"],
                        algorithm="HS256",
                    )
                    self.client.headers["Authorization"] = f"Bearer {test_token}"
                    return
            except httpx.HTTPError:
                sleep(0.05)
        self.stop()
        pytest.fail("The isolated API process did not become ready.")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def restart(self) -> None:
        self.stop()
        self.start()


@pytest.fixture
def api_server(postgres_schema: tuple[str, str]) -> Iterator[RunningApi]:
    test_database_url, schema_name = postgres_schema
    server = RunningApi(test_database_url, schema_name)
    try:
        yield server
    finally:
        server.stop()
        server.client.close()


@pytest.fixture
def api_client(api_server: RunningApi) -> httpx.Client:
    return api_server.client
