from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from task_manager.application.commands import AcceptInvitation, CreateInvitation
from task_manager.application.invitations import (
    AcceptInvitationUseCase,
    CreateInvitationUseCase,
    GetInvitationUseCase,
    ListInvitationsUseCase,
    ResendInvitationUseCase,
    RevokeInvitationUseCase,
)
from task_manager.application.invitations.operations import IssuedInvitation
from task_manager.application.ports import InvitationPage
from task_manager.domain.invitation import Invitation
from task_manager.domain.access import ListMembership
from task_manager.domain.user import User
from task_manager.infrastructure.http.schemas.invitation import (
    AcceptedMembershipResponse,
    CreateInvitationRequest,
    AcceptInvitationRequest,
    InvitationPageResponse,
    InvitationResponse,
    InvitationSimulationResponse,
    IssuedInvitationResponse,
)
from task_manager.infrastructure.http.security import get_current_user
from task_manager.infrastructure.http.support import (
    RESOURCE_RESPONSES,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import validate_query
from task_manager.infrastructure.security.invitation_tokens import (
    SecureInvitationTokenService,
)

router = APIRouter(prefix="/api/v1", responses=RESOURCE_RESPONSES)


def invitation_response(invitation: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        list_id=invitation.list_id,
        invited_by_id=invitation.invited_by_id,
        recipient_email=invitation.recipient_email,
        status=invitation.status.value,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
        simulation=InvitationSimulationResponse(
            recipient=invitation.recipient_email,
            subject=invitation.simulation_subject,
            list_id=invitation.list_id,
            invitation_id=invitation.id,
            status="simulated",
            simulated_at=invitation.simulated_at,
        ),
    )


def issued_response(invited: IssuedInvitation) -> IssuedInvitationResponse:
    return IssuedInvitationResponse(
        **invitation_response(invited.invitation).model_dump(),
        acceptance_token=invited.acceptance_token,
    )


@router.post(
    "/task-lists/{list_id}/invitations",
    response_model=IssuedInvitationResponse,
    status_code=201,
)
def create_invitation(
    list_id: UUID,
    body: CreateInvitationRequest,
    request: Request,
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssuedInvitationResponse:
    validate_query(request, set())
    issued: IssuedInvitation = CreateInvitationUseCase(
        unit_of_work_factory(request), SecureInvitationTokenService()
    ).execute(CreateInvitation(list_id, current_user.id, body.recipient_email))
    response.headers["Location"] = (
        f"/api/v1/task-lists/{list_id}/invitations/{issued.invitation.id}"
    )
    return issued_response(issued)


@router.get("/task-lists/{list_id}/invitations", response_model=InvitationPageResponse)
def list_invitations(
    list_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InvitationPageResponse:
    validate_query(request, {"limit", "offset"})
    page: InvitationPage = ListInvitationsUseCase(
        unit_of_work_factory(request)
    ).execute(list_id, current_user.id, limit, offset)
    return InvitationPageResponse(
        items=[invitation_response(i) for i in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/task-lists/{list_id}/invitations/{invitation_id}",
    response_model=InvitationResponse,
)
def get_invitation(
    list_id: UUID,
    invitation_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvitationResponse:
    validate_query(request, set())
    invitation: Invitation = GetInvitationUseCase(
        unit_of_work_factory(request)
    ).execute(list_id, invitation_id, current_user.id)
    return invitation_response(invitation)


@router.post("/invitations/accept", response_model=AcceptedMembershipResponse)
def accept_invitation(
    body: AcceptInvitationRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> AcceptedMembershipResponse:
    validate_query(request, set())
    membership: ListMembership = AcceptInvitationUseCase(
        unit_of_work_factory(request), SecureInvitationTokenService()
    ).execute(AcceptInvitation(body.acceptance_token, current_user.id))
    return AcceptedMembershipResponse(
        list_id=membership.list_id,
        user_id=membership.user_id,
        created_at=membership.created_at,
    )


@router.post(
    "/task-lists/{list_id}/invitations/{invitation_id}/revoke",
    response_model=InvitationResponse,
)
def revoke_invitation(
    list_id: UUID,
    invitation_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> InvitationResponse:
    validate_query(request, set())
    invitation: Invitation = RevokeInvitationUseCase(
        unit_of_work_factory(request)
    ).execute(list_id, invitation_id, current_user.id)
    return invitation_response(invitation)


@router.post(
    "/task-lists/{list_id}/invitations/{invitation_id}/resend",
    response_model=IssuedInvitationResponse,
)
def resend_invitation(
    list_id: UUID,
    invitation_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> IssuedInvitationResponse:
    validate_query(request, set())
    issued: IssuedInvitation = ResendInvitationUseCase(
        unit_of_work_factory(request), SecureInvitationTokenService()
    ).execute(list_id, invitation_id, current_user.id)
    return issued_response(issued)
