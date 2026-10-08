from uuid import UUID

from task_manager.application.errors import (
    ResourceConflict,
    ResourceForbidden,
    ResourceNotFound,
)
from task_manager.application.ports import ParticipantPage, UnitOfWorkFactory
from task_manager.domain.task_list import TaskList


class ListParticipantsUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(
        self, list_id: UUID, caller_id: UUID, limit: int, offset: int
    ) -> ParticipantPage:
        with self._unit_of_work_factory(True) as unit_of_work:
            if not unit_of_work.memberships.has_access(list_id, caller_id):
                raise ResourceNotFound("Task list not found.")
            return unit_of_work.memberships.page_participants(list_id, limit, offset)


class RemoveListMemberUseCase:
    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, list_id: UUID, caller_id: UUID, member_id: UUID) -> None:
        with self._unit_of_work_factory(False) as unit_of_work:
            task_list: TaskList | None = unit_of_work.task_lists.get_for_update(list_id)
            if task_list is None:
                raise ResourceNotFound("Task list not found.")
            if task_list.owner_id != caller_id:
                if unit_of_work.memberships.has_access(list_id, caller_id):
                    raise ResourceForbidden("Only the owner can remove members.")
                raise ResourceNotFound("Task list not found.")
            if member_id == task_list.owner_id:
                raise ResourceConflict("The list owner cannot be removed.")
            if not unit_of_work.memberships.is_member(list_id, member_id):
                raise ResourceNotFound("List member not found.")
            unit_of_work.tasks.clear_assignee(list_id, member_id)
            unit_of_work.memberships.delete(list_id, member_id)
            unit_of_work.commit()
