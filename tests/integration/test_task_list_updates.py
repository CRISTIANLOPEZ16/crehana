from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event

import pytest
from sqlalchemy import Engine, text

from task_manager.application.commands import CreateTaskList, UpdateTaskList
from task_manager.application.task_lists.operations import (
    CreateTaskListUseCase,
    UpdateTaskListUseCase,
)
from task_manager.application.task_lists.queries import GetTaskListUseCase
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.integration.concurrency_support import wait_for_database_lock

pytestmark = pytest.mark.integration


def test_concurrent_list_updates_preserve_unrelated_fields(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Before", "Before description")
    )
    start_together = Barrier(3)

    def update_name() -> None:
        start_together.wait(timeout=5)
        UpdateTaskListUseCase(factory).execute(
            task_list.id, UpdateTaskList(name="After")
        )

    def update_description() -> None:
        start_together.wait(timeout=5)
        UpdateTaskListUseCase(factory).execute(
            task_list.id, UpdateTaskList(description="After description")
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        name_update = executor.submit(update_name)
        description_update = executor.submit(update_description)
        start_together.wait(timeout=5)
        name_update.result(timeout=10)
        description_update.result(timeout=10)

    retrieved = GetTaskListUseCase(factory).execute(task_list.id)
    assert retrieved.name == "After"
    assert retrieved.description == "After description"


def test_supplied_unchanged_value_wins_after_waiting_for_row_lock(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(CreateTaskList("Original"))
    connection = postgres_engine.connect()
    transaction = connection.begin()
    connection.execute(
        text("SELECT id FROM task_lists WHERE id=:list_id FOR UPDATE"),
        {"list_id": task_list.id},
    )
    connection.execute(
        text("UPDATE task_lists SET name='Concurrent' WHERE id=:list_id"),
        {"list_id": task_list.id},
    )
    worker_started = Event()

    def apply_explicit_value() -> None:
        worker_started.set()
        UpdateTaskListUseCase(factory).execute(
            task_list.id, UpdateTaskList(name="Original")
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            update_future = executor.submit(apply_explicit_value)
            assert worker_started.wait(timeout=5)
            assert wait_for_database_lock(postgres_engine, "task_lists")
            transaction.commit()
            update_future.result(timeout=5)
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()

    assert GetTaskListUseCase(factory).execute(task_list.id).name == "Original"
