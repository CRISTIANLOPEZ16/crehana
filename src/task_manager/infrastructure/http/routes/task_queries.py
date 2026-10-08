from uuid import UUID

from fastapi import APIRouter, Request

from task_manager.application.commands import QueryTasks
from task_manager.application.errors import InvalidRequest
from task_manager.application.tasks.queries import QueryTasksUseCase
from task_manager.domain.errors import FieldViolation
from task_manager.domain.task import TaskPriority, TaskStatus
from task_manager.infrastructure.http.support import (
    RESOURCE_RESPONSES,
    task_response,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import pagination_query, validate_query
from task_manager.infrastructure.http.schemas.common import TaskQuery
from task_manager.infrastructure.http.schemas.task import (
    CompletionSummaryResponse,
    TaskPageResponse,
)

router = APIRouter(prefix="/api/v1/task-lists/{list_id}/tasks")


@router.get("", response_model=TaskPageResponse, responses=RESOURCE_RESPONSES)
def query_tasks(list_id: UUID, request: Request) -> TaskPageResponse:
    values = validate_query(request, {"status", "priority", "limit", "offset"})
    pagination = pagination_query(values)
    task_query = TaskQuery(limit=pagination.limit, offset=pagination.offset)
    try:
        status = TaskStatus(values["status"]) if "status" in values else None
    except ValueError as exception:
        raise InvalidRequest(
            [FieldViolation("query.status", "Unsupported status value.")]
        ) from exception
    try:
        priority = TaskPriority(values["priority"]) if "priority" in values else None
    except ValueError as exception:
        raise InvalidRequest(
            [FieldViolation("query.priority", "Unsupported priority value.")]
        ) from exception
    page = QueryTasksUseCase(unit_of_work_factory(request)).execute(
        QueryTasks(
            list_id=list_id,
            status=status,
            priority=priority,
            limit=task_query.limit,
            offset=task_query.offset,
        )
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
