from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

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
from task_manager.domain.user import User
from task_manager.domain.task import Task
from task_manager.infrastructure.http.security import get_current_user

router = APIRouter(prefix="/api/v1/task-lists/{list_id}/tasks")


@router.post(
    "", response_model=TaskResponse, status_code=201, responses=RESOURCE_RESPONSES
)
def create_task(
    list_id: UUID,
    body: CreateTaskRequest,
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    validate_query(request, set())
    task: Task = CreateTaskUseCase(unit_of_work_factory(request)).execute(
        CreateTask(
            list_id=list_id,
            title=body.title,
            description=body.description,
            status=body.status,
            priority=body.priority,
            assignee_id=body.assignee_id,
        ),
        current_user.id,
    )
    response.headers["Location"] = f"/api/v1/task-lists/{task.list_id}/tasks/{task.id}"
    return task_response(task)


@router.get("/{task_id}", response_model=TaskResponse, responses=RESOURCE_RESPONSES)
def get_task(
    list_id: UUID,
    task_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    validate_query(request, set())
    task: Task = GetTaskUseCase(unit_of_work_factory(request)).execute(
        list_id, task_id, current_user.id
    )
    return task_response(task)


@router.patch("/{task_id}", response_model=TaskResponse, responses=RESOURCE_RESPONSES)
def update_task(
    list_id: UUID,
    task_id: UUID,
    body: UpdateTaskRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> TaskResponse:
    validate_query(request, set())
    command: UpdateTask = UpdateTask(
        title=body.title if "title" in body.model_fields_set else UNSET,
        description=(
            body.description if "description" in body.model_fields_set else UNSET
        ),
        status=body.status if "status" in body.model_fields_set else UNSET,
        priority=body.priority if "priority" in body.model_fields_set else UNSET,
        assignee_id=(
            body.assignee_id if "assignee_id" in body.model_fields_set else UNSET
        ),
    )
    task: Task = UpdateTaskUseCase(unit_of_work_factory(request)).execute(
        list_id, task_id, current_user.id, command
    )
    return task_response(task)


@router.delete("/{task_id}", status_code=204, responses=RESOURCE_RESPONSES)
def delete_task(
    list_id: UUID,
    task_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    validate_query(request, set())
    DeleteTaskUseCase(unit_of_work_factory(request)).execute(
        list_id, task_id, current_user.id
    )
    return Response(status_code=204)
