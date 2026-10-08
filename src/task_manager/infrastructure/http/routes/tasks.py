from uuid import UUID

from fastapi import APIRouter, Request, Response

from task_manager.application.commands import (
    CreateTask,
    UNSET,
    UpdateTask,
)
from task_manager.application.tasks.operations import (
    CreateTaskUseCase,
    DeleteTaskUseCase,
)
from task_manager.application.tasks.queries import GetTaskUseCase
from task_manager.application.tasks.update import UpdateTaskUseCase
from task_manager.infrastructure.http.support import (
    RESOURCE_RESPONSES,
    task_response,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import (
    validate_query,
)
from task_manager.infrastructure.http.schemas.task_requests import (
    CreateTaskRequest,
    UpdateTaskRequest,
)
from task_manager.infrastructure.http.schemas.task import (
    TaskResponse,
)

router = APIRouter(prefix="/api/v1/task-lists/{list_id}/tasks")


@router.post(
    "", response_model=TaskResponse, status_code=201, responses=RESOURCE_RESPONSES
)
def create_task(
    list_id: UUID, body: CreateTaskRequest, request: Request, response: Response
) -> TaskResponse:
    validate_query(request, set())
    task = CreateTaskUseCase(unit_of_work_factory(request)).execute(
        CreateTask(
            list_id=list_id,
            title=body.title,
            description=body.description,
            status=body.status,
            priority=body.priority,
        )
    )
    response.headers["Location"] = f"/api/v1/task-lists/{task.list_id}/tasks/{task.id}"
    return task_response(task)


@router.get("/{task_id}", response_model=TaskResponse, responses=RESOURCE_RESPONSES)
def get_task(list_id: UUID, task_id: UUID, request: Request) -> TaskResponse:
    validate_query(request, set())
    task = GetTaskUseCase(unit_of_work_factory(request)).execute(list_id, task_id)
    return task_response(task)


@router.patch("/{task_id}", response_model=TaskResponse, responses=RESOURCE_RESPONSES)
def update_task(
    list_id: UUID, task_id: UUID, body: UpdateTaskRequest, request: Request
) -> TaskResponse:
    validate_query(request, set())
    command = UpdateTask(
        title=body.title if "title" in body.model_fields_set else UNSET,
        description=(
            body.description if "description" in body.model_fields_set else UNSET
        ),
        status=body.status if "status" in body.model_fields_set else UNSET,
        priority=body.priority if "priority" in body.model_fields_set else UNSET,
    )
    task = UpdateTaskUseCase(unit_of_work_factory(request)).execute(
        list_id, task_id, command
    )
    return task_response(task)


@router.delete("/{task_id}", status_code=204, responses=RESOURCE_RESPONSES)
def delete_task(list_id: UUID, task_id: UUID, request: Request) -> Response:
    validate_query(request, set())
    DeleteTaskUseCase(unit_of_work_factory(request)).execute(list_id, task_id)
    return Response(status_code=204)
