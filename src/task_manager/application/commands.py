from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias
from uuid import UUID

from task_manager.domain.task import TaskPriority, TaskStatus


class _Unset(Enum):
    VALUE = "unset"


Unset: TypeAlias = _Unset
UNSET = _Unset.VALUE


@dataclass(frozen=True, slots=True)
class CreateTaskList:
    name: str
    owner_id: UUID
    description: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateTaskList:
    name: str | None | Unset = UNSET
    description: str | None | Unset = UNSET


@dataclass(frozen=True, slots=True)
class ListTaskLists:
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class CreateTask:
    list_id: UUID
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UpdateTask:
    title: str | None | Unset = UNSET
    description: str | None | Unset = UNSET
    status: TaskStatus | None | Unset = UNSET
    priority: TaskPriority | None | Unset = UNSET
    assignee_id: UUID | None | Unset = UNSET


@dataclass(frozen=True, slots=True)
class QueryTasks:
    list_id: UUID
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class RegisterAccount:
    display_name: str
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginAccount:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class CreateInvitation:
    list_id: UUID
    invited_by_id: UUID
    recipient_email: str


@dataclass(frozen=True, slots=True)
class AcceptInvitation:
    acceptance_token: str
    user_id: UUID


@dataclass(frozen=True, slots=True)
class InvitationPageQuery:
    list_id: UUID
    caller_id: UUID
    limit: int = 20
    offset: int = 0
