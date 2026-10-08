from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from task_manager.application.commands import QueryTasks
from task_manager.application.tasks.queries import QueryTasksUseCase
from task_manager.application.ports import TaskPage
from task_manager.domain.task import TaskPriority, TaskStatus
from task_manager.infrastructure.http.support import (
    RESOURCE_RESPONSES,
    task_response,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import validate_query
from task_manager.infrastructure.http.schemas.common import TaskQuery
from task_manager.infrastructure.http.schemas.task import (
    CompletionSummaryResponse,
    TaskPageResponse,
)
from task_manager.domain.user import User
from task_manager.infrastructure.http.security import get_current_user

router = APIRouter(prefix="/api/v1/task-lists/{list_id}/tasks")


@router.get("", response_model=TaskPageResponse, responses=RESOURCE_RESPONSES)
def query_tasks(
    list_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskPageResponse:
    validate_query(request, {"status", "priority", "limit", "offset"})
    task_query: TaskQuery = TaskQuery(limit=limit, offset=offset)
    page: TaskPage = QueryTasksUseCase(unit_of_work_factory(request)).execute(
        QueryTasks(
            list_id=list_id,
            status=status,
            priority=priority,
            limit=task_query.limit,
            offset=task_query.offset,
        ),
        current_user.id,
    )
    return TaskPageResponse(
        items=[task_response(task) for task in page.items],
        limit=page.limit,
        offset=page.offset,
        matched_tasks=page.matched_tasks,
        summary=CompletionSummaryResponse(
            total_tasks=page.summary.total_tasks,
            completed_tasks=page.summary.completed_tasks,
            completion_percentage=page.summary.completion_percentage,
        ),
    )
