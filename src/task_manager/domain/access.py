from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListMembership:
    list_id: UUID
    user_id: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Participant:
    id: UUID
    display_name: str
    email: str
    classification: Literal["owner", "member"]
    created_at: datetime
