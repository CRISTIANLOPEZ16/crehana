from contextlib import AbstractContextManager, nullcontext
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from task_manager.application.commands import QueryTasks
from task_manager.application.ports import (
    CompletionSummary,
    TaskPage,
    TaskQueryStore,
    UnitOfWork,
)
from task_manager.application.tasks.queries import QueryTasksUseCase
from task_manager.domain.task import TaskPriority, TaskStatus

pytestmark = pytest.mark.unit


def test_query_use_case_delegates_filters_pagination_and_summary() -> None:
    list_id = uuid4()
    expected_page = TaskPage(
        items=[],
        matched_tasks=1,
        limit=3,
        offset=1,
        summary=CompletionSummary(32, 1, Decimal("3.13")),
    )
    task_query_store = Mock(spec=TaskQueryStore)
    task_query_store.query.return_value = expected_page
    unit_of_work = Mock(spec=UnitOfWork)
    unit_of_work.task_queries = task_query_store
    memberships = Mock()
    memberships.has_access.return_value = True
    unit_of_work.memberships = memberships
    snapshot_values: list[bool] = []

    def unit_of_work_factory(
        read_only_snapshot: bool,
    ) -> AbstractContextManager[UnitOfWork]:
        snapshot_values.append(read_only_snapshot)
        return nullcontext(unit_of_work)

    result = QueryTasksUseCase(unit_of_work_factory).execute(
        QueryTasks(
            list_id,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.HIGH,
            limit=3,
            offset=1,
        ),
        uuid4(),
    )

    assert result is expected_page
    assert snapshot_values == [True]
    task_query_store.query.assert_called_once_with(list_id, "completed", "high", 3, 1)
