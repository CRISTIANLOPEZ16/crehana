from dataclasses import dataclass
from uuid import UUID

from task_manager.application.commands import LoginAccount, RegisterAccount
from task_manager.application.errors import AuthenticationFailed, ResourceNotFound
from task_manager.application.ports import (
    AccessTokenIssuer,
    PasswordService,
    UnitOfWorkFactory,
)
from task_manager.domain.errors import DomainValidationError
from task_manager.domain.user import User, canonicalize_email, validate_password


@dataclass(frozen=True, slots=True)
class IssuedAccessToken:
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class RegisterAccountUseCase:
    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, password_service: PasswordService
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._password_service = password_service

    def execute(self, command: RegisterAccount) -> User:
        validate_password(command.password)
        password_hash: str = self._password_service.hash(command.password)
        user: User = User.register(command.display_name, command.email, password_hash)
        with self._unit_of_work_factory(False) as unit_of_work:
            unit_of_work.users.create(user)
            unit_of_work.commit()
        return user


class LoginAccountUseCase:
    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        password_service: PasswordService,
        token_issuer: AccessTokenIssuer,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._password_service = password_service
        self._token_issuer = token_issuer

    def execute(self, command: LoginAccount) -> IssuedAccessToken:
        try:
            email: str = canonicalize_email(command.email)
        except DomainValidationError:
            raise AuthenticationFailed("Invalid credentials.") from None
        with self._unit_of_work_factory(True) as unit_of_work:
            user: User | None = unit_of_work.users.get_by_email(email)
        if user is None or not self._password_service.verify(
            command.password, user.password_hash
        ):
            raise AuthenticationFailed("Invalid credentials.")
        return IssuedAccessToken(self._token_issuer.issue(user.id))


class GetCurrentAccountUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, user_id: UUID) -> User:
        with self._unit_of_work_factory(True) as unit_of_work:
            user: User | None = unit_of_work.users.get(user_id)
        if user is None:
            raise ResourceNotFound("Account not found.")
        return user
