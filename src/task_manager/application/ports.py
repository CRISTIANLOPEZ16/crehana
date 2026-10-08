from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from task_manager.domain.task import Task
from task_manager.domain.task_list import TaskList


@dataclass(frozen=True, slots=True)
class TaskListPage:
    items: list[TaskList]
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

    def update(self, task_list: TaskList, changed_fields: frozenset[str]) -> None: ...

    def delete(self, list_id: UUID) -> None: ...

    def page(self, limit: int, offset: int) -> TaskListPage: ...


class TaskStore(Protocol):
    def create(self, task: Task) -> None: ...

    def get(self, list_id: UUID, task_id: UUID) -> Task | None: ...

    def get_for_update(self, list_id: UUID, task_id: UUID) -> Task | None: ...

    def update(self, task: Task, changed_fields: frozenset[str]) -> None: ...

    def delete(self, list_id: UUID, task_id: UUID) -> None: ...


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

    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[bool], AbstractContextManager[UnitOfWork]]
