from uuid import UUID

from task_manager.application.commands import CreateTaskList, Unset, UpdateTaskList
from task_manager.application.errors import (
    FieldViolation,
    InvalidRequest,
    ResourceNotFound,
)
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.task_list import TaskList


class CreateTaskListUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, command: CreateTaskList) -> TaskList:
        task_list = TaskList.create(command.name, command.description)
        with self._unit_of_work_factory(False) as unit_of_work:
            unit_of_work.task_lists.create(task_list)
            unit_of_work.commit()
        return task_list


class UpdateTaskListUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID, command: UpdateTaskList) -> TaskList:
        if not isinstance(command.name, Unset) and command.name is None:
            raise InvalidRequest([FieldViolation("body.name", "Cannot be null.")])
        if isinstance(command.name, Unset) and isinstance(command.description, Unset):
            raise InvalidRequest(
                [FieldViolation("body", "PATCH body must not be empty.")]
            )
        with self._unit_of_work_factory(False) as unit_of_work:
            task_list = unit_of_work.task_lists.get_for_update(list_id)
            if task_list is None:
                raise ResourceNotFound("Task list not found.")
            previous_name = task_list.name
            previous_description = task_list.description
            name = command.name if isinstance(command.name, str) else None
            description_present = not isinstance(command.description, Unset)
            description = (
                None if isinstance(command.description, Unset) else command.description
            )
            changed = task_list.update(name, description, description_present)
            if changed:
                changed_fields = frozenset(
                    field_name
                    for field_name, previous, current in (
                        ("name", previous_name, task_list.name),
                        ("description", previous_description, task_list.description),
                    )
                    if previous != current
                )
                unit_of_work.task_lists.update(task_list, changed_fields)
            unit_of_work.commit()
            return task_list


class DeleteTaskListUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID) -> None:
        with self._unit_of_work_factory(False) as unit_of_work:
            if unit_of_work.task_lists.get_for_update(list_id) is None:
                raise ResourceNotFound("Task list not found.")
            unit_of_work.task_lists.delete(list_id)
            unit_of_work.commit()
