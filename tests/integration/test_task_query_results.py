from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text

from task_manager.application.commands import CreateTask, CreateTaskList, QueryTasks
from task_manager.application.errors import ResourceNotFound
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.tasks.operations import CreateTaskUseCase
from task_manager.application.tasks.queries import QueryTasksUseCase
from task_manager.domain.task import TaskPriority, TaskStatus
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory

pytestmark = pytest.mark.integration


def test_filters_apply_before_pagination_and_summary_is_unfiltered(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(CreateTaskList("Query list"))
    values = (
        ("Done A", TaskStatus.COMPLETED, TaskPriority.HIGH),
        ("Done B", TaskStatus.COMPLETED, TaskPriority.HIGH),
        ("Pending high", TaskStatus.PENDING, TaskPriority.HIGH),
        ("Active low", TaskStatus.IN_PROGRESS, TaskPriority.LOW),
    )
    tasks = [
        CreateTaskUseCase(factory).execute(
            CreateTask(task_list.id, title, status=status, priority=priority)
        )
        for title, status, priority in values
    ]
    tied_timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE tasks SET created_at=:created_at, updated_at=:updated_at "
                "WHERE list_id=:list_id"
            ),
            {
                "created_at": tied_timestamp,
                "updated_at": tied_timestamp,
                "list_id": task_list.id,
            },
        )

    page = QueryTasksUseCase(factory).execute(
        QueryTasks(
            task_list.id,
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH,
            limit=1,
        )
    )
    assert page.matched_tasks == 1
    assert [task.title for task in page.items] == ["Pending high"]
    assert page.summary.total_tasks == 4
    assert page.summary.completed_tasks == 2
    assert page.summary.completion_percentage == 50

    ordered_page = QueryTasksUseCase(factory).execute(QueryTasks(task_list.id, limit=4))
    assert [task.id for task in ordered_page.items] == sorted(task.id for task in tasks)
    beyond_page = QueryTasksUseCase(factory).execute(
        QueryTasks(task_list.id, offset=20)
    )
    assert beyond_page.items == []
    assert beyond_page.matched_tasks == 4
    assert beyond_page.summary.total_tasks == 4


def test_empty_list_summary_and_missing_list_failure(postgres_engine: Engine) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(CreateTaskList("No tasks"))
    page = QueryTasksUseCase(factory).execute(QueryTasks(task_list.id))

    assert page.items == []
    assert page.matched_tasks == 0
    assert page.summary.total_tasks == 0
    assert page.summary.completed_tasks == 0
    assert page.summary.completion_percentage == 0
    with pytest.raises(ResourceNotFound):
        QueryTasksUseCase(factory).execute(QueryTasks(uuid4()))
