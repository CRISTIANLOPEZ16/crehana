from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import field_serializer

from task_manager.domain.task import TaskPriority, TaskStatus
from task_manager.infrastructure.http.schemas.common import StrictSchema


class TaskResponse(StrictSchema):
    id: UUID
    list_id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CompletionSummaryResponse(StrictSchema):
    total_tasks: int
    completed_tasks: int
    completion_percentage: Decimal

    @field_serializer("completion_percentage")
    def serialize_percentage(self, value: Decimal) -> float:
        return float(value)


class TaskPageResponse(StrictSchema):
    items: list[TaskResponse]
    limit: int
    offset: int
    matched_tasks: int
    summary: CompletionSummaryResponse
