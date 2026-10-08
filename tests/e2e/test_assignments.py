from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from sqlalchemy import Engine

from task_manager.domain.access import ListMembership
from task_manager.domain.user import User
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.fixtures.api import RunningApi, TEST_SIGNING_KEY

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


def test_participant_discovery_assignment_and_atomic_removal(
    api_server: RunningApi, postgres_engine: Engine
) -> None:
    owner_client: httpx.Client = api_server.client
    task_list = owner_client.post(
        "/api/v1/task-lists", json={"name": "Responsible users"}
    ).json()
    list_id: str = task_list["id"]
    member: User = User.register("Member", "assignment.member@example.com", "unused")
    outsider: User = User.register(
        "Outsider", "assignment.outsider@example.com", "unused"
    )
    factory = create_unit_of_work_factory(postgres_engine)
    with factory(False) as unit_of_work:
        unit_of_work.users.create(member)
        unit_of_work.users.create(outsider)
        unit_of_work.commit()
    with factory(False) as unit_of_work:
        unit_of_work.memberships.create(
            ListMembership(task_list["id"], member.id, datetime.now(UTC))
        )
        unit_of_work.commit()

    participants = owner_client.get(
        f"/api/v1/task-lists/{list_id}/participants?limit=1"
    )
    assert participants.status_code == 200
    assert participants.json()["total"] == 2
    all_participants = owner_client.get(
        f"/api/v1/task-lists/{list_id}/participants?limit=100"
    ).json()
    repeated_page = owner_client.get(
        f"/api/v1/task-lists/{list_id}/participants?limit=100"
    ).json()
    assert all_participants["items"] == repeated_page["items"]
    assert {item["classification"] for item in all_participants["items"]} == {
        "owner",
        "member",
    }

    task_collection: str = f"/api/v1/task-lists/{list_id}/tasks"
    created = owner_client.post(
        task_collection,
        json={
            "title": "Assigned completed task",
            "status": "completed",
            "assignee_id": str(member.id),
        },
    )
    assert created.status_code == 201
    task_id: str = created.json()["id"]
    assert created.json()["assignee_id"] == str(member.id)
    missing_assignee = owner_client.post(
        task_collection,
        json={"title": "Invalid participant", "assignee_id": str(outsider.id)},
    )
    assert missing_assignee.status_code == 422
    assert missing_assignee.json()["details"][0]["field"] == "body.assignee_id"
    assert (
        owner_client.post(
            task_collection, json={"title": "Malformed ID", "assignee_id": "bad"}
        ).status_code
        == 422
    )
    nonexistent_user = owner_client.post(
        task_collection,
        json={
            "title": "Missing participant",
            "assignee_id": "00000000-0000-4000-8000-000000000099",
        },
    )
    assert nonexistent_user.status_code == 422
    member_headers = {"Authorization": f"Bearer {_token(api_server, str(member.id))}"}
    member_assignment = owner_client.patch(
        f"{task_collection}/{task_id}",
        headers=member_headers,
        json={"assignee_id": str(member.id)},
    )
    assert member_assignment.status_code == 200
    assert member_assignment.json()["assignee_id"] == str(member.id)

    task_path: str = f"{task_collection}/{task_id}"
    unchanged = owner_client.patch(task_path, json={"assignee_id": str(member.id)})
    assert unchanged.status_code == 200
    assert unchanged.json()["updated_at"] == created.json()["updated_at"]
    cleared = owner_client.patch(task_path, json={"assignee_id": None})
    assert cleared.status_code == 200
    assert cleared.json()["assignee_id"] is None
    assert cleared.json()["status"] == "completed"
    reassigned = owner_client.patch(task_path, json={"assignee_id": str(member.id)})
    assert reassigned.status_code == 200
    before_remove_summary = owner_client.get(task_collection).json()["summary"]

    removed = owner_client.delete(
        f"/api/v1/task-lists/{list_id}/participants/{member.id}"
    )
    assert removed.status_code == 204
    after_remove = owner_client.get(task_path).json()
    assert after_remove["assignee_id"] is None
    assert after_remove["updated_at"] > reassigned.json()["updated_at"]
    assert owner_client.get(task_collection).json()["summary"] == before_remove_summary
    assert (
        owner_client.delete(
            f"/api/v1/task-lists/{list_id}/participants/{member.id}"
        ).status_code
        == 404
    )
    assert (
        owner_client.delete(
            f"/api/v1/task-lists/{list_id}/participants/{task_list['owner_id']}"
        ).status_code
        == 409
    )
