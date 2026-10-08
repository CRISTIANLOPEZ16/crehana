from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints

from task_manager.infrastructure.http.schemas.common import StrictSchema


class CreateInvitationRequest(StrictSchema):
    recipient_email: Annotated[str, StringConstraints(min_length=3, max_length=254)]


class AcceptInvitationRequest(StrictSchema):
    acceptance_token: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class InvitationSimulationResponse(StrictSchema):
    recipient: str
    subject: str
    list_id: UUID
    invitation_id: UUID
    status: Literal["simulated"]
    simulated_at: datetime


class InvitationResponse(StrictSchema):
    id: UUID
    list_id: UUID
    invited_by_id: UUID
    recipient_email: str
    status: Literal["pending", "accepted", "revoked", "expired"]
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    simulation: InvitationSimulationResponse


class IssuedInvitationResponse(InvitationResponse):
    acceptance_token: str


class InvitationPageResponse(StrictSchema):
    items: list[InvitationResponse]
    total: int
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class AcceptedMembershipResponse(StrictSchema):
    list_id: UUID
    user_id: UUID
    created_at: datetime
