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


@dataclass(frozen=True, slots=True)
class UpdateTask:
    title: str | None | Unset = UNSET
    description: str | None | Unset = UNSET
    status: TaskStatus | None | Unset = UNSET
    priority: TaskPriority | None | Unset = UNSET


@dataclass(frozen=True, slots=True)
class QueryTasks:
    list_id: UUID
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    limit: int = 20
    offset: int = 0
