import httpx
import pytest

pytestmark = pytest.mark.e2e


def test_task_lifecycle_status_transitions_and_parent_scope(
    api_client: httpx.Client,
) -> None:
    list_response = api_client.post("/api/v1/task-lists", json={"name": "Release"})
    list_id = list_response.json()["id"]
    collection_path = f"/api/v1/task-lists/{list_id}/tasks"
    created = api_client.post(
        collection_path, json={"title": "  Ship  ", "description": "  Details  "}
    )
    assert created.status_code == 201
    task = created.json()
    task_path = f"{collection_path}/{task['id']}"
    assert task["title"] == "Ship"
    assert task["status"] == "pending"
    assert task["priority"] == "medium"
    assert task["description"] == "Details"
    assert created.headers["location"].endswith(task["id"])
    duplicate = api_client.post(collection_path, json={"title": "Ship"}).json()
    assert api_client.get(task_path).json()["title"] == "Ship"
    cleared_description = api_client.patch(task_path, json={"description": None})
    assert cleared_description.status_code == 200
    assert cleared_description.json()["description"] is None

    parent_updated_at = api_client.get(f"/api/v1/task-lists/{list_id}").json()[
        "updated_at"
    ]
    for status in ("in_progress", "completed", "pending", "completed"):
        response = api_client.patch(task_path, json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status
    assert (
        api_client.get(f"/api/v1/task-lists/{list_id}").json()["updated_at"]
        == parent_updated_at
    )
    assert api_client.get(collection_path).json()["summary"] == {
        "total_tasks": 2,
        "completed_tasks": 1,
        "completion_percentage": 50.0,
    }

    other_list_id = api_client.post(
        "/api/v1/task-lists", json={"name": "Other"}
    ).json()["id"]
    other_task_path = f"/api/v1/task-lists/{other_list_id}/tasks/{task['id']}"
    assert api_client.get(other_task_path).status_code == 404
    assert (
        api_client.patch(other_task_path, json={"title": "Wrong parent"}).status_code
        == 404
    )
    assert api_client.delete(other_task_path).status_code == 404
    assert api_client.delete(task_path).status_code == 204
    assert api_client.get(f"/api/v1/task-lists/{list_id}").status_code == 200
    assert api_client.delete(task_path).status_code == 404
    assert api_client.get(collection_path).json()["summary"] == {
        "total_tasks": 1,
        "completed_tasks": 0,
        "completion_percentage": 0.0,
    }
    assert api_client.delete(f"/api/v1/task-lists/{list_id}").status_code == 204
    assert api_client.get(task_path).status_code == 404
    assert api_client.get(f"{collection_path}/{duplicate['id']}").status_code == 404
    assert api_client.delete(f"/api/v1/task-lists/{other_list_id}").status_code == 204
