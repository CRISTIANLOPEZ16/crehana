from pydantic import BaseModel, ConfigDict, Field

from task_manager.domain.task import TaskPriority, TaskStatus


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictSchema):
    status: str


class ErrorDetail(StrictSchema):
    field: str
    message: str


class ErrorResponse(StrictSchema):
    code: str
    message: str
    details: list[ErrorDetail]


class PaginationQuery(StrictSchema):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class TaskQuery(PaginationQuery):
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
