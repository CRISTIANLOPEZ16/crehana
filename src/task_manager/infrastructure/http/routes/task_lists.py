from uuid import UUID

from fastapi import APIRouter, Request, Response

from task_manager.application.commands import (
    UNSET,
    UpdateTaskList,
)
from task_manager.application.task_lists.operations import (
    DeleteTaskListUseCase,
    UpdateTaskListUseCase,
)
from task_manager.application.task_lists.queries import GetTaskListUseCase
from task_manager.infrastructure.http.support import (
    RESOURCE_RESPONSES,
    task_list_response,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import validate_query
from task_manager.infrastructure.http.schemas.task_list import (
    TaskListResponse,
    UpdateTaskListRequest,
)

router = APIRouter(prefix="/api/v1/task-lists")


@router.get("/{list_id}", response_model=TaskListResponse, responses=RESOURCE_RESPONSES)
def get_task_list(list_id: UUID, request: Request) -> TaskListResponse:
    validate_query(request, set())
    task_list = GetTaskListUseCase(unit_of_work_factory(request)).execute(list_id)
    return task_list_response(task_list)


@router.patch(
    "/{list_id}",
    response_model=TaskListResponse,
    responses=RESOURCE_RESPONSES,
)
def update_task_list(
    list_id: UUID, body: UpdateTaskListRequest, request: Request
) -> TaskListResponse:
    validate_query(request, set())
    command = UpdateTaskList(
        name=body.name if "name" in body.model_fields_set else UNSET,
        description=(
            body.description if "description" in body.model_fields_set else UNSET
        ),
    )
    task_list = UpdateTaskListUseCase(unit_of_work_factory(request)).execute(
        list_id, command
    )
    return task_list_response(task_list)


@router.delete("/{list_id}", status_code=204, responses=RESOURCE_RESPONSES)
def delete_task_list(list_id: UUID, request: Request) -> Response:
    validate_query(request, set())
    DeleteTaskListUseCase(unit_of_work_factory(request)).execute(list_id)
    return Response(status_code=204)
