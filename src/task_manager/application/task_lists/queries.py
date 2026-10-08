from uuid import UUID

from task_manager.application.commands import ListTaskLists
from task_manager.application.errors import ResourceNotFound
from task_manager.application.ports import TaskListPage, UnitOfWorkFactory
from task_manager.domain.task_list import TaskList


class GetTaskListUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID) -> TaskList:
        with self._unit_of_work_factory(False) as unit_of_work:
            task_list = unit_of_work.task_lists.get(list_id)
            if task_list is None:
                raise ResourceNotFound("Task list not found.")
            return task_list


class ListTaskListsUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, command: ListTaskLists) -> TaskListPage:
        with self._unit_of_work_factory(True) as unit_of_work:
            return unit_of_work.task_lists.page(command.limit, command.offset)
