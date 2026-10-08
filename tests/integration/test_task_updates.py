from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from sqlalchemy import Engine, text

from task_manager.application.commands import CreateTask, CreateTaskList, UpdateTask
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.tasks.operations import CreateTaskUseCase
from task_manager.application.tasks.queries import GetTaskUseCase
from task_manager.application.tasks.update import UpdateTaskUseCase
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.integration.concurrency_support import wait_for_database_lock

pytestmark = pytest.mark.integration


def test_concurrent_task_updates_preserve_unrelated_fields(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(CreateTaskList("Parent"))
    task = CreateTaskUseCase(factory).execute(
        CreateTask(task_list.id, "Before", "Before description")
    )
    start_together = Barrier(3)

    def update_title() -> None:
        start_together.wait(timeout=5)
        UpdateTaskUseCase(factory).execute(
            task_list.id, task.id, UpdateTask(title="After")
        )

    def update_description() -> None:
        start_together.wait(timeout=5)
        UpdateTaskUseCase(factory).execute(
            task_list.id, task.id, UpdateTask(description="After description")
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        title_update = executor.submit(update_title)
        description_update = executor.submit(update_description)
        start_together.wait(timeout=5)
        title_update.result(timeout=10)
        description_update.result(timeout=10)

    retrieved = GetTaskUseCase(factory).execute(task_list.id, task.id)
    assert retrieved.title == "After"
    assert retrieved.description == "After description"


def test_supplied_task_value_wins_after_waiting_for_row_lock(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(CreateTaskList("Parent"))
    task = CreateTaskUseCase(factory).execute(
        CreateTask(task_list.id, "Original", "Keep")
    )
    connection = postgres_engine.connect()
    transaction = connection.begin()
    connection.execute(
        text("SELECT id FROM tasks WHERE id=:task_id FOR UPDATE"),
        {"task_id": task.id},
    )
    connection.execute(
        text("UPDATE tasks SET title='Concurrent' WHERE id=:task_id"),
        {"task_id": task.id},
    )
    worker_started = Event()

    def apply_explicit_value() -> None:
        worker_started.set()
        UpdateTaskUseCase(factory).execute(
            task_list.id, task.id, UpdateTask(title="Original")
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            update_future = executor.submit(apply_explicit_value)
            assert worker_started.wait(timeout=5)
            assert wait_for_database_lock(postgres_engine, "tasks")
            transaction.commit()
            update_future.result(timeout=5)
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()

    retrieved = GetTaskUseCase(factory).execute(task_list.id, task.id)
    assert retrieved.title == "Original"
    assert retrieved.description == "Keep"
