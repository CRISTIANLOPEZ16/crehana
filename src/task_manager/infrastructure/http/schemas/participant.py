from typing import Literal
from uuid import UUID

from pydantic import Field

from task_manager.infrastructure.http.schemas.common import StrictSchema


class ParticipantResponse(StrictSchema):
    id: UUID
    display_name: str
    email: str
    classification: Literal["owner", "member"]


class ParticipantPageResponse(StrictSchema):
    items: list[ParticipantResponse]
    total: int
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
