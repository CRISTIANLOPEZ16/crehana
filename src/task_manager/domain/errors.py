from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldViolation:
    field: str
    message: str


class DomainValidationError(Exception):
    def __init__(self, violations: list[FieldViolation]) -> None:
        self.violations = violations
        super().__init__("Request validation failed.")
