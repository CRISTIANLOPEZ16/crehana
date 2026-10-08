from threading import Lock
from collections.abc import Mapping
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from task_manager.application.errors import (
    AuthenticationFailed,
    InvalidRequest,
    ResourceConflict,
    ResourceForbidden,
    ResourceNotFound,
)
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
from task_manager.infrastructure.http.routes.accounts import router as account_router
from task_manager.infrastructure.http.routes.participants import (
    router as participant_router,
)
from task_manager.infrastructure.http.routes.invitations import (
    router as invitation_router,
)
from task_manager.infrastructure.security.config import (
    TokenConfiguration,
    api_docs_enabled,
)


def _request_violations(exception: RequestValidationError) -> list[ErrorDetail]:
    return [
        ErrorDetail(
            field=_validation_location(error.get("loc")),
            message=_safe_validation_message(error),
        )
        for error in exception.errors()
    ]


def _validation_location(location: object) -> str:
    if not isinstance(location, (list, tuple)):
        return "body"
    return ".".join(str(part) for part in location)


def _public_violation_location(field: str) -> str:
    if field in {
        "name",
        "title",
        "description",
        "status",
        "priority",
        "display_name",
        "email",
        "recipient_email",
        "password",
    }:
        return f"body.{field}"
    return field


def _safe_validation_message(error: Mapping[str, object]) -> str:
    error_type: object = error.get("type")
    if error_type == "missing":
        return "Required field."
    if error_type == "string_too_short":
        return "Must not be blank or shorter than the minimum length."
    if error_type == "string_too_long":
        return "Exceeds the maximum length."
    if error_type == "enum":
        return "Unsupported value."
    if error_type == "extra_forbidden":
        return "Unknown field."
    context: object = error.get("ctx")
    if error_type == "value_error" and isinstance(context, dict):
        reason: object = context.get("error")
        if isinstance(reason, ValueError) and str(reason) == "Cannot be null.":
            return "Cannot be null."
    return "Invalid value."


def create_app(database_engine: Engine | None = None) -> FastAPI:
    docs_enabled: bool = api_docs_enabled()
    application: FastAPI = FastAPI(
        title="Task Manager API",
        version="1.0.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    application.state.database_engine = database_engine
    application.state.unit_of_work_factory = (
        create_unit_of_work_factory(database_engine) if database_engine else None
    )
    application.state.engine_lock = Lock()

    def validate_runtime_configuration() -> None:
        if database_engine is not None or os.environ.get("DATABASE_URL"):
            TokenConfiguration.from_environment()

    application.router.add_event_handler("startup", validate_runtime_configuration)

    @application.exception_handler(InvalidRequest)
    async def invalid_request_handler(
        request: Request, exception: InvalidRequest
    ) -> JSONResponse:
        return error_response(
            "validation_error",
            "Request validation failed.",
            [
                ErrorDetail(
                    field=_public_violation_location(item.field), message=item.message
                )
                for item in exception.violations
            ],
        )

    @application.exception_handler(ResourceNotFound)
    async def not_found_handler(
        request: Request, exception: ResourceNotFound
    ) -> JSONResponse:
        return error_response("resource_not_found", "Resource not found.", [])

    @application.exception_handler(ResourceForbidden)
    async def forbidden_handler(
        request: Request, exception: ResourceForbidden
    ) -> JSONResponse:
        return error_response("resource_forbidden", "Insufficient permission.", [])

    @application.exception_handler(ResourceConflict)
    async def conflict_handler(
        request: Request, exception: ResourceConflict
    ) -> JSONResponse:
        return error_response("resource_conflict", str(exception), [])

    @application.exception_handler(AuthenticationFailed)
    async def authentication_failed_handler(
        request: Request, exception: AuthenticationFailed
    ) -> JSONResponse:
        return error_response(
            "authentication_failed",
            "Authentication required or credentials are invalid.",
            [],
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    application.include_router(account_router)
    application.include_router(participant_router)
    application.include_router(invitation_router)
    application.include_router(task_list_collection_router)
    application.include_router(task_list_router)
    application.include_router(task_router)
    application.include_router(task_query_router)
    return application
