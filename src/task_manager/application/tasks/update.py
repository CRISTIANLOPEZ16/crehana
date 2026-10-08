from uuid import UUID

from task_manager.application.commands import Unset, UpdateTask
from task_manager.application.errors import (
    FieldViolation,
    InvalidRequest,
    ResourceNotFound,
)
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.task import Task, TaskPriority, TaskStatus
from task_manager.domain.task_list import TaskList


class UpdateTaskUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, list_id: UUID, task_id: UUID, caller_id: UUID, command: UpdateTask
    ) -> Task:
        if all(
            isinstance(value, Unset)
            for value in (
                command.title,
                command.description,
                command.status,
                command.priority,
                command.assignee_id,
            )
        ):
            raise InvalidRequest(
                [FieldViolation("body", "PATCH body must not be empty.")]
            )
        for field_name, value in (
            ("title", command.title),
            ("status", command.status),
            ("priority", command.priority),
        ):
            if not isinstance(value, Unset) and value is None:
                raise InvalidRequest(
                    [FieldViolation(f"body.{field_name}", "Cannot be null.")]
                )
        with self._unit_of_work_factory(False) as unit_of_work:
            parent: TaskList | None = unit_of_work.task_lists.get_for_share(list_id)
            if parent is None or not unit_of_work.memberships.has_access(
                list_id, caller_id
            ):
                raise ResourceNotFound("Task not found.")
            task: Task | None = unit_of_work.tasks.get_for_update(list_id, task_id)
            if task is None:
                raise ResourceNotFound("Task not found.")
            previous_values: dict[str, object] = {
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "assignee_id": task.assignee_id,
            }
            title: str | None = (
                command.title if isinstance(command.title, str) else None
            )
            has_description: bool = not isinstance(command.description, Unset)
            description: str | None = (
                None if isinstance(command.description, Unset) else command.description
            )
            status: TaskStatus | None = (
                command.status if isinstance(command.status, TaskStatus) else None
            )
            priority: TaskPriority | None = (
                command.priority if isinstance(command.priority, TaskPriority) else None
            )
            assignee_present: bool = not isinstance(command.assignee_id, Unset)
            assignee_id: UUID | None = (
                command.assignee_id if isinstance(command.assignee_id, UUID) else None
            )
            if assignee_id is not None and not unit_of_work.memberships.has_access(
                list_id, assignee_id
            ):
                raise InvalidRequest(
                    [
                        FieldViolation(
                            "body.assignee_id",
                            "Assignee must be a participant in this list.",
                        )
                    ]
                )
            if task.update(
                title,
                description,
                has_description,
                status,
                priority,
                assignee_id,
                assignee_present,
            ):
                changed_fields: frozenset[str] = frozenset(
                    field_name
                    for field_name, previous, current in (
                        ("title", previous_values["title"], task.title),
                        (
                            "description",
                            previous_values["description"],
                            task.description,
                        ),
                        ("status", previous_values["status"], task.status),
                        ("priority", previous_values["priority"], task.priority),
                        (
                            "assignee_id",
                            previous_values["assignee_id"],
                            task.assignee_id,
                        ),
                    )
                    if previous != current
                )
                unit_of_work.tasks.update(task, changed_fields)
            unit_of_work.commit()
            return task
