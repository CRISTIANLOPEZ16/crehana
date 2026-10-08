from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints, field_validator, model_validator

from task_manager.infrastructure.http.schemas.common import StrictSchema


class TaskListResponse(StrictSchema):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class TaskListPageResponse(StrictSchema):
    items: list[TaskListResponse]
    total: int
    limit: int
    offset: int


class CreateTaskListRequest(StrictSchema):
    name: Annotated[
        str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)
    ]
    description: Annotated[
        str | None,
        StringConstraints(max_length=1000, strip_whitespace=True),
    ] = None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_blank_description(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class UpdateTaskListRequest(StrictSchema):
    name: Annotated[
        str | None,
        StringConstraints(min_length=1, max_length=100, strip_whitespace=True),
    ] = None
    description: Annotated[
        str | None,
        StringConstraints(max_length=1000, strip_whitespace=True),
    ] = None

    @field_validator("description", mode="before")
    @classmethod
    def normalize_blank_description(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_patch(self) -> UpdateTaskListRequest:
        if not self.model_fields_set:
            raise ValueError("PATCH body must contain at least one field.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null.")
        return self
