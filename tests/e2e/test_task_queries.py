import httpx
import pytest

pytestmark = pytest.mark.e2e


def test_filters_and_pagination_leave_completion_summary_unfiltered(
    api_client: httpx.Client,
) -> None:
    list_id = api_client.post("/api/v1/task-lists", json={"name": "Query list"}).json()[
        "id"
    ]
    collection = f"/api/v1/task-lists/{list_id}/tasks"
    for title, status, priority in (
        ("Done one", "completed", "high"),
        ("Done two", "completed", "high"),
        ("Pending", "pending", "high"),
        ("Active", "in_progress", "low"),
    ):
        response = api_client.post(
            collection,
            json={"title": title, "status": status, "priority": priority},
        )
        assert response.status_code == 201

    combined = api_client.get(
        collection, params={"status": "pending", "priority": "high", "limit": 1}
    ).json()
    assert combined["matched_tasks"] == 1
    assert [task["title"] for task in combined["items"]] == ["Pending"]
    assert combined["summary"] == {
        "total_tasks": 4,
        "completed_tasks": 2,
        "completion_percentage": 50.0,
    }
    assert (
        api_client.get(collection, params={"status": "completed"}).json()[
            "matched_tasks"
        ]
        == 2
    )
    assert (
        api_client.get(collection, params={"priority": "low"}).json()["matched_tasks"]
        == 1
    )

    no_matches = api_client.get(
        collection, params={"status": "pending", "priority": "low"}
    ).json()
    assert no_matches["items"] == []
    assert no_matches["matched_tasks"] == 0
    assert no_matches["summary"] == combined["summary"]
    beyond_page = api_client.get(collection, params={"offset": 100}).json()
    assert beyond_page["items"] == []
    assert beyond_page["matched_tasks"] == 4
    assert beyond_page["summary"] == combined["summary"]
    assert api_client.get(collection, params={"status": "PENDING"}).status_code == 422
    assert api_client.get(collection, params={"unknown": "value"}).status_code == 422
    for parameters in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        assert api_client.get(collection, params=parameters).status_code == 422
    assert (
        api_client.get(
            collection, params=[("status", "pending"), ("status", "completed")]
        ).status_code
        == 422
    )


def test_empty_and_fractional_completion_summaries(api_client: httpx.Client) -> None:
    empty_id = api_client.post("/api/v1/task-lists", json={"name": "Empty"}).json()[
        "id"
    ]
    empty_page = api_client.get(f"/api/v1/task-lists/{empty_id}/tasks").json()
    assert empty_page["summary"]["completion_percentage"] == 0.0

    list_id = api_client.post("/api/v1/task-lists", json={"name": "Fractional"}).json()[
        "id"
    ]
    collection = f"/api/v1/task-lists/{list_id}/tasks"
    responses = [
        api_client.post(
            collection,
            json={
                "title": f"Task {task_number}",
                "status": "completed" if task_number == 0 else "pending",
                "priority": "low" if task_number == 0 else "medium",
            },
        )
        for task_number in range(32)
    ]
    assert all(response.status_code == 201 for response in responses)
    page = api_client.get(
        collection, params={"status": "pending", "limit": 1, "offset": 1}
    ).json()
    assert len(page["items"]) == 1
    assert page["summary"]["total_tasks"] == 32
    assert page["summary"]["completed_tasks"] == 1
    assert page["summary"]["completion_percentage"] == 3.13
