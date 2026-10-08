from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from task_manager.domain.user import User
from task_manager.infrastructure.persistence.user_record import UserRecord


class SQLAlchemyUserStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, user: User) -> None:
        self._session.add(
            UserRecord(
                id=user.id,
                display_name=user.display_name,
                email=user.email,
                password_hash=user.password_hash,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )

    def get(self, user_id: UUID) -> User | None:
        record: UserRecord | None = self._session.get(UserRecord, user_id)
        return record.to_domain() if record is not None else None

    def get_by_email(self, email: str) -> User | None:
        record: UserRecord | None = self._session.scalar(
            select(UserRecord).where(UserRecord.email == email)
        )
        return record.to_domain() if record is not None else None
