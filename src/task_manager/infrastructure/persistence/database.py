from collections.abc import Iterator
from contextlib import contextmanager
import os
import re

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from task_manager.application.ports import (
    TaskListStore,
    TaskQueryStore,
    TaskStore,
    UnitOfWork,
    UnitOfWorkFactory,
)
from task_manager.infrastructure.persistence.task_list_store import (
    SQLAlchemyTaskListStore,
)
from task_manager.infrastructure.persistence.task_query_store import (
    SQLAlchemyTaskQueryStore,
)
from task_manager.infrastructure.persistence.task_store import SQLAlchemyTaskStore

_SCHEMA_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = database_url or os.environ.get("DATABASE_URL", "")
    if not resolved_url.startswith("postgresql+psycopg://"):
        raise RuntimeError("DATABASE_URL must use the PostgreSQL psycopg driver.")
    return create_engine(resolved_url, pool_pre_ping=True)


class SQLAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.task_lists: TaskListStore = SQLAlchemyTaskListStore(session)
        self.tasks: TaskStore = SQLAlchemyTaskStore(session)
        self.task_queries: TaskQueryStore = SQLAlchemyTaskQueryStore(session)

    def commit(self) -> None:
        self._session.flush()
        self._session.commit()


def create_unit_of_work_factory(engine: Engine) -> UnitOfWorkFactory:
    @contextmanager
    def create_unit_of_work(read_only_snapshot: bool) -> Iterator[UnitOfWork]:
        isolation_level = "REPEATABLE READ" if read_only_snapshot else "READ COMMITTED"
        connection = engine.connect().execution_options(isolation_level=isolation_level)
        session = Session(bind=connection, expire_on_commit=False)
        try:
            schema = os.environ.get("DATABASE_SCHEMA")
            if schema:
                if not _SCHEMA_PATTERN.fullmatch(schema):
                    raise RuntimeError("DATABASE_SCHEMA is invalid.")
                session.execute(text(f'SET search_path TO "{schema}"'))
            if read_only_snapshot:
                session.execute(text("SET TRANSACTION READ ONLY"))
            yield SQLAlchemyUnitOfWork(session)
        finally:
            session.close()
            connection.close()

    return create_unit_of_work
