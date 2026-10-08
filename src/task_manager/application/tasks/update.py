from uuid import UUID

from task_manager.application.commands import Unset, UpdateTask
from task_manager.application.errors import (
    FieldViolation,
    InvalidRequest,
    ResourceNotFound,
)
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.task import Task, TaskPriority, TaskStatus


class UpdateTaskUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID, task_id: UUID, command: UpdateTask) -> Task:
        if all(
            isinstance(value, Unset)
            for value in (
                command.title,
                command.description,
                command.status,
                command.priority,
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
            task = unit_of_work.tasks.get_for_update(list_id, task_id)
            if task is None:
                raise ResourceNotFound("Task not found.")
            previous_values: dict[str, object] = {
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
            }
            title = command.title if isinstance(command.title, str) else None
            has_description = not isinstance(command.description, Unset)
            description = (
                None if isinstance(command.description, Unset) else command.description
            )
            status = command.status if isinstance(command.status, TaskStatus) else None
            priority = (
                command.priority if isinstance(command.priority, TaskPriority) else None
            )
            if task.update(title, description, has_description, status, priority):
                changed_fields = frozenset(
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
                    )
                    if previous != current
                )
                unit_of_work.tasks.update(task, changed_fields)
            unit_of_work.commit()
            return task
