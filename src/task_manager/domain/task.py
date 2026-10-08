from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from task_manager.domain.validation import (
    changed_timestamp,
    initial_timestamp,
    normalize_description,
    normalize_required_text,
)


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(slots=True)
class Task:
    id: UUID
    list_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        list_id: UUID,
        title: str,
        description: str | None = None,
        status: TaskStatus = TaskStatus.PENDING,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee_id: UUID | None = None,
    ) -> Task:
        normalized_title: str = normalize_required_text(title, "title", 200)
        normalized_description: str | None = normalize_description(
            description, "description", 2000
        )
        created_at: datetime = initial_timestamp()
        return cls(
            id=uuid4(),
            list_id=list_id,
            title=normalized_title,
            description=normalized_description,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            created_at=created_at,
            updated_at=created_at,
        )

    def update(
        self,
        title: str | None,
        description: str | None,
        has_description: bool,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: UUID | None = None,
        has_assignee: bool = False,
    ) -> bool:
        normalized_title: str | None = (
            normalize_required_text(title, "title", 200) if title is not None else None
        )
        normalized_description: str | None = (
            normalize_description(description, "description", 2000)
            if has_description
            else None
        )
        changed: bool = False
        if normalized_title is not None and normalized_title != self.title:
            self.title = normalized_title
            changed = True
        if has_description and normalized_description != self.description:
            self.description = normalized_description
            changed = True
        if status is not None and status != self.status:
            self.status = status
            changed = True
        if priority is not None and priority != self.priority:
            self.priority = priority
            changed = True
        if has_assignee and assignee_id != self.assignee_id:
            self.assignee_id = assignee_id
            changed = True
        if changed:
            self.updated_at = changed_timestamp(self.updated_at)
        return changed

    def change_status(self, status: TaskStatus) -> bool:
        if status == self.status:
            return False
        self.status = status
        self.updated_at = changed_timestamp(self.updated_at)
        return True
