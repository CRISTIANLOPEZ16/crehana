from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from sqlalchemy import Engine

from task_manager.domain.access import ListMembership
from task_manager.domain.user import User
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.fixtures.api import RunningApi, TEST_SIGNING_KEY
from tests.fixtures.identities import TEST_OWNER_ID

pytestmark = pytest.mark.e2e


def _token(server: RunningApi, user_id: str) -> str:
    issued_at: datetime = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": user_id,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=30),
        "iss": server.settings["JWT_ISSUER"],
        "aud": server.settings["JWT_AUDIENCE"],
    }
    return jwt.encode(claims, TEST_SIGNING_KEY, algorithm="HS256")


def test_owner_member_and_unrelated_resource_permissions(
    api_server: RunningApi, postgres_engine: Engine
) -> None:
    owner_client: httpx.Client = api_server.client
    member: User = User.register("List member", "member@example.com", "test-hash")
    outsider: User = User.register("Unrelated", "other@example.com", "test-hash")
    factory = create_unit_of_work_factory(postgres_engine)
    with factory(False) as unit_of_work:
        unit_of_work.users.create(member)
        unit_of_work.users.create(outsider)
        unit_of_work.commit()

    created_list = owner_client.post("/api/v1/task-lists", json={"name": "Shared list"})
    assert created_list.status_code == 201
    list_id: str = created_list.json()["id"]
    assert created_list.json()["owner_id"] == str(TEST_OWNER_ID)
    task = owner_client.post(
        f"/api/v1/task-lists/{list_id}/tasks", json={"title": "Member can edit"}
    )
    assert task.status_code == 201
    task_id: str = task.json()["id"]
    with factory(False) as unit_of_work:
        unit_of_work.memberships.create(
            ListMembership(created_list.json()["id"], member.id, datetime.now(UTC))
        )
        unit_of_work.commit()

    member_headers: dict[str, str] = {
        "Authorization": f"Bearer {_token(api_server, str(member.id))}"
    }
    member_get = owner_client.get(
        f"/api/v1/task-lists/{list_id}", headers=member_headers
    )
    assert member_get.status_code == 200
    assert (
        owner_client.patch(
            f"/api/v1/task-lists/{list_id}",
            headers=member_headers,
            json={"name": "Member cannot rename"},
        ).status_code
        == 403
    )
    member_task_update = owner_client.patch(
        f"/api/v1/task-lists/{list_id}/tasks/{task_id}",
        headers=member_headers,
        json={"status": "completed"},
    )
    assert member_task_update.status_code == 200
    assert (
        owner_client.delete(
            f"/api/v1/task-lists/{list_id}", headers=member_headers
        ).status_code
        == 403
    )

    outsider_headers: dict[str, str] = {
        "Authorization": f"Bearer {_token(api_server, str(outsider.id))}"
    }
    assert (
        owner_client.get(
            f"/api/v1/task-lists/{list_id}", headers=outsider_headers
        ).status_code
        == 404
    )
    assert (
        owner_client.get(
            f"/api/v1/task-lists/{list_id}/tasks/{task_id}", headers=outsider_headers
        ).status_code
        == 404
    )
    outsider_page = owner_client.get(
        "/api/v1/task-lists", headers=outsider_headers
    ).json()
    assert outsider_page["items"] == []
    assert outsider_page["total"] == 0
    assert (
        owner_client.get(
            f"/api/v1/task-lists/{list_id}/tasks", headers=outsider_headers
        ).status_code
        == 404
    )

    other_list = owner_client.post(
        "/api/v1/task-lists", json={"name": "Different parent"}
    ).json()
    assert (
        owner_client.get(
            f"/api/v1/task-lists/{other_list['id']}/tasks/{task_id}"
        ).status_code
        == 404
    )


def test_authentication_precedes_malformed_business_input(
    api_client: httpx.Client,
) -> None:
    unauthenticated = {"Authorization": ""}
    response = api_client.post(
        "/api/v1/task-lists", headers=unauthenticated, json={"name": ""}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["code"] == "authentication_failed"
