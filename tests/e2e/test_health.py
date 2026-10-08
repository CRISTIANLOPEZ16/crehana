import os
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

import pytest


@pytest.mark.e2e
def test_health_through_running_uvicorn_process() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    environment.pop("DATABASE_URL", None)
    environment.pop("DATABASE_SCHEMA", None)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "task_manager.infrastructure.http.api:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail("Uvicorn exited before becoming ready.")
            try:
                with urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=0.5
                ) as response:
                    assert response.status == 200
                    assert response.read() == b'{"status":"ok"}'
                    return
            except (OSError, URLError):
                time.sleep(0.05)
        pytest.fail("Uvicorn did not become ready before the deadline.")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
