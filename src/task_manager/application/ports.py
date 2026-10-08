from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from task_manager.domain.task import Task
from task_manager.domain.access import ListMembership, Participant
from task_manager.domain.task_list import TaskList
from task_manager.domain.user import User
from task_manager.domain.invitation import Invitation


@dataclass(frozen=True, slots=True)
class TaskListPage:
    items: list[TaskList]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ParticipantPage:
    items: list[Participant]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class InvitationPage:
    items: list[Invitation]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class CompletionSummary:
    total_tasks: int
    completed_tasks: int
    completion_percentage: Decimal


@dataclass(frozen=True, slots=True)
class TaskPage:
    items: list[Task]
    matched_tasks: int
    limit: int
    offset: int
    summary: CompletionSummary


class TaskListStore(Protocol):
    def create(self, task_list: TaskList) -> None: ...

    def get(self, list_id: UUID) -> TaskList | None: ...

    def get_for_update(self, list_id: UUID) -> TaskList | None: ...

    def get_for_share(self, list_id: UUID) -> TaskList | None: ...

    def update(self, task_list: TaskList, changed_fields: frozenset[str]) -> None: ...

    def delete(self, list_id: UUID) -> None: ...

    def page(self, caller_id: UUID, limit: int, offset: int) -> TaskListPage: ...

    def owner_ids(self) -> set[UUID]: ...

    def assign_missing_owner(self, owner_id: UUID) -> None: ...


class UserStore(Protocol):
    def create(self, user: User) -> None: ...

    def get(self, user_id: UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...


class MembershipStore(Protocol):
    def has_access(self, list_id: UUID, user_id: UUID) -> bool: ...

    def is_member(self, list_id: UUID, user_id: UUID) -> bool: ...

    def create(self, membership: ListMembership) -> None: ...

    def delete(self, list_id: UUID, user_id: UUID) -> bool: ...

    def page_participants(
        self, list_id: UUID, limit: int, offset: int
    ) -> ParticipantPage: ...


class InvitationStore(Protocol):
    def create(self, invitation: Invitation) -> None: ...

    def get(self, list_id: UUID, invitation_id: UUID) -> Invitation | None: ...

    def get_for_update(
        self, list_id: UUID, invitation_id: UUID
    ) -> Invitation | None: ...

    def find_by_token_hash(self, token_hash: bytes) -> Invitation | None: ...

    def find_by_token_hash_for_update(self, token_hash: bytes) -> Invitation | None: ...

    def expire_pending(self, list_id: UUID, now: datetime) -> None: ...

    def has_pending(self, list_id: UUID, recipient_email: str) -> bool: ...

    def update(self, invitation: Invitation) -> None: ...

    def page(self, list_id: UUID, limit: int, offset: int) -> InvitationPage: ...


class PasswordService(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class AccessTokenIssuer(Protocol):
    def issue(self, user_id: UUID) -> str: ...


class InvitationTokenService(Protocol):
    def issue(self) -> tuple[str, bytes]: ...

    def digest(self, token: str) -> bytes: ...


class TaskStore(Protocol):
    def create(self, task: Task) -> None: ...

    def get(self, list_id: UUID, task_id: UUID) -> Task | None: ...

    def get_for_update(self, list_id: UUID, task_id: UUID) -> Task | None: ...

    def update(self, task: Task, changed_fields: frozenset[str]) -> None: ...

    def delete(self, list_id: UUID, task_id: UUID) -> None: ...

    def clear_assignee(self, list_id: UUID, user_id: UUID) -> None: ...


class TaskQueryStore(Protocol):
    def query(
        self,
        list_id: UUID,
        status: str | None,
        priority: str | None,
        limit: int,
        offset: int,
    ) -> TaskPage: ...


class UnitOfWork(Protocol):
    task_lists: TaskListStore
    tasks: TaskStore
    task_queries: TaskQueryStore
    users: UserStore
    memberships: MembershipStore
    invitations: InvitationStore

    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[bool], AbstractContextManager[UnitOfWork]]
