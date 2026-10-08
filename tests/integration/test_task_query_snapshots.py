from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text

from task_manager.application.commands import (
    CreateTask,
    CreateTaskList,
    QueryTasks,
)
from task_manager.application.ports import UnitOfWork
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.tasks.operations import CreateTaskUseCase
from task_manager.application.tasks.queries import QueryTasksUseCase
from task_manager.domain.task import TaskStatus
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory

pytestmark = pytest.mark.integration


def test_collection_read_uses_one_repeatable_read_snapshot(
    postgres_engine: Engine,
) -> None:
    regular_factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(regular_factory).execute(
        CreateTaskList("Snapshot")
    )
    CreateTaskUseCase(regular_factory).execute(
        CreateTask(task_list.id, "Before snapshot", status=TaskStatus.PENDING)
    )
    inserted_during_read = False

    def interleaving_factory(
        read_only_snapshot: bool,
    ) -> AbstractContextManager[UnitOfWork]:
        @contextmanager
        def create_unit_of_work() -> Iterator[UnitOfWork]:
            nonlocal inserted_during_read
            with regular_factory(read_only_snapshot) as unit_of_work:
                if read_only_snapshot and not inserted_during_read:
                    assert unit_of_work.task_lists.get(task_list.id) is not None
                    inserted_during_read = True
                    created_at = datetime.now(UTC)
                    with postgres_engine.begin() as connection:
                        connection.execute(
                            text(
                                "INSERT INTO tasks "
                                "(id, list_id, title, description, status, priority, "
                                "created_at, updated_at) VALUES "
                                "(:id, :list_id, :title, NULL, 'completed', 'high', "
                                ":created_at, :updated_at)"
                            ),
                            {
                                "id": uuid4(),
                                "list_id": task_list.id,
                                "title": "Committed during read",
                                "created_at": created_at,
                                "updated_at": created_at,
                            },
                        )
                yield unit_of_work

        return create_unit_of_work()

    query = QueryTasksUseCase(interleaving_factory)
    first_snapshot = query.execute(QueryTasks(task_list.id))
    assert first_snapshot.summary.total_tasks == 1
    assert first_snapshot.summary.completed_tasks == 0

    next_snapshot = QueryTasksUseCase(regular_factory).execute(QueryTasks(task_list.id))
    assert next_snapshot.summary.total_tasks == 2
    assert next_snapshot.summary.completed_tasks == 1
