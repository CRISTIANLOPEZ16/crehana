from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4


class InvitationStateError(Exception):
    pass


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass(slots=True)
class Invitation:
    id: UUID
    list_id: UUID
    invited_by_id: UUID
    recipient_email: str
    token_hash: bytes
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    simulation_subject: str
    simulated_at: datetime

    @classmethod
    def create(
        cls,
        list_id: UUID,
        inviter_id: UUID,
        recipient_email: str,
        token_hash: bytes,
        list_name: str,
        now: datetime,
    ) -> Invitation:
        return cls(
            uuid4(),
            list_id,
            inviter_id,
            recipient_email,
            token_hash,
            InvitationStatus.PENDING,
            now,
            now + timedelta(days=7),
            None,
            None,
            f"Invitation to collaborate on {list_name}",
            now,
        )

    def effective_status(self, now: datetime) -> InvitationStatus:
        if self.status == InvitationStatus.PENDING and now >= self.expires_at:
            return InvitationStatus.EXPIRED
        return self.status

    def accept(self, now: datetime) -> None:
        if self.effective_status(now) != InvitationStatus.PENDING:
            raise InvitationStateError(
                "Invitation cannot be accepted in its current state."
            )
        self.status = InvitationStatus.ACCEPTED
        self.accepted_at = now

    def revoke(self, now: datetime) -> bool:
        status: InvitationStatus = self.effective_status(now)
        if status == InvitationStatus.REVOKED:
            return False
        if status != InvitationStatus.PENDING:
            raise InvitationStateError(
                "Invitation cannot be revoked in its current state."
            )
        self.status = InvitationStatus.REVOKED
        self.revoked_at = now
        return True

    def resend(self, token_hash: bytes, list_name: str, now: datetime) -> None:
        if self.effective_status(now) not in {
            InvitationStatus.PENDING,
            InvitationStatus.EXPIRED,
        }:
            raise InvitationStateError(
                "Invitation cannot be resent in its current state."
            )
        self.token_hash = token_hash
        self.status = InvitationStatus.PENDING
        self.expires_at = now + timedelta(days=7)
        self.accepted_at = None
        self.revoked_at = None
        self.simulation_subject = f"Invitation to collaborate on {list_name}"
        self.simulated_at = now
