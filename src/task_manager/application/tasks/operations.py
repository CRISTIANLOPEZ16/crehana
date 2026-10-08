from uuid import UUID

from task_manager.application.commands import CreateTask
from task_manager.application.errors import (
    FieldViolation,
    InvalidRequest,
    ResourceNotFound,
)
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.task import Task
from task_manager.domain.task_list import TaskList


class CreateTaskUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, command: CreateTask, caller_id: UUID) -> Task:
        with self._unit_of_work_factory(False) as unit_of_work:
            parent: TaskList | None = unit_of_work.task_lists.get_for_share(
                command.list_id
            )
            if parent is None or not unit_of_work.memberships.has_access(
                command.list_id, caller_id
            ):
                raise ResourceNotFound("Task list not found.")
            if (
                command.assignee_id is not None
                and not unit_of_work.memberships.has_access(
                    command.list_id, command.assignee_id
                )
            ):
                raise InvalidRequest(
                    [
                        FieldViolation(
                            "body.assignee_id",
                            "Assignee must be a participant in this list.",
                        )
                    ]
                )
            task: Task = Task.create(
                command.list_id,
                command.title,
                command.description,
                command.status,
                command.priority,
                command.assignee_id,
            )
            unit_of_work.tasks.create(task)
            unit_of_work.commit()
        return task


class DeleteTaskUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID, task_id: UUID, caller_id: UUID) -> None:
        with self._unit_of_work_factory(False) as unit_of_work:
            parent: TaskList | None = unit_of_work.task_lists.get_for_share(list_id)
            if parent is None or not unit_of_work.memberships.has_access(
                list_id, caller_id
            ):
                raise ResourceNotFound("Task not found.")
            if unit_of_work.tasks.get_for_update(list_id, task_id) is None:
                raise ResourceNotFound("Task not found.")
            unit_of_work.tasks.delete(list_id, task_id)
            unit_of_work.commit()
