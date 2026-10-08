from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from task_manager.domain.invitation import (
    Invitation,
    InvitationStateError,
    InvitationStatus,
)
from task_manager.infrastructure.security.invitation_tokens import (
    SecureInvitationTokenService,
)

pytestmark = pytest.mark.unit


def test_invitation_expires_at_exact_boundary_and_rejects_acceptance() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    invitation = Invitation.create(
        uuid4(), uuid4(), "person@example.com", b"a" * 32, "Launch", now
    )
    assert invitation.status is InvitationStatus.PENDING
    assert invitation.expires_at == now + timedelta(days=7)
    assert (
        invitation.effective_status(invitation.expires_at - timedelta(microseconds=1))
        is InvitationStatus.PENDING
    )
    assert (
        invitation.effective_status(invitation.expires_at) is InvitationStatus.EXPIRED
    )
    with pytest.raises(InvitationStateError):
        invitation.accept(invitation.expires_at)


def test_invitation_accept_revoke_and_resend_preserve_lifecycle_timestamps() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    invitation = Invitation.create(
        uuid4(), uuid4(), "person@example.com", b"a" * 32, "Launch", now
    )
    invitation.accept(now + timedelta(minutes=1))
    assert invitation.accepted_at == now + timedelta(minutes=1)
    with pytest.raises(InvitationStateError):
        invitation.resend(b"b" * 32, "Launch", now + timedelta(minutes=2))

    revoked = Invitation.create(
        uuid4(), uuid4(), "other@example.com", b"c" * 32, "Launch", now
    )
    assert revoked.revoke(now + timedelta(minutes=1))
    assert not revoked.revoke(now + timedelta(minutes=2))
    assert revoked.revoked_at == now + timedelta(minutes=1)

    expired = Invitation.create(
        uuid4(), uuid4(), "third@example.com", b"d" * 32, "Launch", now
    )
    expired_at = expired.created_at
    expired.resend(b"e" * 32, "Launch 2", expired.expires_at)
    assert expired.status is InvitationStatus.PENDING
    assert expired.created_at == expired_at
    assert expired.token_hash == b"e" * 32
    assert expired.simulation_subject.endswith("Launch 2")


def test_invitation_token_service_returns_random_verifier_and_never_token() -> None:
    service = SecureInvitationTokenService()
    token, verifier = service.issue()
    assert len(token) >= 43
    assert len(verifier) == 32
    assert service.digest(token) == verifier
    assert service.digest(token + "x") != verifier
