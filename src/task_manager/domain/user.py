from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from email_validator import EmailNotValidError, ValidatedEmail, validate_email

from task_manager.domain.errors import DomainValidationError, FieldViolation
from task_manager.domain.validation import initial_timestamp, normalize_required_text


def canonicalize_email(email_address: str) -> str:
    trimmed_email: str = email_address.strip()
    try:
        validated_email: ValidatedEmail = validate_email(
            trimmed_email, allow_smtputf8=False, check_deliverability=False
        )
    except EmailNotValidError as error:
        raise DomainValidationError(
            [FieldViolation("email", "Enter a valid email address.")]
        ) from error
    local_part: str = validated_email.normalized.split("@", maxsplit=1)[0]
    if not local_part.isascii():
        raise DomainValidationError(
            [FieldViolation("email", "The email local part must use ASCII.")]
        )
    domain_name: str = validated_email.normalized.split("@", maxsplit=1)[1]
    ascii_domain: str = domain_name.encode("idna").decode("ascii").lower()
    canonical_email: str = f"{local_part.lower()}@{ascii_domain}"
    if len(canonical_email) > 254:
        raise DomainValidationError(
            [FieldViolation("email", "Must be at most 254 characters.")]
        )
    return canonical_email


def validate_password(password: str) -> None:
    if not 15 <= len(password) <= 128:
        raise DomainValidationError(
            [FieldViolation("password", "Must contain 15 to 128 Unicode characters.")]
        )
    try:
        password.encode("utf-8")
    except UnicodeEncodeError as error:
        raise DomainValidationError(
            [FieldViolation("password", "Must contain valid Unicode text.")]
        ) from error


@dataclass(slots=True)
class User:
    id: UUID
    display_name: str
    email: str
    password_hash: str = field(repr=False)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def register(
        cls, display_name: str, email_address: str, password_hash: str
    ) -> User:
        normalized_name: str = normalize_required_text(
            display_name, "display_name", 100
        )
        canonical_email: str = canonicalize_email(email_address)
        if not password_hash:
            raise DomainValidationError(
                [FieldViolation("password", "Password hash is required.")]
            )
        created_at: datetime = initial_timestamp()
        return cls(
            id=uuid4(),
            display_name=normalized_name,
            email=canonical_email,
            password_hash=password_hash,
            created_at=created_at,
            updated_at=created_at,
        )
