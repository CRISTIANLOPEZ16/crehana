from logging.config import fileConfig
import os
import re

from alembic import context
from sqlalchemy import Engine, create_engine, pool

from task_manager.infrastructure.persistence import task_list_record, task_record
from task_manager.infrastructure.persistence import user_record, membership_record
from task_manager.infrastructure.persistence import invitation_record
from task_manager.infrastructure.persistence.base import Base

config = context.config
url: str | None = os.environ.get("DATABASE_URL")
if not url or not url.startswith("postgresql+psycopg://"):
    raise RuntimeError("DATABASE_URL must use the PostgreSQL psycopg driver.")
config.set_main_option("sqlalchemy.url", url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
_ = (
    task_list_record.TaskListRecord,
    task_record.TaskRecord,
    user_record.UserRecord,
    membership_record.MembershipRecord,
    invitation_record.InvitationRecord,
)
schema: str | None = os.environ.get("DATABASE_SCHEMA")
if schema and not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
    raise RuntimeError("DATABASE_SCHEMA is invalid.")


def run_migrations_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table_schema=schema,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    if url is None:
        raise RuntimeError("DATABASE_URL is required.")
    connect_args: dict[str, str] = (
        {"options": f"-csearch_path={schema}"} if schema else {}
    )
    connectable: Engine = create_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
