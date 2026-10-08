from task_manager.domain.errors import (
    DomainValidationError as InvalidRequest,
    FieldViolation,
)

__all__ = [
    "InvalidRequest",
    "FieldViolation",
    "ResourceNotFound",
    "ResourceForbidden",
    "ResourceConflict",
    "AuthenticationFailed",
]


class ResourceNotFound(Exception):
    pass


class ResourceForbidden(Exception):
    pass


class ResourceConflict(Exception):
    pass


class AuthenticationFailed(Exception):
    pass
