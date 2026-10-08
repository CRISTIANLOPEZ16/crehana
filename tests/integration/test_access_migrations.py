from datetime import UTC, datetime
import os
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import IntegrityError

from task_manager.application.accounts.bootstrap import BootstrapHistoricalOwnerUseCase
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory

pytestmark = pytest.mark.integration


class BootstrapPasswordService:
    def hash(self, password: str) -> str:
        return f"bootstrap-hash:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"bootstrap-hash:{password}"


def _upgrade(database_url: str, schema_name: str, revision: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    os.environ["DATABASE_SCHEMA"] = schema_name
    command.upgrade(Config("alembic.ini"), revision)


def test_fresh_schema_migrates_with_no_owner_mapping(
    postgres_schema: tuple[str, str],
) -> None:
    database_url, schema_name = postgres_schema
    engine: Engine = create_engine(
        database_url, connect_args={"options": f"-csearch_path={schema_name}"}
    )
    try:
        with engine.connect() as connection:
            tables: set[str] = set(
                connection.scalars(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema=:schema"
                    ),
                    {"schema": schema_name},
                )
            )
        assert {
            "users",
            "list_memberships",
            "invitations",
            "task_lists",
            "tasks",
        } <= tables
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "postgres_schema", ["0003_name_task_list_foreign_key"], indirect=True
)
def test_populated_upgrade_requires_explicit_owner_and_preserves_rows(
    postgres_schema: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url, schema_name = postgres_schema
    engine: Engine = create_engine(
        database_url, connect_args={"options": f"-csearch_path={schema_name}"}
    )
    task_list_id: UUID = uuid4()
    task_id: UUID = uuid4()
    created_at: datetime = datetime(2024, 1, 2, tzinfo=UTC)
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("DATABASE_SCHEMA", schema_name)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO task_lists "
                    "(id,name,description,created_at,updated_at) "
                    "VALUES (:id,'Historical list','Preserve me',:created,:updated)"
                ),
                {"id": task_list_id, "created": created_at, "updated": created_at},
            )
            connection.execute(
                text(
                    "INSERT INTO tasks "
                    "(id,list_id,title,description,status,priority,created_at,"
                    "updated_at) "
                    "VALUES (:id,:list_id,'Historical task',NULL,'completed','high',"
                    ":created,:updated)"
                ),
                {
                    "id": task_id,
                    "list_id": task_list_id,
                    "created": created_at,
                    "updated": created_at,
                },
            )
        _upgrade(database_url, schema_name, "0004_access_schema")
        with pytest.raises(RuntimeError, match="offline owner bootstrap"):
            _upgrade(database_url, schema_name, "head")
        with engine.connect() as connection:
            current_revision: str | None = connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            assert current_revision == "0004_access_schema"
            ownerless_count: int = connection.scalar(
                text("SELECT count(*) FROM task_lists WHERE owner_id IS NULL")
            )
            assert ownerless_count == 1

        owner = BootstrapHistoricalOwnerUseCase(
            create_unit_of_work_factory(engine), BootstrapPasswordService()
        ).execute(
            "historical@example.com",
            "Historical owner",
            "a secure bootstrap passphrase",
        )
        owner_id: UUID = owner.id
        _upgrade(database_url, schema_name, "head")
        with engine.connect() as connection:
            saved_list = connection.execute(
                text(
                    "SELECT owner_id,name,description,created_at,updated_at "
                    "FROM task_lists WHERE id=:id"
                ),
                {"id": task_list_id},
            ).one()
            saved_task = connection.execute(
                text(
                    "SELECT id,list_id,title,status,priority,assignee_id,created_at "
                    "FROM tasks WHERE id=:id"
                ),
                {"id": task_id},
            ).one()
            assert saved_list == (
                owner_id,
                "Historical list",
                "Preserve me",
                created_at,
                created_at,
            )
            assert saved_task == (
                task_id,
                task_list_id,
                "Historical task",
                "completed",
                "high",
                None,
                created_at,
            )
            with pytest.raises(IntegrityError):
                with engine.begin() as invalid_owner_transaction:
                    invalid_owner_transaction.execute(
                        text("UPDATE task_lists SET owner_id=NULL WHERE id=:id"),
                        {"id": task_list_id},
                    )
    finally:
        engine.dispose()
