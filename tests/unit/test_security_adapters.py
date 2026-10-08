from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from task_manager.infrastructure.security.config import TokenConfiguration
from task_manager.infrastructure.security.passwords import Argon2PasswordService
from task_manager.infrastructure.security.tokens import AccessTokenService

pytestmark = pytest.mark.unit


def test_argon2id_hash_uses_approved_cost_and_verifies_password() -> None:
    password_service = Argon2PasswordService()
    encoded_hash: str = password_service.hash("a long secure passphrase")

    assert encoded_hash.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert password_service.verify("a long secure passphrase", encoded_hash)
    assert not password_service.verify("different passphrase", encoded_hash)


def test_jwt_uses_fixed_hs256_and_required_standard_claims() -> None:
    configuration = TokenConfiguration(
        "test-only-signing-key-for-authentication-tests-0123456789abcdef",
        "task-manager-tests",
        "task-manager-test-clients",
    )
    token_service = AccessTokenService(configuration)
    user_id = uuid4()
    issued_token: str = token_service.issue(user_id)

    assert token_service.verify(issued_token) == user_id
    disallowed_algorithm_token: str = jwt.encode(
        {
            "sub": str(user_id),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=1),
            "iss": configuration.issuer,
            "aud": configuration.audience,
        },
        configuration.signing_key,
        algorithm="HS384",
    )
    with pytest.raises(jwt.InvalidTokenError):
        token_service.verify(disallowed_algorithm_token)


def test_jwt_rejects_wrong_issuer_audience_and_missing_claims() -> None:
    configuration = TokenConfiguration("s" * 32, "expected-issuer", "expected-aud")
    token_service = AccessTokenService(configuration)
    now: datetime = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=1),
        "iss": "wrong-issuer",
        "aud": "expected-aud",
    }
    wrong_issuer: str = jwt.encode(claims, "s" * 32, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        token_service.verify(wrong_issuer)
    missing_subject: str = jwt.encode(
        {key: value for key, value in claims.items() if key != "sub"},
        "s" * 32,
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError):
        token_service.verify(missing_subject)


def test_token_configuration_requires_secret_issuer_and_audience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JWT_SIGNING_KEY", raising=False)
    monkeypatch.delenv("JWT_ISSUER", raising=False)
    monkeypatch.delenv("JWT_AUDIENCE", raising=False)
    with pytest.raises(RuntimeError, match="configuration is incomplete"):
        TokenConfiguration.from_environment()
