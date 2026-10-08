from contextlib import nullcontext
import getpass
import sys
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy import Engine

from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.user import User
from task_manager.infrastructure import bootstrap_owner

pytestmark = pytest.mark.unit


def test_bootstrap_cli_uses_existing_account_without_prompting_for_password(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    owner = User.register("Historical owner", "historical@example.com", "kept-hash")
    unit = Mock()
    unit.users.get_by_email.return_value = owner
    unit.task_lists.owner_ids.return_value = set()
    factory: UnitOfWorkFactory = cast(UnitOfWorkFactory, lambda _: nullcontext(unit))
    engine = Mock(spec=Engine)
    monkeypatch.setattr(bootstrap_owner, "create_database_engine", lambda: engine)
    monkeypatch.setattr(
        bootstrap_owner, "create_unit_of_work_factory", lambda _: factory
    )
    monkeypatch.setattr(sys, "stdin", Mock(isatty=Mock(return_value=True)))
    monkeypatch.setattr("builtins.input", lambda _: owner.email)
    monkeypatch.setattr(
        getpass,
        "getpass",
        lambda _: pytest.fail("Existing account must not prompt for a password."),
    )

    assert bootstrap_owner.main() == 0
    assert str(owner.id) in capsys.readouterr().out
    unit.task_lists.assign_missing_owner.assert_called_once_with(owner.id)
    unit.commit.assert_called_once_with()
    engine.dispose.assert_called_once_with()


def test_bootstrap_cli_rejects_invalid_email_with_safe_field_reason(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    engine = Mock(spec=Engine)
    monkeypatch.setattr(bootstrap_owner, "create_database_engine", lambda: engine)
    monkeypatch.setattr(sys, "stdin", Mock(isatty=Mock(return_value=True)))
    monkeypatch.setattr("builtins.input", lambda _: "invalid-address")

    assert bootstrap_owner.main() == 2
    captured = capsys.readouterr()
    assert "email:" in captured.err
    assert "invalid-address" not in captured.err
    engine.dispose.assert_called_once_with()


def test_bootstrap_cli_requires_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", Mock(isatty=Mock(return_value=False)))
    monkeypatch.setattr(
        bootstrap_owner,
        "create_database_engine",
        lambda: pytest.fail("Do not connect without a terminal."),
    )
    assert bootstrap_owner.main() == 2
