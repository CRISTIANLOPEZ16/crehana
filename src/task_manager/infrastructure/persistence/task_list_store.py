from uuid import UUID

from sqlalchemy import exists, func, or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from task_manager.application.errors import ResourceNotFound
from task_manager.application.ports import TaskListPage
from task_manager.domain.task_list import TaskList
from task_manager.infrastructure.persistence.task_list_record import TaskListRecord
from task_manager.infrastructure.persistence.membership_record import MembershipRecord


class SQLAlchemyTaskListStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, task_list: TaskList) -> None:
        self._session.add(
            TaskListRecord(
                id=task_list.id,
                owner_id=task_list.owner_id,
                name=task_list.name,
                description=task_list.description,
                created_at=task_list.created_at,
                updated_at=task_list.updated_at,
            )
        )

    def get(self, list_id: UUID) -> TaskList | None:
        record: TaskListRecord | None = self._session.get(TaskListRecord, list_id)
        return record.to_domain() if record is not None else None

    def get_for_update(self, list_id: UUID) -> TaskList | None:
        record: TaskListRecord | None = self._session.scalar(
            select(TaskListRecord).where(TaskListRecord.id == list_id).with_for_update()
        )
        return record.to_domain() if record is not None else None

    def get_for_share(self, list_id: UUID) -> TaskList | None:
        record: TaskListRecord | None = self._session.scalar(
            select(TaskListRecord)
            .where(TaskListRecord.id == list_id)
            .with_for_update(read=True, key_share=True)
        )
        return record.to_domain() if record is not None else None

    def update(self, task_list: TaskList, changed_fields: frozenset[str]) -> None:
        record: TaskListRecord | None = self._session.get(TaskListRecord, task_list.id)
        if record is None:
            raise ResourceNotFound("Task list not found.")
        if "name" in changed_fields:
            record.name = task_list.name
        if "description" in changed_fields:
            record.description = task_list.description
        record.updated_at = task_list.updated_at

    def delete(self, list_id: UUID) -> None:
        record: TaskListRecord | None = self._session.get(TaskListRecord, list_id)
        if record is None:
            raise ResourceNotFound("Task list not found.")
        self._session.delete(record)

    def page(self, caller_id: UUID, limit: int, offset: int) -> TaskListPage:
        membership_exists: ColumnElement[bool] = exists(
            select(MembershipRecord.list_id).where(
                MembershipRecord.list_id == TaskListRecord.id,
                MembershipRecord.user_id == caller_id,
            )
        )
        visible_condition: ColumnElement[bool] = or_(
            TaskListRecord.owner_id == caller_id, membership_exists
        )
        total: int = int(
            self._session.scalar(
                select(func.count())
                .select_from(TaskListRecord)
                .where(visible_condition)
            )
            or 0
        )
        records: list[TaskListRecord] = []
        if offset < total:
            records = list(
                self._session.scalars(
                    select(TaskListRecord)
                    .where(visible_condition)
                    .order_by(TaskListRecord.created_at, TaskListRecord.id)
                    .limit(limit)
                    .offset(offset)
                )
            )
        return TaskListPage(
            [record.to_domain() for record in records], total, limit, offset
        )

    def owner_ids(self) -> set[UUID]:
        return set(
            self._session.scalars(
                select(TaskListRecord.owner_id).where(
                    TaskListRecord.owner_id.is_not(None)
                )
            )
        )

    def assign_missing_owner(self, owner_id: UUID) -> None:
        self._session.execute(
            update(TaskListRecord)
            .where(TaskListRecord.owner_id.is_(None))
            .values(owner_id=owner_id)
        )
