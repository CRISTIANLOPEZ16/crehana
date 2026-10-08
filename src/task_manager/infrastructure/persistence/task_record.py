from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from task_manager.domain.task import Task, TaskPriority, TaskStatus
from task_manager.infrastructure.persistence.base import Base, TRIM_EXPRESSION


class TaskRecord(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "char_length(title) BETWEEN 1 AND 200", name="ck_tasks_title_length"
        ),
        CheckConstraint(
            f"title = btrim(title, {TRIM_EXPRESSION})", name="ck_tasks_title_trimmed"
        ),
        CheckConstraint(
            "description IS NULL OR char_length(description) BETWEEN 1 AND 2000",
            name="ck_tasks_description_length",
        ),
        CheckConstraint(
            "description IS NULL OR description = "
            f"btrim(description, {TRIM_EXPRESSION})",
            name="ck_tasks_description_trimmed",
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')", name="ck_tasks_priority"
        ),
        CheckConstraint("updated_at >= created_at", name="ck_tasks_timestamp_order"),
        Index("ix_tasks_list_created_id", "list_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    list_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "task_lists.id", ondelete="CASCADE", name="fk_tasks_list_id_task_lists"
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    def to_domain(self) -> Task:
        return Task(
            id=self.id,
            list_id=self.list_id,
            title=self.title,
            description=self.description,
            status=TaskStatus(self.status),
            priority=TaskPriority(self.priority),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
