from datetime import UTC

import pytest

from task_manager.domain.errors import DomainValidationError
from task_manager.domain.user import User, canonicalize_email, validate_password

pytestmark = pytest.mark.unit


def test_email_canonicalization_trims_case_and_converts_idna() -> None:
    assert canonicalize_email("  Person+tag@EXAMPLE.COM ") == "person+tag@example.com"
    assert canonicalize_email("User@bücher.example") == "user@xn--bcher-kva.example"
    assert canonicalize_email("first.last@example.com") == "first.last@example.com"
    with pytest.raises(DomainValidationError):
        canonicalize_email("bad\u3000@example.com")


@pytest.mark.parametrize("password", ["short", "x" * 129, "bad\ud800unicode"])
def test_password_policy_rejects_short_oversized_and_malformed_unicode(
    password: str,
) -> None:
    with pytest.raises(DomainValidationError):
        validate_password(password)


def test_password_policy_preserves_whitespace_and_unicode() -> None:
    password: str = "  " + "🦄" * 14 + "  "
    validate_password(password)
    user: User = User.register("  Ada  ", "ADA@example.com", "argon2-hash")
    assert user.display_name == "Ada"
    assert user.email == "ada@example.com"
    assert user.created_at == user.updated_at
    assert user.created_at.tzinfo == UTC
    assert "argon2-hash" not in repr(user)
