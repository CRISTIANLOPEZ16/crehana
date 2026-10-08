from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from task_manager.domain.user import User
from task_manager.infrastructure.persistence.base import Base


class UserRecord(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "char_length(display_name) BETWEEN 1 AND 100",
            name="ck_users_display_name_length",
        ),
        CheckConstraint(
            "display_name = btrim(display_name)",
            name="ck_users_display_name_trimmed",
        ),
        CheckConstraint(
            "email = lower(email) AND char_length(email) BETWEEN 3 AND 254",
            name="ck_users_email_canonical",
        ),
        CheckConstraint("updated_at >= created_at", name="ck_users_timestamp_order"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def to_domain(self) -> User:
        return User(
            id=self.id,
            display_name=self.display_name,
            email=self.email,
            password_hash=self.password_hash,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
