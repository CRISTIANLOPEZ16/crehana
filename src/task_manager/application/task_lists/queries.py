from uuid import UUID

from task_manager.application.commands import ListTaskLists
from task_manager.application.errors import ResourceNotFound
from task_manager.application.ports import TaskListPage, UnitOfWorkFactory
from task_manager.domain.task_list import TaskList


class GetTaskListUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID, caller_id: UUID) -> TaskList:
        with self._unit_of_work_factory(True) as unit_of_work:
            task_list: TaskList | None = unit_of_work.task_lists.get(list_id)
            if task_list is None or not unit_of_work.memberships.has_access(
                list_id, caller_id
            ):
                raise ResourceNotFound("Task list not found.")
            return task_list


class ListTaskListsUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, command: ListTaskLists, caller_id: UUID) -> TaskListPage:
        with self._unit_of_work_factory(True) as unit_of_work:
            return unit_of_work.task_lists.page(
                caller_id, command.limit, command.offset
            )
