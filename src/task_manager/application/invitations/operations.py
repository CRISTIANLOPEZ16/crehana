from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from task_manager.application.commands import CreateInvitation
from task_manager.application.errors import (
    ResourceConflict,
    ResourceForbidden,
    ResourceNotFound,
)
from task_manager.application.ports import (
    InvitationTokenService,
    UnitOfWork,
    UnitOfWorkFactory,
)
from task_manager.domain.task_list import TaskList
from task_manager.domain.user import User
from task_manager.domain.errors import DomainValidationError, FieldViolation
from task_manager.domain.invitation import (
    Invitation,
    InvitationStateError,
    InvitationStatus,
)
from task_manager.domain.user import canonicalize_email


@dataclass(frozen=True, slots=True)
class IssuedInvitation:
    invitation: Invitation
    acceptance_token: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owner_list(unit_of_work: UnitOfWork, list_id: UUID, owner_id: UUID) -> TaskList:
    task_list: TaskList | None = unit_of_work.task_lists.get_for_update(list_id)
    if task_list is None:
        raise ResourceNotFound("Task list not found.")
    if task_list.owner_id != owner_id:
        if unit_of_work.memberships.has_access(list_id, owner_id):
            raise ResourceForbidden("Only the owner can manage invitations.")
        raise ResourceNotFound("Task list not found.")
    return task_list


class CreateInvitationUseCase:
    def __init__(
        self, factory: UnitOfWorkFactory, tokens: InvitationTokenService
    ) -> None:
        self._factory, self._tokens = factory, tokens

    def execute(self, command: CreateInvitation) -> IssuedInvitation:
        try:
            email: str = canonicalize_email(command.recipient_email)
        except DomainValidationError as error:
            raise DomainValidationError(
                [
                    FieldViolation("recipient_email", item.message)
                    for item in error.violations
                ]
            ) from error
        now: datetime = _now()
        token, digest = self._tokens.issue()
        with self._factory(False) as unit:
            task_list: TaskList = _owner_list(
                unit, command.list_id, command.invited_by_id
            )
            unit.invitations.expire_pending(command.list_id, now)
            recipient: User | None = unit.users.get_by_email(email)
            if recipient is not None and (
                recipient.id == task_list.owner_id
                or unit.memberships.is_member(command.list_id, recipient.id)
            ):
                raise ResourceConflict("The recipient already has access to this list.")
            if unit.invitations.has_pending(command.list_id, email):
                raise ResourceConflict("An active invitation already exists.")
            invitation: Invitation = Invitation.create(
                command.list_id,
                command.invited_by_id,
                email,
                digest,
                task_list.name,
                now,
            )
            unit.invitations.create(invitation)
            unit.commit()
        return IssuedInvitation(invitation, token)


class RevokeInvitationUseCase:
    def __init__(self, factory: UnitOfWorkFactory) -> None:
        self._factory = factory

    def execute(
        self, list_id: UUID, invitation_id: UUID, caller_id: UUID
    ) -> Invitation:
        now: datetime = _now()
        with self._factory(False) as unit:
            _owner_list(unit, list_id, caller_id)
            invitation: Invitation | None = unit.invitations.get_for_update(
                list_id, invitation_id
            )
            if invitation is None:
                raise ResourceNotFound("Invitation not found.")
            try:
                changed: bool = invitation.revoke(now)
            except InvitationStateError as error:
                if invitation.effective_status(now) == InvitationStatus.EXPIRED:
                    invitation.status = InvitationStatus.EXPIRED
                    unit.invitations.update(invitation)
                    unit.commit()
                raise ResourceConflict(str(error)) from error
            if changed:
                unit.invitations.update(invitation)
                unit.commit()
        return invitation


class ResendInvitationUseCase:
    def __init__(
        self, factory: UnitOfWorkFactory, tokens: InvitationTokenService
    ) -> None:
        self._factory, self._tokens = factory, tokens

    def execute(
        self, list_id: UUID, invitation_id: UUID, caller_id: UUID
    ) -> IssuedInvitation:
        now: datetime = _now()
        raw_token, digest = self._tokens.issue()
        with self._factory(False) as unit:
            task_list: TaskList = _owner_list(unit, list_id, caller_id)
            invitation: Invitation | None = unit.invitations.get_for_update(
                list_id, invitation_id
            )
            if invitation is None:
                raise ResourceNotFound("Invitation not found.")
            if invitation.effective_status(now) == InvitationStatus.EXPIRED:
                unit.invitations.expire_pending(list_id, now)
                invitation.status = InvitationStatus.EXPIRED
            unit.invitations.expire_pending(list_id, now)
            if (
                unit.invitations.has_pending(list_id, invitation.recipient_email)
                and invitation.status != InvitationStatus.PENDING
            ):
                raise ResourceConflict("An active invitation already exists.")
            try:
                invitation.resend(digest, task_list.name, now)
            except InvitationStateError as error:
                raise ResourceConflict(str(error)) from error
            unit.invitations.update(invitation)
            unit.commit()
        return IssuedInvitation(invitation, raw_token)
