from datetime import UTC, datetime, timedelta

from task_manager.domain.errors import DomainValidationError, FieldViolation


def normalize_required_text(value: str, field: str, maximum: int) -> str:
    normalized_value: str = value.strip()
    if "\x00" in normalized_value:
        raise DomainValidationError(
            [FieldViolation(field, "Must not contain NUL characters.")]
        )
    if not normalized_value:
        raise DomainValidationError([FieldViolation(field, "Must not be blank.")])
    if len(normalized_value) > maximum:
        raise DomainValidationError(
            [FieldViolation(field, f"Must be at most {maximum} characters.")]
        )
    return normalized_value


def normalize_description(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    normalized_value: str = value.strip()
    if not normalized_value:
        return None
    if "\x00" in normalized_value:
        raise DomainValidationError(
            [FieldViolation(field, "Must not contain NUL characters.")]
        )
    if len(normalized_value) > maximum:
        raise DomainValidationError(
            [FieldViolation(field, f"Must be at most {maximum} characters.")]
        )
    return normalized_value


def initial_timestamp() -> datetime:
    return datetime.now(UTC)


def changed_timestamp(previous: datetime) -> datetime:
    return max(datetime.now(UTC), previous + timedelta(microseconds=1))
