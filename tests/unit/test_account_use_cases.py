from contextlib import nullcontext
from typing import cast
from unittest.mock import Mock
from uuid import UUID

import pytest

from task_manager.application.accounts.operations import (
    LoginAccountUseCase,
    RegisterAccountUseCase,
)
from task_manager.application.commands import LoginAccount, RegisterAccount
from task_manager.application.errors import AuthenticationFailed
from task_manager.application.ports import (
    AccessTokenIssuer,
    PasswordService,
    UnitOfWork,
    UnitOfWorkFactory,
)
from task_manager.domain.user import User

pytestmark = pytest.mark.unit


class FakePasswordService:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeTokenIssuer:
    def issue(self, user_id: UUID) -> str:
        return f"token:{user_id}"


def test_registration_hashes_before_persisting_and_commits() -> None:
    user_store = Mock()
    unit_of_work = Mock(spec=UnitOfWork)
    unit_of_work.users = user_store
    factory: UnitOfWorkFactory = cast(
        UnitOfWorkFactory, lambda _: nullcontext(unit_of_work)
    )

    user = RegisterAccountUseCase(factory, FakePasswordService()).execute(
        RegisterAccount("Ada", "ADA@example.com", "a long passphrase")
    )

    user_store.create.assert_called_once_with(user)
    assert user.password_hash == "hashed:a long passphrase"
    assert "hashed:" not in repr(user)
    unit_of_work.commit.assert_called_once_with()


def test_login_uses_one_generic_failure_and_issues_access_token() -> None:
    user = User.register("Ada", "ada@example.com", "hashed:correct horse battery")
    user_store = Mock()
    user_store.get_by_email.return_value = user
    unit_of_work = Mock(spec=UnitOfWork)
    unit_of_work.users = user_store
    factory: UnitOfWorkFactory = cast(
        UnitOfWorkFactory, lambda _: nullcontext(unit_of_work)
    )
    use_case = LoginAccountUseCase(
        factory,
        cast(PasswordService, FakePasswordService()),
        cast(AccessTokenIssuer, FakeTokenIssuer()),
    )

    issued = use_case.execute(LoginAccount("ADA@example.com", "correct horse battery"))

    assert issued.access_token == f"token:{user.id}"
    assert issued.expires_in == 1800
    with pytest.raises(AuthenticationFailed, match="Invalid credentials"):
        use_case.execute(LoginAccount("unknown@example.com", "wrong password"))
