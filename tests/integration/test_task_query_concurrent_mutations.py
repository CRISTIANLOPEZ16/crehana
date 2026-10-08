from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager

import pytest
from sqlalchemy import Engine

from task_manager.application.commands import (
    CreateTask,
    CreateTaskList,
    QueryTasks,
    UpdateTask,
)
from task_manager.application.ports import UnitOfWork
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.tasks.operations import (
    CreateTaskUseCase,
    DeleteTaskUseCase,
)
from task_manager.application.tasks.queries import QueryTasksUseCase
from task_manager.application.tasks.update import UpdateTaskUseCase
from task_manager.domain.task import TaskStatus
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.fixtures.identities import TEST_OWNER_ID

pytestmark = pytest.mark.integration


def test_query_snapshot_survives_concurrent_status_change_and_delete(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Changing snapshot", TEST_OWNER_ID)
    )
    pending_task = CreateTaskUseCase(factory).execute(
        CreateTask(task_list.id, "Pending", status=TaskStatus.PENDING), TEST_OWNER_ID
    )
    completed_task = CreateTaskUseCase(factory).execute(
        CreateTask(task_list.id, "Completed", status=TaskStatus.COMPLETED),
        TEST_OWNER_ID,
    )
    interleaved = False

    def interleaving_factory(
        read_only_snapshot: bool,
    ) -> AbstractContextManager[UnitOfWork]:
        @contextmanager
        def create_unit_of_work() -> Iterator[UnitOfWork]:
            nonlocal interleaved
            with factory(read_only_snapshot) as unit_of_work:
                if read_only_snapshot and not interleaved:
                    assert unit_of_work.task_lists.get(task_list.id) is not None
                    interleaved = True
                    UpdateTaskUseCase(factory).execute(
                        task_list.id,
                        pending_task.id,
                        TEST_OWNER_ID,
                        UpdateTask(status=TaskStatus.COMPLETED),
                    )
                    DeleteTaskUseCase(factory).execute(
                        task_list.id, completed_task.id, TEST_OWNER_ID
                    )
                yield unit_of_work

        return create_unit_of_work()

    first_snapshot = QueryTasksUseCase(interleaving_factory).execute(
        QueryTasks(task_list.id), TEST_OWNER_ID
    )
    assert first_snapshot.summary.total_tasks == 2
    assert first_snapshot.summary.completed_tasks == 1
    assert {task.id for task in first_snapshot.items} == {
        pending_task.id,
        completed_task.id,
    }

    next_snapshot = QueryTasksUseCase(factory).execute(
        QueryTasks(task_list.id), TEST_OWNER_ID
    )
    assert next_snapshot.summary.total_tasks == 1
    assert next_snapshot.summary.completed_tasks == 1
    assert [task.id for task in next_snapshot.items] == [pending_task.id]
