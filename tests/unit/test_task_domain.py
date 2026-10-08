from uuid import uuid4

import pytest

from task_manager.application.errors import InvalidRequest
from task_manager.domain.task import Task, TaskPriority, TaskStatus

pytestmark = pytest.mark.unit


def test_task_creation_applies_defaults_and_normalizes_text() -> None:
    parent_id = uuid4()
    task = Task.create(parent_id, "  Release  ", " \u3000 ")

    assert task.list_id == parent_id
    assert task.title == "Release"
    assert task.description is None
    assert task.status is TaskStatus.PENDING
    assert task.priority is TaskPriority.MEDIUM
    assert task.created_at == task.updated_at


@pytest.mark.parametrize("starting_status", list(TaskStatus))
@pytest.mark.parametrize("status", list(TaskStatus))
def test_task_status_can_change_to_every_value(
    starting_status: TaskStatus, status: TaskStatus
) -> None:
    task = Task.create(uuid4(), "Release", status=starting_status)
    original_updated_at = task.updated_at

    changed = task.change_status(status)

    assert changed is (status is not starting_status)
    assert task.status is status
    if changed:
        assert task.updated_at > original_updated_at
    else:
        assert task.updated_at == original_updated_at


def test_task_update_validates_before_mutating_and_supports_clearing() -> None:
    task = Task.create(uuid4(), "Old", "Keep")
    original_updated_at = task.updated_at

    with pytest.raises(InvalidRequest):
        task.update("New", "x" * 2001, True, TaskStatus.COMPLETED, TaskPriority.HIGH)

    assert task.title == "Old"
    assert task.description == "Keep"
    assert task.status is TaskStatus.PENDING
    assert task.priority is TaskPriority.MEDIUM
    assert task.updated_at == original_updated_at

    assert task.update(None, None, True, TaskStatus.COMPLETED, TaskPriority.HIGH)
    assert task.description is None
    assert task.status is TaskStatus.COMPLETED
    assert task.priority is TaskPriority.HIGH


def test_task_unchanged_update_preserves_timestamp() -> None:
    task = Task.create(uuid4(), "Same", "Description")
    original_updated_at = task.updated_at

    assert not task.update("Same", "Description", True, task.status, task.priority)
    assert task.updated_at == original_updated_at


@pytest.mark.parametrize("title", ["", "  \u3000 ", "x" * 201])
def test_task_rejects_invalid_title(title: str) -> None:
    with pytest.raises(InvalidRequest):
        Task.create(uuid4(), title)


@pytest.mark.parametrize("title", ["bad\x00title"])
def test_task_rejects_unpersistable_title(title: str) -> None:
    with pytest.raises(InvalidRequest) as error:
        Task.create(uuid4(), title)
    assert error.value.violations[0].field == "title"


def test_task_rejects_unpersistable_description_without_mutating() -> None:
    with pytest.raises(InvalidRequest):
        Task.create(uuid4(), "Valid", "bad\x00description")
    task = Task.create(uuid4(), "Valid", "Keep")
    original_updated_at = task.updated_at
    with pytest.raises(InvalidRequest):
        task.update(None, "bad\x00description", True, None, None)
    assert task.description == "Keep"
    assert task.updated_at == original_updated_at


def test_assignment_create_replace_clear_and_no_op_timestamp_rules() -> None:
    owner_id = uuid4()
    member_id = uuid4()
    task = Task.create(uuid4(), "Assigned", assignee_id=owner_id)
    assert task.assignee_id == owner_id
    original_updated_at = task.updated_at

    assert not task.update(None, None, False, None, None, owner_id, True)
    assert task.updated_at == original_updated_at
    assert task.update(None, None, False, None, None, member_id, True)
    assert task.assignee_id == member_id
    assert task.status is TaskStatus.PENDING
    assigned_updated_at = task.updated_at
    assert task.update(None, None, False, None, None, None, True)
    assert task.assignee_id is None
    assert task.updated_at > assigned_updated_at
    cleared_updated_at = task.updated_at
    assert not task.update(None, None, False, None, None, None, True)
    assert task.updated_at == cleared_updated_at
