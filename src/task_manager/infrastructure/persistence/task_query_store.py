from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from task_manager.application.errors import ResourceNotFound
from task_manager.application.ports import CompletionSummary, TaskPage
from task_manager.infrastructure.persistence.task_list_record import TaskListRecord
from task_manager.infrastructure.persistence.task_record import TaskRecord


class SQLAlchemyTaskQueryStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def query(
        self,
        list_id: UUID,
        status: str | None,
        priority: str | None,
        limit: int,
        offset: int,
    ) -> TaskPage:
        if (
            self._session.scalar(
                select(TaskListRecord.id).where(TaskListRecord.id == list_id)
            )
            is None
        ):
            raise ResourceNotFound("Task list not found.")
        filters = [TaskRecord.list_id == list_id]
        if status is not None:
            filters.append(TaskRecord.status == status)
        if priority is not None:
            filters.append(TaskRecord.priority == priority)
        matched_tasks = int(
            self._session.scalar(
                select(func.count()).select_from(TaskRecord).where(*filters)
            )
            or 0
        )
        total_tasks, completed_tasks = self._session.execute(
            select(
                func.count(TaskRecord.id),
                func.count(TaskRecord.id).filter(TaskRecord.status == "completed"),
            ).where(TaskRecord.list_id == list_id)
        ).one()
        total_count = int(total_tasks or 0)
        completed_count = int(completed_tasks or 0)
        percentage = self._completion_percentage(total_count, completed_count)
        records = list(
            self._session.scalars(
                select(TaskRecord)
                .where(*filters)
                .order_by(TaskRecord.created_at, TaskRecord.id)
                .limit(limit)
                .offset(offset)
            )
        )
        summary = CompletionSummary(total_count, completed_count, percentage)
        return TaskPage(
            [record.to_domain() for record in records],
            matched_tasks,
            limit,
            offset,
            summary,
        )

    @staticmethod
    def _completion_percentage(total_tasks: int, completed_tasks: int) -> Decimal:
        if total_tasks == 0:
            return Decimal("0")
        return (Decimal(completed_tasks) * 100 / Decimal(total_tasks)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
