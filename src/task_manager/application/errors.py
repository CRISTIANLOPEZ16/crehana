from task_manager.domain.errors import (
    DomainValidationError as InvalidRequest,
    FieldViolation,
)

__all__ = ["InvalidRequest", "FieldViolation", "ResourceNotFound"]


class ResourceNotFound(Exception):
    pass
