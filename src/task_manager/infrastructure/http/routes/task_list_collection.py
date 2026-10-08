from fastapi import APIRouter, Request, Response

from task_manager.application.commands import CreateTaskList, ListTaskLists
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.task_lists.queries import ListTaskListsUseCase
from task_manager.infrastructure.http.support import (
    VALIDATION_RESPONSES,
    task_list_response,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import pagination_query, validate_query
from task_manager.infrastructure.http.schemas.task_list import (
    CreateTaskListRequest,
    TaskListPageResponse,
    TaskListResponse,
)

router = APIRouter(prefix="/api/v1/task-lists", responses=VALIDATION_RESPONSES)


@router.post("", response_model=TaskListResponse, status_code=201)
def create_task_list(
    body: CreateTaskListRequest, request: Request, response: Response
) -> TaskListResponse:
    validate_query(request, set())
    task_list = CreateTaskListUseCase(unit_of_work_factory(request)).execute(
        CreateTaskList(name=body.name, description=body.description)
    )
    response.headers["Location"] = f"/api/v1/task-lists/{task_list.id}"
    return task_list_response(task_list)


@router.get("", response_model=TaskListPageResponse)
def list_task_lists(request: Request) -> TaskListPageResponse:
    values = validate_query(request, {"limit", "offset"})
    query = pagination_query(values)
    page = ListTaskListsUseCase(unit_of_work_factory(request)).execute(
        ListTaskLists(limit=query.limit, offset=query.offset)
    )
    return TaskListPageResponse(
        items=[task_list_response(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
