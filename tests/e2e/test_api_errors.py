import httpx
import pytest
from sqlalchemy import Engine, text

from tests.fixtures.api import RunningApi

pytestmark = pytest.mark.e2e


def test_request_failures_have_safe_error_envelopes(api_client: httpx.Client) -> None:
    response = api_client.post("/api/v1/task-lists", json={"name": "  "})
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert response.json()["details"]
    missing_id = "11111111-1111-4111-8111-111111111111"
    assert api_client.get(f"/api/v1/task-lists/{missing_id}").status_code == 404
    assert api_client.get(f"/api/v1/task-lists/{missing_id}/tasks").status_code == 404
    assert (
        api_client.get(
            f"/api/v1/task-lists/{missing_id}/tasks?status=pending"
        ).status_code
        == 404
    )


def test_unexpected_database_failure_returns_generic_error(
    api_client: httpx.Client, postgres_engine: Engine
) -> None:
    with postgres_engine.begin() as connection:
        connection.execute(text("DROP TABLE task_lists CASCADE"))

    response = api_client.get("/api/v1/task-lists")
    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "An unexpected error occurred.",
        "details": [],
    }
    assert "task_lists" not in response.text


def test_list_persists_after_api_process_restart(api_server: RunningApi) -> None:
    response = api_server.client.post(
        "/api/v1/task-lists", json={"name": "Survives restart"}
    )
    assert response.status_code == 201
    task_list = response.json()

    api_server.restart()

    retrieved = api_server.client.get(f"/api/v1/task-lists/{task_list['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == task_list


def test_task_text_enums_and_immutable_fields(api_client: httpx.Client) -> None:
    list_id = api_client.post(
        "/api/v1/task-lists", json={"name": "Task validation"}
    ).json()["id"]
    collection = f"/api/v1/task-lists/{list_id}/tasks"
    missing_list = "11111111-1111-4111-8111-111111111111"
    assert (
        api_client.post(
            f"/api/v1/task-lists/{missing_list}/tasks", json={"title": "Orphan"}
        ).status_code
        == 404
    )
    invalid_tasks = (
        {"title": " \u3000 "},
        {"title": "x" * 201},
        {"title": "Valid", "description": "x" * 2001},
        {"title": "Valid", "status": "done"},
        {"title": "Valid", "priority": "urgent"},
        {"title": "Valid", "extra": True},
    )
    for request_body in invalid_tasks:
        assert api_client.post(collection, json=request_body).status_code == 422
    valid_task = api_client.post(
        collection, json={"title": "é" * 200, "description": "x" * 2000}
    )
    assert valid_task.status_code == 201
    task = api_client.post(
        collection, json={"title": "Clear", "description": "Keep"}
    ).json()
    task_path = f"{collection}/{task['id']}"
    assert (
        api_client.patch(task_path, json={"description": None}).json()["description"]
        is None
    )
    invalid_updates = (
        {"title": None},
        {"status": None},
        {"priority": None},
        {"list_id": list_id},
        {"created_at": "2024-01-01T00:00:00Z"},
        {},
    )
    for request_body in invalid_updates:
        assert api_client.patch(task_path, json=request_body).status_code == 422
    assert api_client.get(f"{collection}/not-a-uuid").status_code == 422
