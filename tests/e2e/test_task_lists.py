import httpx
import pytest

pytestmark = pytest.mark.e2e


def test_task_list_crud_and_pagination(api_client: httpx.Client) -> None:
    response = api_client.post(
        "/api/v1/task-lists",
        json={"name": "  Release  ", "description": "  Notes  "},
    )
    assert response.status_code == 201
    task_list = response.json()
    list_id = task_list["id"]
    list_path = f"/api/v1/task-lists/{list_id}"
    assert task_list["name"] == "Release"
    assert task_list["description"] == "Notes"
    assert response.headers["location"].endswith(list_id)
    assert api_client.get(list_path).json() == task_list
    assert api_client.get("/api/v1/task-lists/not-a-uuid").status_code == 422
    assert api_client.get(list_path, params={"extra": 1}).status_code == 422

    page = api_client.get("/api/v1/task-lists", params={"limit": 1}).json()
    assert page["total"] == 1
    assert len(page["items"]) == 1
    assert (
        api_client.get(
            "/api/v1/task-lists", params=[("limit", 1), ("limit", 2)]
        ).status_code
        == 422
    )
    beyond_page = api_client.get(
        "/api/v1/task-lists", params={"limit": 1, "offset": 100}
    ).json()
    assert beyond_page["items"] == []
    assert beyond_page["total"] == 1
    for parameters in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": 1.5}):
        assert (
            api_client.get("/api/v1/task-lists", params=parameters).status_code == 422
        )

    unchanged_time = task_list["updated_at"]
    cleared = api_client.patch(list_path, json={"description": None})
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    changed = api_client.patch(list_path, json={"name": "Release"}).json()
    assert changed["updated_at"] != unchanged_time
    unchanged_time = changed["updated_at"]
    assert (
        api_client.patch(list_path, json={"name": "Release"}).json()["updated_at"]
        == unchanged_time
    )
    assert api_client.patch(list_path, json={}).status_code == 422
    assert api_client.patch(list_path, json={"id": list_id}).status_code == 422
    assert api_client.patch(list_path, json={"name": None}).status_code == 422
    assert api_client.patch(list_path, json={"unknown": "field"}).status_code == 422
    assert (
        api_client.post("/api/v1/task-lists", json={"name": "Release"}).status_code
        == 201
    )


def test_task_list_text_validation_boundaries(api_client: httpx.Client) -> None:
    response = api_client.post(
        "/api/v1/task-lists",
        json={"name": "é" * 100, "description": "x" * 1000},
    )
    assert response.status_code == 201
    assert (
        api_client.post("/api/v1/task-lists", json={"name": "x" * 101}).status_code
        == 422
    )
    assert api_client.post("/api/v1/task-lists", json={"name": None}).status_code == 422
    assert api_client.post("/api/v1/task-lists", json={"name": True}).status_code == 422
    blank_description = api_client.post(
        "/api/v1/task-lists",
        json={"name": "Blank description", "description": " \t "},
    )
    assert blank_description.status_code == 201
    assert blank_description.json()["description"] is None
    assert (
        api_client.post(
            "/api/v1/task-lists",
            json={"name": "Valid", "description": "x" * 1001},
        ).status_code
        == 422
    )
