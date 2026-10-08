from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from sqlalchemy import Engine, text

from task_manager.domain.user import User
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.fixtures.api import RunningApi, TEST_SIGNING_KEY

pytestmark = pytest.mark.e2e


def _authorize(client: httpx.Client, server: RunningApi, user_id: str) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=30),
            "iss": server.settings["JWT_ISSUER"],
            "aud": server.settings["JWT_AUDIENCE"],
        },
        TEST_SIGNING_KEY,
        algorithm="HS256",
    )
    client.headers["Authorization"] = f"Bearer {token}"


def test_invitation_create_accept_remove_and_safe_inspection(
    api_server: RunningApi, postgres_engine: Engine
) -> None:
    client = api_server.client
    task_list = client.post(
        "/api/v1/task-lists", json={"name": "Invitation list"}
    ).json()
    list_id = task_list["id"]
    recipient = User.register("Invitee", "invitee@example.com", "test-hash")
    outsider = User.register("Outsider", "outsider@example.com", "test-hash")
    factory = create_unit_of_work_factory(postgres_engine)
    with factory(False) as unit:
        unit.users.create(recipient)
        unit.users.create(outsider)
        unit.commit()
    path = f"/api/v1/task-lists/{list_id}/invitations"
    created = client.post(path, json={"recipient_email": " INVITEE@EXAMPLE.COM "})
    assert created.status_code == 201
    body = created.json()
    token = body["acceptance_token"]
    invitation_id = body["id"]
    assert body["status"] == "pending"
    assert body["simulation"]["status"] == "simulated"
    assert body["simulation"]["recipient"] == "invitee@example.com"
    assert "acceptance_token" not in client.get(path).json()["items"][0]
    assert "token_hash" not in str(client.get(f"{path}/{invitation_id}").json())
    assert (
        client.post(path, json={"recipient_email": "invitee@example.com"}).status_code
        == 409
    )
    assert (
        client.post(path, json={"recipient_email": "bad"}).json()["details"][0]["field"]
        == "body.recipient_email"
    )

    _authorize(client, api_server, str(outsider.id))
    assert client.get(path).status_code == 404
    _authorize(client, api_server, str(recipient.id))
    assert client.get(f"/api/v1/task-lists/{list_id}").status_code == 404
    assert (
        client.post(
            "/api/v1/invitations/accept", json={"acceptance_token": token}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/invitations/accept", json={"acceptance_token": token}
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/task-lists/{list_id}").status_code == 200
    assert client.get(path).status_code == 403

    _authorize(client, api_server, task_list["owner_id"])
    assert client.post(f"{path}/{invitation_id}/resend").status_code == 409
    member_removal = client.delete(
        f"/api/v1/task-lists/{list_id}/participants/{recipient.id}"
    )
    assert member_removal.status_code == 204
    _authorize(client, api_server, str(recipient.id))
    retry_after_removal = client.post(
        "/api/v1/invitations/accept", json={"acceptance_token": token}
    )
    assert retry_after_removal.status_code == 409

    _authorize(client, api_server, task_list["owner_id"])
    other = client.post(path, json={"recipient_email": "later@example.com"}).json()
    resend = client.post(f"{path}/{other['id']}/resend")
    assert resend.status_code == 200
    rotated = resend.json()["acceptance_token"]
    assert rotated != other["acceptance_token"]
    _authorize(client, api_server, str(outsider.id))
    assert (
        client.post(
            "/api/v1/invitations/accept",
            json={"acceptance_token": other["acceptance_token"]},
        ).status_code
        == 404
    )
    _authorize(client, api_server, task_list["owner_id"])
    revoked = client.post(f"{path}/{other['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert client.post(f"{path}/{other['id']}/revoke").status_code == 200
    assert client.post(f"{path}/{other['id']}/resend").status_code == 409
    assert "acceptance_token" not in str(client.get(path).json())

    expiring = client.post(path, json={"recipient_email": "expiry@example.com"}).json()
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE invitations SET created_at=:created, "
                "expires_at=:expiry WHERE id=:invitation_id"
            ),
            {
                "created": datetime.now(UTC) - timedelta(days=8),
                "expiry": datetime.now(UTC) - timedelta(seconds=1),
                "invitation_id": expiring["id"],
            },
        )
    assert client.get(f"{path}/{expiring['id']}").json()["status"] == "expired"
    assert client.post(f"{path}/{expiring['id']}/revoke").status_code == 409
    assert client.post(f"{path}/{expiring['id']}/resend").status_code == 200
    unregistered = client.post(
        path, json={"recipient_email": "not.registered@example.com"}
    )
    assert unregistered.status_code == 201
    assert (
        unregistered.json()["simulation"]["recipient"] == "not.registered@example.com"
    )
