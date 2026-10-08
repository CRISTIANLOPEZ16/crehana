from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from task_manager.domain.invitation import Invitation, InvitationStatus
from task_manager.infrastructure.persistence.base import Base


class InvitationRecord(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        Index(
            "uq_invitations_pending_recipient",
            "list_id",
            "recipient_email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_invitations_list_created_id", "list_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    list_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("task_lists.id", ondelete="CASCADE"),
        nullable=False,
    )
    invited_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    recipient_email: Mapped[str] = mapped_column(String(254), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(
        LargeBinary(32), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    simulation_subject: Mapped[str] = mapped_column(Text, nullable=False)
    simulation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="simulated"
    )
    simulated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def to_domain(self) -> Invitation:
        return Invitation(
            self.id,
            self.list_id,
            self.invited_by_id,
            self.recipient_email,
            self.token_hash,
            InvitationStatus(self.status),
            self.created_at,
            self.expires_at,
            self.accepted_at,
            self.revoked_at,
            self.simulation_subject,
            self.simulated_at,
        )
