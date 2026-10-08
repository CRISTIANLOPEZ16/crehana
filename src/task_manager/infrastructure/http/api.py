from threading import Lock

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from task_manager.application.errors import InvalidRequest, ResourceNotFound
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from task_manager.infrastructure.http.support import error_response
from task_manager.infrastructure.http.schemas.common import ErrorDetail, HealthResponse
from task_manager.infrastructure.http.routes.task_list_collection import (
    router as task_list_collection_router,
)
from task_manager.infrastructure.http.routes.task_lists import (
    router as task_list_router,
)
from task_manager.infrastructure.http.routes.task_queries import (
    router as task_query_router,
)
from task_manager.infrastructure.http.routes.tasks import router as task_router


def _request_violations(exception: RequestValidationError) -> list[ErrorDetail]:
    return [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"]),
            message="Invalid value.",
        )
        for error in exception.errors()
    ]


def create_app(database_engine: Engine | None = None) -> FastAPI:
    application = FastAPI(title="Task Manager API", version="1.0.0")
    application.state.database_engine = database_engine
    application.state.unit_of_work_factory = (
        create_unit_of_work_factory(database_engine) if database_engine else None
    )
    application.state.engine_lock = Lock()

    @application.exception_handler(InvalidRequest)
    async def invalid_request_handler(
        request: Request, exception: InvalidRequest
    ) -> JSONResponse:
        return error_response(
            "validation_error",
            "Request validation failed.",
            [
                ErrorDetail(field=item.field, message=item.message)
                for item in exception.violations
            ],
        )

    @application.exception_handler(ResourceNotFound)
    async def not_found_handler(
        request: Request, exception: ResourceNotFound
    ) -> JSONResponse:
        return error_response("resource_not_found", "Resource not found.", [])

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            "validation_error",
            "Request validation failed.",
            _request_violations(exception),
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request, exception: Exception
    ) -> JSONResponse:
        return error_response("internal_error", "An unexpected error occurred.", [])

    @application.get("/health", response_model=HealthResponse)
    def get_health() -> HealthResponse:
        return HealthResponse(status="ok")

    application.include_router(task_list_collection_router)
    application.include_router(task_list_router)
    application.include_router(task_router)
    application.include_router(task_query_router)
    return application
