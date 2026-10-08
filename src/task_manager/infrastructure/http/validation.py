import re

from fastapi import Request

from task_manager.application.errors import InvalidRequest
from task_manager.domain.errors import FieldViolation
from task_manager.infrastructure.http.schemas.common import PaginationQuery

_INTEGER_PATTERN = re.compile(r"^[+-]?[0-9]+$")


def validate_query(request: Request, allowed: set[str]) -> dict[str, str]:
    violations: list[FieldViolation] = []
    for key in request.query_params.keys():
        if key not in allowed:
            violations.append(
                FieldViolation(f"query.{key}", "Unknown query parameter.")
            )
        if len(request.query_params.getlist(key)) > 1:
            violations.append(
                FieldViolation(f"query.{key}", "May be provided only once.")
            )
    if violations:
        raise InvalidRequest(violations)
    return {key: request.query_params[key] for key in request.query_params.keys()}


def pagination_query(values: dict[str, str]) -> PaginationQuery:
    limit: int = _integer_query(values, "limit", 20)
    offset: int = _integer_query(values, "offset", 0)
    violations: list[FieldViolation] = []
    if not 1 <= limit <= 100:
        violations.append(FieldViolation("query.limit", "Must be between 1 and 100."))
    if offset < 0:
        violations.append(FieldViolation("query.offset", "Must be non-negative."))
    if violations:
        raise InvalidRequest(violations)
    return PaginationQuery(limit=limit, offset=offset)


def _integer_query(values: dict[str, str], name: str, default: int) -> int:
    value: str | None = values.get(name)
    if value is None:
        return default
    if not _INTEGER_PATTERN.fullmatch(value):
        raise InvalidRequest([FieldViolation(f"query.{name}", "Must be an integer.")])
    try:
        return int(value)
    except ValueError as exception:
        raise InvalidRequest(
            [FieldViolation(f"query.{name}", "Must be an integer.")]
        ) from exception
