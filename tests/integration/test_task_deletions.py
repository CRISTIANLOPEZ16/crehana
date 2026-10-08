from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import Engine, event, inspect, text
from sqlalchemy.orm import Session

from task_manager.application.commands import CreateTask, CreateTaskList
from task_manager.application.errors import ResourceNotFound
from task_manager.application.task_lists.operations import (
    CreateTaskListUseCase,
    DeleteTaskListUseCase,
)
from task_manager.application.task_lists.queries import GetTaskListUseCase
from task_manager.application.tasks.operations import (
    CreateTaskUseCase,
)
from task_manager.application.tasks.queries import GetTaskUseCase
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.integration.concurrency_support import wait_for_database_lock

pytestmark = pytest.mark.integration


def test_task_table_has_named_cascading_list_foreign_key(
    postgres_engine: Engine,
) -> None:
    foreign_keys = inspect(postgres_engine).get_foreign_keys("tasks")

    assert foreign_keys == [
        {
            "name": "fk_tasks_list_id_task_lists",
            "constrained_columns": ["list_id"],
            "referred_schema": None,
            "referred_table": "task_lists",
            "referred_columns": ["id"],
            "options": {"ondelete": "CASCADE"},
            "comment": None,
        }
    ]


def test_parent_delete_serializes_with_task_creation(postgres_engine: Engine) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(CreateTaskList("Parent"))
    connection = postgres_engine.connect()
    transaction = connection.begin()
    connection.execute(
        text("SELECT id FROM task_lists WHERE id=:list_id FOR UPDATE"),
        {"list_id": task_list.id},
    )
    worker_started = Event()

    def create_child() -> None:
        worker_started.set()
        CreateTaskUseCase(factory).execute(CreateTask(task_list.id, "Child"))

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            creation_future = executor.submit(create_child)
            assert worker_started.wait(timeout=5)
            assert wait_for_database_lock(postgres_engine, "task_lists")
            connection.execute(
                text("DELETE FROM task_lists WHERE id=:list_id"),
                {"list_id": task_list.id},
            )
            transaction.commit()
            with pytest.raises(ResourceNotFound):
                creation_future.result(timeout=5)
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()

    with postgres_engine.connect() as database_connection:
        assert database_connection.scalar(text("SELECT count(*) FROM tasks")) == 0


def test_cascade_delete_rolls_back_when_commit_fails(postgres_engine: Engine) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(CreateTaskList("Parent"))
    task = CreateTaskUseCase(factory).execute(CreateTask(task_list.id, "Child"))

    def reject_commit(session: Session) -> None:
        raise RuntimeError("Injected pre-commit failure.")

    event.listen(Session, "before_commit", reject_commit)
    try:
        with pytest.raises(RuntimeError, match="Injected pre-commit failure"):
            DeleteTaskListUseCase(factory).execute(task_list.id)
    finally:
        event.remove(Session, "before_commit", reject_commit)

    assert GetTaskListUseCase(factory).execute(task_list.id).id == task_list.id
    assert GetTaskUseCase(factory).execute(task_list.id, task.id).id == task.id
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tasks")) == 1
