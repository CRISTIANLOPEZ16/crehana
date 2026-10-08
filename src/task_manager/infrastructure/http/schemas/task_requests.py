from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints, field_validator, model_validator

from task_manager.domain.task import TaskPriority, TaskStatus
from task_manager.infrastructure.http.schemas.common import StrictSchema


class CreateTaskRequest(StrictSchema):
    title: Annotated[
        str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)
    ]
    description: Annotated[
        str | None,
        StringConstraints(max_length=2000, strip_whitespace=True),
    ] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_blank_description(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class UpdateTaskRequest(StrictSchema):
    title: Annotated[
        str | None,
        StringConstraints(min_length=1, max_length=200, strip_whitespace=True),
    ] = None
    description: Annotated[
        str | None,
        StringConstraints(max_length=2000, strip_whitespace=True),
    ] = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None

    @field_validator("title", "status", "priority", mode="before")
    @classmethod
    def reject_null_required_patch_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("Cannot be null.")
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_blank_description(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_patch(self) -> UpdateTaskRequest:
        if not self.model_fields_set:
            raise ValueError("PATCH body must contain at least one field.")
        return self
