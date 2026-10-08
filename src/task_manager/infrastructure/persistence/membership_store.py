from uuid import UUID
from typing import Literal, cast

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from task_manager.application.ports import ParticipantPage
from task_manager.domain.access import ListMembership, Participant
from task_manager.infrastructure.persistence.membership_record import MembershipRecord
from task_manager.infrastructure.persistence.task_list_record import TaskListRecord
from task_manager.infrastructure.persistence.user_record import UserRecord


class SQLAlchemyMembershipStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def has_access(self, list_id: UUID, user_id: UUID) -> bool:
        membership_exists: ColumnElement[bool] = exists(
            select(MembershipRecord.user_id).where(
                MembershipRecord.list_id == TaskListRecord.id,
                MembershipRecord.user_id == user_id,
            )
        )
        return (
            self._session.scalar(
                select(TaskListRecord.id).where(
                    TaskListRecord.id == list_id,
                    or_(TaskListRecord.owner_id == user_id, membership_exists),
                )
            )
            is not None
        )

    def is_member(self, list_id: UUID, user_id: UUID) -> bool:
        return self._session.get(MembershipRecord, (list_id, user_id)) is not None

    def create(self, membership: ListMembership) -> None:
        self._session.add(
            MembershipRecord(
                list_id=membership.list_id,
                user_id=membership.user_id,
                created_at=membership.created_at,
            )
        )

    def delete(self, list_id: UUID, user_id: UUID) -> bool:
        membership: MembershipRecord | None = self._session.get(
            MembershipRecord, (list_id, user_id)
        )
        if membership is None:
            return False
        self._session.delete(membership)
        return True

    def page_participants(
        self, list_id: UUID, limit: int, offset: int
    ) -> ParticipantPage:
        membership_exists: ColumnElement[bool] = exists(
            select(MembershipRecord.user_id).where(
                MembershipRecord.list_id == list_id,
                MembershipRecord.user_id == UserRecord.id,
            )
        )
        participant_condition: ColumnElement[bool] = or_(
            UserRecord.id == TaskListRecord.owner_id, membership_exists
        )
        total: int = int(
            self._session.scalar(
                select(func.count(UserRecord.id))
                .select_from(UserRecord)
                .join(TaskListRecord, TaskListRecord.id == list_id)
                .where(participant_condition)
            )
            or 0
        )
        rows: list[tuple[UserRecord, str]] = []
        if offset < total:
            rows = list(
                self._session.execute(
                    select(
                        UserRecord,
                        case(
                            (UserRecord.id == TaskListRecord.owner_id, "owner"),
                            else_="member",
                        ),
                    )
                    .join(TaskListRecord, TaskListRecord.id == list_id)
                    .where(participant_condition)
                    .order_by(UserRecord.created_at, UserRecord.id)
                    .limit(limit)
                    .offset(offset)
                ).all()
            )
        participants: list[Participant] = [
            Participant(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                classification=cast(Literal["owner", "member"], classification),
                created_at=user.created_at,
            )
            for user, classification in rows
        ]
        return ParticipantPage(participants, total, limit, offset)
