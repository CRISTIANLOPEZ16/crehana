from uuid import UUID

from task_manager.application.commands import CreateTask
from task_manager.application.errors import ResourceNotFound
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.task import Task


class CreateTaskUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, command: CreateTask) -> Task:
        task = Task.create(
            command.list_id,
            command.title,
            command.description,
            command.status,
            command.priority,
        )
        with self._unit_of_work_factory(False) as unit_of_work:
            unit_of_work.tasks.create(task)
            unit_of_work.commit()
        return task


class DeleteTaskUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID, task_id: UUID) -> None:
        with self._unit_of_work_factory(False) as unit_of_work:
            if unit_of_work.tasks.get_for_update(list_id, task_id) is None:
                raise ResourceNotFound("Task not found.")
            unit_of_work.tasks.delete(list_id, task_id)
            unit_of_work.commit()
