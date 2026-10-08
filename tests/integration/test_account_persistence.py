from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import Engine

from task_manager.application.accounts.operations import RegisterAccountUseCase
from task_manager.application.commands import RegisterAccount
from task_manager.application.errors import ResourceConflict
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory

pytestmark = pytest.mark.integration


class StoredPasswordService:
    def hash(self, password: str) -> str:
        return f"stored:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"stored:{password}"


def test_concurrent_canonical_email_registration_has_one_winner(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    use_case = RegisterAccountUseCase(factory, StoredPasswordService())
    start_together = Barrier(3)

    def register(email: str) -> bool:
        start_together.wait(timeout=5)
        try:
            use_case.execute(RegisterAccount("Race", email, "a valid long password"))
            return True
        except ResourceConflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(register, "Race@example.com")
        second = executor.submit(register, "race@EXAMPLE.COM")
        start_together.wait(timeout=5)
        outcomes: list[bool] = [first.result(timeout=10), second.result(timeout=10)]

    assert sorted(outcomes) == [False, True]
    with postgres_engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM users WHERE email='race@example.com'"
            ).scalar_one()
            == 1
        )
