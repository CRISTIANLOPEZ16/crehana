from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from task_manager.application.commands import CreateInvitation
from task_manager.application.errors import InvalidRequest, ResourceConflict
from task_manager.application.invitations.operations import (
    CreateInvitationUseCase,
    ResendInvitationUseCase,
    RevokeInvitationUseCase,
)
from task_manager.application.ports import (
    InvitationTokenService,
    UnitOfWorkFactory,
)
from task_manager.domain.invitation import Invitation, InvitationStatus
from task_manager.domain.task_list import TaskList

pytestmark = pytest.mark.unit


class FixedInvitationTokens:
    def issue(self) -> tuple[str, bytes]:
        return "raw-one-time-token", b"v" * 32

    def digest(self, token: str) -> bytes:
        return token.encode("utf-8")


def _unit_of_work(owner_id: UUID) -> tuple[Mock, UnitOfWorkFactory, TaskList]:
    task_list = TaskList.create("Launch", owner_id)
    unit = Mock()
    unit.task_lists.get_for_update.return_value = task_list
    unit.task_lists.get.return_value = task_list
    unit.memberships.has_access.return_value = True
    unit.memberships.is_member.return_value = False
    unit.users.get_by_email.return_value = None
    unit.invitations.has_pending.return_value = False
    factory: UnitOfWorkFactory = cast(UnitOfWorkFactory, lambda _: nullcontext(unit))
    return unit, factory, task_list


def test_create_invitation_normalizes_recipient_and_exposes_token_once() -> None:
    owner_id = uuid4()
    unit, factory, task_list = _unit_of_work(owner_id)
    issued = CreateInvitationUseCase(factory, FixedInvitationTokens()).execute(
        CreateInvitation(task_list.id, owner_id, " Person@EXAMPLE.COM ")
    )
    assert issued.invitation.recipient_email == "person@example.com"
    assert issued.invitation.status is InvitationStatus.PENDING
    assert issued.invitation.expires_at - issued.invitation.created_at == timedelta(
        days=7
    )
    assert issued.acceptance_token == "raw-one-time-token"
    assert issued.acceptance_token not in repr(issued.invitation)
    unit.invitations.create.assert_called_once_with(issued.invitation)
    unit.commit.assert_called_once_with()


def test_create_invitation_rejects_existing_active_duplicate_without_commit() -> None:
    owner_id = uuid4()
    unit, factory, task_list = _unit_of_work(owner_id)
    unit.invitations.has_pending.return_value = True
    with pytest.raises(ResourceConflict):
        CreateInvitationUseCase(factory, FixedInvitationTokens()).execute(
            CreateInvitation(task_list.id, owner_id, "person@example.com")
        )
    unit.invitations.create.assert_not_called()
    unit.commit.assert_not_called()


def test_create_invitation_maps_invalid_recipient_to_its_request_field() -> None:
    owner_id = uuid4()
    unit, factory, task_list = _unit_of_work(owner_id)
    with pytest.raises(InvalidRequest) as error:
        CreateInvitationUseCase(factory, FixedInvitationTokens()).execute(
            CreateInvitation(task_list.id, owner_id, "invalid-address")
        )
    assert error.value.violations[0].field == "recipient_email"
    unit.task_lists.get_for_update.assert_not_called()


def test_resend_rotates_verifier_and_revoked_revoke_is_idempotent() -> None:
    owner_id = uuid4()
    unit, factory, task_list = _unit_of_work(owner_id)
    now = datetime.now(UTC)
    invitation = Invitation.create(
        task_list.id, owner_id, "person@example.com", b"o" * 32, task_list.name, now
    )
    unit.invitations.get_for_update.return_value = invitation
    resend = ResendInvitationUseCase(
        factory, cast(InvitationTokenService, FixedInvitationTokens())
    )
    issued = resend.execute(task_list.id, invitation.id, owner_id)
    assert issued.acceptance_token == "raw-one-time-token"
    assert issued.invitation.token_hash == b"v" * 32
    assert issued.invitation.expires_at > issued.invitation.created_at + timedelta(
        days=6
    )
    unit.commit.assert_called_once_with()

    unit.commit.reset_mock()
    invitation.status = InvitationStatus.REVOKED
    invitation.revoked_at = now
    assert (
        RevokeInvitationUseCase(factory)
        .execute(task_list.id, invitation.id, owner_id)
        .status
        is InvitationStatus.REVOKED
    )
    unit.commit.assert_not_called()
