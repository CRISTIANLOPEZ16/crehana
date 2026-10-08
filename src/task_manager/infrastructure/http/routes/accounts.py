from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from starlette.datastructures import FormData

from task_manager.application.commands import LoginAccount, RegisterAccount
from task_manager.application.accounts.operations import (
    GetCurrentAccountUseCase,
    IssuedAccessToken,
    LoginAccountUseCase,
    RegisterAccountUseCase,
)
from task_manager.application.errors import InvalidRequest
from task_manager.domain.errors import FieldViolation
from task_manager.domain.user import User
from task_manager.infrastructure.http.schemas.account import (
    AccessTokenResponse,
    RegisterAccountRequest,
    UserResponse,
)
from task_manager.infrastructure.http.security import get_current_user
from task_manager.infrastructure.http.support import (
    RESOURCE_RESPONSES,
    unit_of_work_factory,
)
from task_manager.infrastructure.security.passwords import Argon2PasswordService
from task_manager.infrastructure.security.tokens import AccessTokenService
from task_manager.infrastructure.security.config import TokenConfiguration

router = APIRouter(prefix="/api/v1/auth")


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register_account(
    body: RegisterAccountRequest, request: Request, response: Response
) -> UserResponse:
    user: User = RegisterAccountUseCase(
        unit_of_work_factory(request), Argon2PasswordService()
    ).execute(
        RegisterAccount(
            display_name=body.display_name,
            email=body.email,
            password=body.password.get_secret_value(),
        )
    )
    response.headers["Location"] = "/api/v1/auth/me"
    return user_response(user)


@router.post("/login", response_model=AccessTokenResponse)
async def login_account(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    grant_type: Annotated[str | None, Form()] = None,
    scope: Annotated[str, Form()] = "",
) -> AccessTokenResponse:
    form_data: FormData = await request.form()
    violations: list[FieldViolation] = []
    for field_name in form_data.keys():
        if field_name not in {"username", "password", "grant_type", "scope"}:
            violations.append(
                FieldViolation(f"body.{field_name}", "Unknown form field.")
            )
        if len(form_data.getlist(field_name)) > 1:
            violations.append(
                FieldViolation(f"body.{field_name}", "May be provided only once.")
            )
    if grant_type not in (None, "password"):
        violations.append(
            FieldViolation("body.grant_type", "Must be password when provided.")
        )
    if scope:
        violations.append(FieldViolation("body.scope", "Must be empty."))
    if violations:
        raise InvalidRequest(violations)
    configuration: TokenConfiguration = TokenConfiguration.from_environment()
    issued_token: IssuedAccessToken = LoginAccountUseCase(
        unit_of_work_factory(request),
        Argon2PasswordService(),
        AccessTokenService(configuration),
    ).execute(LoginAccount(email=username, password=password))
    return AccessTokenResponse(
        access_token=issued_token.access_token,
        token_type=issued_token.token_type,
        expires_in=issued_token.expires_in,
    )


@router.get("/me", response_model=UserResponse, responses=RESOURCE_RESPONSES)
def get_current_account(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    user: User = GetCurrentAccountUseCase(unit_of_work_factory(request)).execute(
        current_user.id
    )
    return user_response(user)
