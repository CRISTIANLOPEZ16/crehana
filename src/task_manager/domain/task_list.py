from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from task_manager.domain.validation import (
    changed_timestamp,
    initial_timestamp,
    normalize_description,
    normalize_required_text,
)


@dataclass(slots=True)
class TaskList:
    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls, name: str, owner_id: UUID, description: str | None = None
    ) -> TaskList:
        normalized_name: str = normalize_required_text(name, "name", 100)
        normalized_description: str | None = normalize_description(
            description, "description", 1000
        )
        created_at: datetime = initial_timestamp()
        return cls(
            id=uuid4(),
            owner_id=owner_id,
            name=normalized_name,
            description=normalized_description,
            created_at=created_at,
            updated_at=created_at,
        )

    def update(
        self, name: str | None, description: str | None, has_description: bool
    ) -> bool:
        normalized_name: str | None = (
            normalize_required_text(name, "name", 100) if name is not None else None
        )
        normalized_description: str | None = (
            normalize_description(description, "description", 1000)
            if has_description
            else None
        )
        changed: bool = False
        if normalized_name is not None and normalized_name != self.name:
            self.name = normalized_name
            changed = True
        if has_description and normalized_description != self.description:
            self.description = normalized_description
            changed = True
        if changed:
            self.updated_at = changed_timestamp(self.updated_at)
        return changed
