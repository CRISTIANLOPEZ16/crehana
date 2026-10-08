from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from task_manager.application.access.operations import (
    ListParticipantsUseCase,
    RemoveListMemberUseCase,
)
from task_manager.domain.user import User
from task_manager.application.ports import ParticipantPage
from task_manager.infrastructure.http.schemas.participant import (
    ParticipantPageResponse,
    ParticipantResponse,
)
from task_manager.infrastructure.http.security import get_current_user
from task_manager.infrastructure.http.support import (
    RESOURCE_RESPONSES,
    unit_of_work_factory,
)
from task_manager.infrastructure.http.validation import validate_query

router = APIRouter(
    prefix="/api/v1/task-lists/{list_id}/participants",
    responses=RESOURCE_RESPONSES,
)


@router.get("", response_model=ParticipantPageResponse)
def list_participants(
    list_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ParticipantPageResponse:
    validate_query(request, {"limit", "offset"})
    page: ParticipantPage = ListParticipantsUseCase(
        unit_of_work_factory(request)
    ).execute(list_id, current_user.id, limit, offset)
    return ParticipantPageResponse(
        items=[
            ParticipantResponse(
                id=participant.id,
                display_name=participant.display_name,
                email=participant.email,
                classification=participant.classification,
            )
            for participant in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.delete("/{user_id}", status_code=204)
def remove_participant(
    list_id: UUID,
    user_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    validate_query(request, set())
    RemoveListMemberUseCase(unit_of_work_factory(request)).execute(
        list_id, current_user.id, user_id
    )
    return Response(status_code=204)
