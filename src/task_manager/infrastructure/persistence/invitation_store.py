from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from task_manager.application.ports import InvitationPage
from task_manager.domain.invitation import Invitation, InvitationStatus
from task_manager.infrastructure.persistence.invitation_record import InvitationRecord


class SQLAlchemyInvitationStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, invitation: Invitation) -> None:
        self._session.add(
            InvitationRecord(
                id=invitation.id,
                list_id=invitation.list_id,
                invited_by_id=invitation.invited_by_id,
                recipient_email=invitation.recipient_email,
                token_hash=invitation.token_hash,
                status=invitation.status.value,
                created_at=invitation.created_at,
                expires_at=invitation.expires_at,
                accepted_at=invitation.accepted_at,
                revoked_at=invitation.revoked_at,
                simulation_subject=invitation.simulation_subject,
                simulation_status="simulated",
                simulated_at=invitation.simulated_at,
            )
        )

    def _get(
        self, query: Select[InvitationRecord], lock: bool = False
    ) -> Invitation | None:
        statement: Select[InvitationRecord] = query.with_for_update() if lock else query
        record: InvitationRecord | None = self._session.scalars(statement).first()
        return record.to_domain() if record is not None else None

    def get(self, list_id: UUID, invitation_id: UUID) -> Invitation | None:
        return self._get(
            select(InvitationRecord).where(
                InvitationRecord.list_id == list_id,
                InvitationRecord.id == invitation_id,
            )
        )

    def get_for_update(self, list_id: UUID, invitation_id: UUID) -> Invitation | None:
        return self._get(
            select(InvitationRecord).where(
                InvitationRecord.list_id == list_id,
                InvitationRecord.id == invitation_id,
            ),
            True,
        )

    def find_by_token_hash(self, token_hash: bytes) -> Invitation | None:
        return self._get(
            select(InvitationRecord).where(InvitationRecord.token_hash == token_hash)
        )

    def find_by_token_hash_for_update(self, token_hash: bytes) -> Invitation | None:
        return self._get(
            select(InvitationRecord).where(InvitationRecord.token_hash == token_hash),
            True,
        )

    def expire_pending(self, list_id: UUID, now: datetime) -> None:
        self._session.execute(
            update(InvitationRecord)
            .where(
                InvitationRecord.list_id == list_id,
                InvitationRecord.status == InvitationStatus.PENDING.value,
                InvitationRecord.expires_at <= now,
            )
            .values(status=InvitationStatus.EXPIRED.value)
        )

    def has_pending(self, list_id: UUID, recipient_email: str) -> bool:
        return (
            self._session.scalar(
                select(InvitationRecord.id).where(
                    InvitationRecord.list_id == list_id,
                    InvitationRecord.recipient_email == recipient_email,
                    InvitationRecord.status == InvitationStatus.PENDING.value,
                )
            )
            is not None
        )

    def update(self, invitation: Invitation) -> None:
        record: InvitationRecord | None = self._session.get(
            InvitationRecord, invitation.id
        )
        if record is None:
            raise LookupError("Invitation disappeared during update.")
        record.token_hash = invitation.token_hash
        record.status = invitation.status.value
        record.created_at = invitation.created_at
        record.expires_at = invitation.expires_at
        record.accepted_at = invitation.accepted_at
        record.revoked_at = invitation.revoked_at
        record.simulation_subject = invitation.simulation_subject
        record.simulated_at = invitation.simulated_at

    def page(self, list_id: UUID, limit: int, offset: int) -> InvitationPage:
        total: int = int(
            self._session.scalar(
                select(func.count())
                .select_from(InvitationRecord)
                .where(InvitationRecord.list_id == list_id)
            )
            or 0
        )
        rows: list[InvitationRecord] = []
        if offset < total:
            rows = list(
                self._session.scalars(
                    select(InvitationRecord)
                    .where(InvitationRecord.list_id == list_id)
                    .order_by(InvitationRecord.created_at, InvitationRecord.id)
                    .limit(limit)
                    .offset(offset)
                )
            )
        return InvitationPage(
            [record.to_domain() for record in rows], total, limit, offset
        )
