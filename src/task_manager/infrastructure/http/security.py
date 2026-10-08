from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from task_manager.application.errors import AuthenticationFailed
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.user import User
from task_manager.infrastructure.http.support import unit_of_work_factory
from task_manager.infrastructure.security.config import TokenConfiguration
from task_manager.infrastructure.security.tokens import AccessTokenService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if token is None:
        raise AuthenticationFailed("Authentication required.")
    configuration: TokenConfiguration = TokenConfiguration.from_environment()
    try:
        subject: UUID = AccessTokenService(configuration).verify(token)
    except (jwt.InvalidTokenError, ValueError):
        raise AuthenticationFailed("Invalid authentication credentials.") from None
    factory: UnitOfWorkFactory = unit_of_work_factory(request)
    with factory(True) as unit_of_work:
        user: User | None = unit_of_work.users.get(subject)
    if user is None:
        raise AuthenticationFailed("Invalid authentication credentials.")
    return user
