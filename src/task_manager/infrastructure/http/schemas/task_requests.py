from __future__ import annotations

from typing import Annotated

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
        for field_name in ("title", "status", "priority"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null.")
        return self
