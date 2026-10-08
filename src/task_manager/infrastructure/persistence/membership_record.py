from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from task_manager.domain.access import ListMembership
from task_manager.infrastructure.persistence.base import Base


class MembershipRecord(Base):
    __tablename__ = "list_memberships"

    list_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("task_lists.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def to_domain(self) -> ListMembership:
        return ListMembership(self.list_id, self.user_id, self.created_at)
