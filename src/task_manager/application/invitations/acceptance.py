from datetime import datetime, timezone
from task_manager.application.commands import AcceptInvitation
from task_manager.application.errors import ResourceConflict, ResourceNotFound
from task_manager.application.ports import InvitationTokenService, UnitOfWorkFactory
from task_manager.domain.access import ListMembership
from task_manager.domain.invitation import (
    Invitation,
    InvitationStateError,
    InvitationStatus,
)
from task_manager.domain.task_list import TaskList
from task_manager.domain.user import User


class AcceptInvitationUseCase:
    def __init__(
        self, factory: UnitOfWorkFactory, tokens: InvitationTokenService
    ) -> None:
        self._factory, self._tokens = factory, tokens

    def execute(self, command: AcceptInvitation) -> ListMembership:
        digest: bytes = self._tokens.digest(command.acceptance_token)
        now: datetime = datetime.now(timezone.utc)
        with self._factory(False) as unit:
            invitation: Invitation | None = unit.invitations.find_by_token_hash(digest)
            if invitation is None:
                raise ResourceNotFound("Invitation not found.")
            task_list: TaskList | None = unit.task_lists.get_for_update(
                invitation.list_id
            )
            if task_list is None:
                raise ResourceNotFound("Invitation not found.")
            invitation = unit.invitations.find_by_token_hash_for_update(digest)
            if invitation is None:
                raise ResourceNotFound("Invitation not found.")
            user: User | None = unit.users.get(command.user_id)
            if user is None or user.email != invitation.recipient_email:
                raise ResourceNotFound("Invitation not found.")
            membership: ListMembership
            if invitation.status == InvitationStatus.ACCEPTED:
                if unit.memberships.has_access(invitation.list_id, user.id):
                    membership = ListMembership(
                        invitation.list_id, user.id, invitation.accepted_at or now
                    )
                    return membership
                raise ResourceConflict("Accepted invitation no longer grants access.")
            try:
                invitation.accept(now)
            except InvitationStateError as error:
                if invitation.effective_status(now) == InvitationStatus.EXPIRED:
                    invitation.status = InvitationStatus.EXPIRED
                    unit.invitations.update(invitation)
                    unit.commit()
                raise ResourceConflict(str(error)) from error
            membership = ListMembership(invitation.list_id, user.id, now)
            if not unit.memberships.is_member(invitation.list_id, user.id):
                unit.memberships.create(membership)
            unit.invitations.update(invitation)
            unit.commit()
        return membership
