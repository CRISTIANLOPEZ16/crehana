from collections.abc import Iterator
import os
import re
import subprocess
import sys
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import Engine, create_engine, text

from tests.fixtures.identities import TEST_OWNER_ID


@pytest.fixture
def postgres_schema(request: pytest.FixtureRequest) -> Iterator[tuple[str, str]]:
    test_database_url = os.environ.get("TEST_DATABASE_URL", "")
    if not test_database_url.startswith("postgresql+psycopg://"):
        pytest.skip("TEST_DATABASE_URL must point to the dedicated PostgreSQL test DB.")
    development_database_url = os.environ.get("DATABASE_URL", "")
    test_url = urlsplit(test_database_url)
    development_url = urlsplit(development_database_url)
    if test_url[:2] == development_url[:2] and test_url.path == development_url.path:
        pytest.fail("Integration tests must not target the development database.")

    schema_name = f"test_{uuid4().hex}"
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema_name):
        pytest.fail("Generated test schema name is invalid.")
    admin_engine = create_engine(test_database_url)
    try:
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))

        environment = os.environ.copy()
        environment["DATABASE_URL"] = test_database_url
        environment["DATABASE_SCHEMA"] = schema_name
        requested_revision: object = getattr(request, "param", "head")
        if not isinstance(requested_revision, str):
            pytest.fail("The requested Alembic revision must be a string.")
        target_revision: str = requested_revision
        migration_result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", target_revision],
            check=True,
            env=environment,
            capture_output=True,
            text=True,
        )
        with admin_engine.connect() as connection:
            table_names = list(
                connection.scalars(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = :schema_name"
                    ),
                    {"schema_name": schema_name},
                )
            )
        if "task_lists" not in table_names or "tasks" not in table_names:
            pytest.fail(
                f"Migrations did not create test schema {schema_name}: {table_names}; "
                f"migration output: {migration_result.stdout} "
                f"{migration_result.stderr}"
            )
        if "users" in table_names:
            with admin_engine.begin() as connection:
                connection.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))
                connection.execute(
                    text(
                        "INSERT INTO users "
                        "(id,display_name,email,password_hash,created_at,updated_at) "
                        "VALUES (:id,'Test owner','owner@example.test','test-hash',"
                        "now(),now())"
                    ),
                    {"id": TEST_OWNER_ID},
                )
        yield test_database_url, schema_name
    finally:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def postgres_engine(postgres_schema: tuple[str, str]) -> Iterator[Engine]:
    test_database_url, schema_name = postgres_schema
    engine = create_engine(
        test_database_url,
        connect_args={"options": f"-csearch_path={schema_name}"},
        pool_pre_ping=True,
    )
    try:
        yield engine
    finally:
        engine.dispose()
