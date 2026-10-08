from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from task_manager.domain.task_list import TaskList
from task_manager.infrastructure.persistence.base import Base, TRIM_EXPRESSION


class TaskListRecord(Base):
    __tablename__ = "task_lists"
    __table_args__ = (
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100", name="ck_task_lists_name_length"
        ),
        CheckConstraint(
            f"name = btrim(name, {TRIM_EXPRESSION})",
            name="ck_task_lists_name_trimmed",
        ),
        CheckConstraint(
            "description IS NULL OR char_length(description) BETWEEN 1 AND 1000",
            name="ck_task_lists_description_length",
        ),
        CheckConstraint(
            "description IS NULL OR description = "
            f"btrim(description, {TRIM_EXPRESSION})",
            name="ck_task_lists_description_trimmed",
        ),
        CheckConstraint(
            "updated_at >= created_at", name="ck_task_lists_timestamp_order"
        ),
        Index("ix_task_lists_created_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def to_domain(self) -> TaskList:
        return TaskList(
            id=self.id,
            name=self.name,
            description=self.description,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
