from uuid import UUID

from task_manager.application.errors import ResourceForbidden, ResourceNotFound
from datetime import datetime, timezone

from task_manager.application.ports import InvitationPage, UnitOfWork, UnitOfWorkFactory
from task_manager.domain.invitation import Invitation
from task_manager.domain.task_list import TaskList


def _require_owner(unit: UnitOfWork, list_id: UUID, caller_id: UUID) -> None:
    task_list: TaskList | None = unit.task_lists.get(list_id)
    if task_list is None:
        raise ResourceNotFound("Task list not found.")
    if task_list.owner_id != caller_id:
        if unit.memberships.has_access(list_id, caller_id):
            raise ResourceForbidden("Only the owner can inspect invitations.")
        raise ResourceNotFound("Task list not found.")


class ListInvitationsUseCase:
    def __init__(self, factory: UnitOfWorkFactory) -> None:
        self._factory = factory

    def execute(
        self, list_id: UUID, caller_id: UUID, limit: int, offset: int
    ) -> InvitationPage:
        with self._factory(True) as unit:
            _require_owner(unit, list_id, caller_id)
            page: InvitationPage = unit.invitations.page(list_id, limit, offset)
            now: datetime = datetime.now(timezone.utc)
            for invitation in page.items:
                invitation.status = invitation.effective_status(now)
            return page


class GetInvitationUseCase:
    def __init__(self, factory: UnitOfWorkFactory) -> None:
        self._factory = factory

    def execute(
        self, list_id: UUID, invitation_id: UUID, caller_id: UUID
    ) -> Invitation:
        with self._factory(True) as unit:
            _require_owner(unit, list_id, caller_id)
            invitation: Invitation | None = unit.invitations.get(list_id, invitation_id)
        if invitation is None:
            raise ResourceNotFound("Invitation not found.")
        invitation.status = invitation.effective_status(datetime.now(timezone.utc))
        return invitation
