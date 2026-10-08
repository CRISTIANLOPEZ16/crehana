from threading import Lock
from typing import Any, cast

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import Engine
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.task import Task
from task_manager.domain.task_list import TaskList
from task_manager.infrastructure.persistence.database import (
    create_database_engine,
    create_unit_of_work_factory,
)
from task_manager.infrastructure.http.schemas.common import (
    ErrorDetail,
    ErrorResponse,
)
from task_manager.infrastructure.http.schemas.task_list import TaskListResponse
from task_manager.infrastructure.http.schemas.task import (
    TaskResponse,
)

# FastAPI's OpenAPI extension point requires Any-valued response metadata.
VALIDATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
}
RESOURCE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **VALIDATION_RESPONSES,
    404: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
}


def error_response(
    code: str,
    message: str,
    details: list[ErrorDetail],
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: ErrorResponse = ErrorResponse(code=code, message=message, details=details)
    status_code: int = {
        "validation_error": 422,
        "resource_not_found": 404,
        "resource_forbidden": 403,
        "resource_conflict": 409,
        "authentication_failed": 401,
    }.get(code, 500)
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=headers,
    )


def unit_of_work_factory(request: Request) -> UnitOfWorkFactory:
    factory: UnitOfWorkFactory | None = request.app.state.unit_of_work_factory
    if factory is None:
        with cast(Lock, request.app.state.engine_lock):
            factory = request.app.state.unit_of_work_factory
            if factory is None:
                engine: Engine = create_database_engine()
                factory = create_unit_of_work_factory(engine)
                request.app.state.database_engine = engine
                request.app.state.unit_of_work_factory = factory
    return cast(UnitOfWorkFactory, factory)


def task_list_response(task_list: TaskList) -> TaskListResponse:
    return TaskListResponse(
        id=task_list.id,
        owner_id=task_list.owner_id,
        name=task_list.name,
        description=task_list.description,
        created_at=task_list.created_at,
        updated_at=task_list.updated_at,
    )


def task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        list_id=task.list_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        assignee_id=task.assignee_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
