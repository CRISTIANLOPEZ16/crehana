from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import jwt
import pytest

from tests.fixtures.api import RunningApi, TEST_SIGNING_KEY

pytestmark = pytest.mark.e2e


def _signed_token(server: RunningApi, claims: dict[str, object]) -> str:
    return jwt.encode(claims, TEST_SIGNING_KEY, algorithm="HS256")


def test_registration_form_login_and_current_profile(api_client: httpx.Client) -> None:
    registration = api_client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "  Collaboration User  ",
            "email": " New.User+tag@EXAMPLE.COM ",
            "password": "a long Unicode 🦄 passphrase",
        },
    )
    assert registration.status_code == 201
    assert registration.headers["location"] == "/api/v1/auth/me"
    profile = registration.json()
    assert profile["display_name"] == "Collaboration User"
    assert profile["email"] == "new.user+tag@example.com"
    assert "password" not in profile
    assert "password_hash" not in profile

    login = api_client.post(
        "/api/v1/auth/login",
        data={
            "username": "NEW.USER+tag@example.com",
            "password": "a long Unicode 🦄 passphrase",
        },
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["expires_in"] == 1800
    api_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    current_user = api_client.get("/api/v1/auth/me")
    assert current_user.status_code == 200
    assert current_user.json() == profile


def test_duplicate_canonical_email_and_bad_password_use_generic_login_error(
    api_client: httpx.Client,
) -> None:
    body: dict[str, str] = {
        "display_name": "User",
        "email": " Person@example.com ",
        "password": "a sufficiently long password",
    }
    assert api_client.post("/api/v1/auth/register", json=body).status_code == 201
    duplicate = {**body, "email": "person@EXAMPLE.COM"}
    duplicate_response = api_client.post("/api/v1/auth/register", json=duplicate)
    assert duplicate_response.status_code == 409

    wrong_password = api_client.post(
        "/api/v1/auth/login",
        data={"username": "person@example.com", "password": "another wrong password"},
    )
    unknown_account = api_client.post(
        "/api/v1/auth/login",
        data={"username": "unknown@example.com", "password": "another wrong password"},
    )
    assert wrong_password.status_code == unknown_account.status_code == 401
    assert wrong_password.json() == unknown_account.json()


def test_invalid_access_tokens_fail_with_bearer_challenge(
    api_server: RunningApi,
) -> None:
    now: datetime = datetime.now(UTC)
    valid_claims: dict[str, object] = {
        "sub": "00000000-0000-4000-8000-000000000001",
        "iat": now,
        "exp": now + timedelta(minutes=30),
        "iss": api_server.settings["JWT_ISSUER"],
        "aud": api_server.settings["JWT_AUDIENCE"],
    }
    valid_token: str = _signed_token(api_server, valid_claims)
    disallowed_algorithm: str = jwt.encode(
        valid_claims, TEST_SIGNING_KEY, algorithm="HS384"
    )
    missing_expiration_claims: dict[str, object] = {
        claim_name: claim_value
        for claim_name, claim_value in valid_claims.items()
        if claim_name != "exp"
    }
    tampered_token: str = valid_token[:-1] + ("A" if valid_token[-1] != "A" else "B")
    invalid_tokens: list[str] = [
        "malformed.token.value",
        tampered_token,
        disallowed_algorithm,
        _signed_token(
            api_server,
            {**valid_claims, "exp": now - timedelta(seconds=1)},
        ),
        _signed_token(api_server, {**valid_claims, "aud": "wrong-audience"}),
        _signed_token(api_server, {**valid_claims, "iss": "wrong-issuer"}),
        _signed_token(api_server, missing_expiration_claims),
        _signed_token(
            api_server,
            {**valid_claims, "sub": str(uuid4())},
        ),
    ]
    for token in invalid_tokens:
        response = api_server.client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert "password_hash" not in response.text


def test_public_registration_schema_and_documentation_visibility(
    api_server: RunningApi,
) -> None:
    response = api_server.client.post(
        "/api/v1/auth/register",
        json={
            "display_name": "Short",
            "email": "valid@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "body.password"
    unsupported_form_field = api_server.client.post(
        "/api/v1/auth/login",
        data={"username": "valid@example.com", "password": "x", "extra": "no"},
    )
    assert unsupported_form_field.status_code == 422
    repeated_form_field = api_server.client.post(
        "/api/v1/auth/login",
        content=(
            "username=valid%40example.com&username=other%40example.com&"
            "password=a+passphrase"
        ),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert repeated_form_field.status_code == 422
    assert api_server.client.get("/openapi.json").status_code == 404
