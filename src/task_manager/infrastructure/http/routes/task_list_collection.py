from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from task_manager.application.commands import CreateTaskList, ListTaskLists
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.task_lists.queries import ListTaskListsUseCase
from task_manager.application.ports import TaskListPage
from task_manager.infrastructure.http.support import (
    VALIDATION_RESPONSES,
    task_list_response,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import validate_query
from task_manager.infrastructure.http.schemas.task_list import (
    CreateTaskListRequest,
    TaskListPageResponse,
    TaskListResponse,
)
from task_manager.infrastructure.http.security import get_current_user
from task_manager.domain.user import User
from task_manager.domain.task_list import TaskList

router = APIRouter(prefix="/api/v1/task-lists", responses=VALIDATION_RESPONSES)


@router.post("", response_model=TaskListResponse, status_code=201)
def create_task_list(
    body: CreateTaskListRequest,
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskListResponse:
    validate_query(request, set())
    task_list: TaskList = CreateTaskListUseCase(unit_of_work_factory(request)).execute(
        CreateTaskList(
            name=body.name, owner_id=current_user.id, description=body.description
        )
    )
    response.headers["Location"] = f"/api/v1/task-lists/{task_list.id}"
    return task_list_response(task_list)


@router.get("", response_model=TaskListPageResponse)
def list_task_lists(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListPageResponse:
    validate_query(request, {"limit", "offset"})
    page: TaskListPage = ListTaskListsUseCase(unit_of_work_factory(request)).execute(
        ListTaskLists(limit=limit, offset=offset), current_user.id
    )
    return TaskListPageResponse(
        items=[task_list_response(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
