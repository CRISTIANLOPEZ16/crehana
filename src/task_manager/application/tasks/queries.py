from uuid import UUID

from task_manager.application.commands import QueryTasks
from task_manager.application.errors import ResourceNotFound
from task_manager.application.ports import TaskPage, UnitOfWorkFactory
from task_manager.domain.task import Task


class GetTaskUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID, task_id: UUID) -> Task:
        with self._unit_of_work_factory(False) as unit_of_work:
            task = unit_of_work.tasks.get(list_id, task_id)
            if task is None:
                raise ResourceNotFound("Task not found.")
            return task


class QueryTasksUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, command: QueryTasks) -> TaskPage:
        with self._unit_of_work_factory(True) as unit_of_work:
            return unit_of_work.task_queries.query(
                command.list_id,
                command.status.value if command.status else None,
                command.priority.value if command.priority else None,
                command.limit,
                command.offset,
            )
