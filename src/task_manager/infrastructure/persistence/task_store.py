from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from task_manager.application.errors import ResourceNotFound
from task_manager.domain.task import Task
from task_manager.infrastructure.persistence.task_list_record import TaskListRecord
from task_manager.infrastructure.persistence.task_record import TaskRecord


class SQLAlchemyTaskStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, task: Task) -> None:
        parent_id: UUID | None = self._session.scalar(
            select(TaskListRecord.id)
            .where(TaskListRecord.id == task.list_id)
            .with_for_update(read=True, key_share=True)
        )
        if parent_id is None:
            raise ResourceNotFound("Task list not found.")
        self._session.add(
            TaskRecord(
                id=task.id,
                list_id=task.list_id,
                title=task.title,
                description=task.description,
                status=task.status.value,
                priority=task.priority.value,
                assignee_id=task.assignee_id,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        )

    def get(self, list_id: UUID, task_id: UUID) -> Task | None:
        record: TaskRecord | None = self._session.scalar(
            select(TaskRecord).where(
                TaskRecord.id == task_id,
                TaskRecord.list_id == list_id,
            )
        )
        return record.to_domain() if record is not None else None

    def get_for_update(self, list_id: UUID, task_id: UUID) -> Task | None:
        parent_id: UUID | None = self._session.scalar(
            select(TaskListRecord.id)
            .where(TaskListRecord.id == list_id)
            .with_for_update(read=True, key_share=True)
        )
        if parent_id is None:
            return None
        record: TaskRecord | None = self._session.scalar(
            select(TaskRecord)
            .where(TaskRecord.id == task_id, TaskRecord.list_id == list_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return record.to_domain() if record is not None else None

    def update(self, task: Task, changed_fields: frozenset[str]) -> None:
        record: TaskRecord | None = self._session.scalar(
            select(TaskRecord)
            .where(TaskRecord.id == task.id, TaskRecord.list_id == task.list_id)
            .execution_options(populate_existing=True)
        )
        if record is None:
            raise ResourceNotFound("Task not found.")
        if "title" in changed_fields:
            record.title = task.title
        if "description" in changed_fields:
            record.description = task.description
        if "status" in changed_fields:
            record.status = task.status.value
        if "priority" in changed_fields:
            record.priority = task.priority.value
        if "assignee_id" in changed_fields:
            record.assignee_id = task.assignee_id
        record.updated_at = task.updated_at

    def delete(self, list_id: UUID, task_id: UUID) -> None:
        record: TaskRecord | None = self._session.scalar(
            select(TaskRecord).where(
                TaskRecord.id == task_id,
                TaskRecord.list_id == list_id,
            )
        )
        if record is None:
            raise ResourceNotFound("Task not found.")
        self._session.delete(record)

    def clear_assignee(self, list_id: UUID, user_id: UUID) -> None:
        records: list[TaskRecord] = list(
            self._session.scalars(
                select(TaskRecord)
                .where(
                    TaskRecord.list_id == list_id,
                    TaskRecord.assignee_id == user_id,
                )
                .order_by(TaskRecord.id)
                .with_for_update()
            )
        )
        for record in records:
            task: Task = record.to_domain()
            task.update(None, None, False, None, None, None, True)
            record.assignee_id = task.assignee_id
            record.updated_at = task.updated_at
