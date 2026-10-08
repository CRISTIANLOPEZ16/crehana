from threading import Lock
from typing import Any, cast

from fastapi import Request
from fastapi.responses import JSONResponse
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
}
RESOURCE_RESPONSES: dict[int | str, dict[str, Any]] = {
    **VALIDATION_RESPONSES,
    404: {"model": ErrorResponse},
}


def error_response(code: str, message: str, details: list[ErrorDetail]) -> JSONResponse:
    body = ErrorResponse(code=code, message=message, details=details)
    status_code = {
        "validation_error": 422,
        "resource_not_found": 404,
    }.get(code, 500)
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def unit_of_work_factory(request: Request) -> UnitOfWorkFactory:
    factory = request.app.state.unit_of_work_factory
    if factory is None:
        with cast(Lock, request.app.state.engine_lock):
            factory = request.app.state.unit_of_work_factory
            if factory is None:
                engine = create_database_engine()
                factory = create_unit_of_work_factory(engine)
                request.app.state.database_engine = engine
                request.app.state.unit_of_work_factory = factory
    return cast(UnitOfWorkFactory, factory)


def task_list_response(task_list: TaskList) -> TaskListResponse:
    return TaskListResponse(
        id=task_list.id,
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
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
