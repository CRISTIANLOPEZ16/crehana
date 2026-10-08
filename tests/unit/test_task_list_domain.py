from datetime import UTC

import pytest

from task_manager.application.errors import InvalidRequest
from task_manager.domain.task_list import TaskList

pytestmark = pytest.mark.unit


def test_create_list_normalizes_and_sets_equal_utc_timestamps() -> None:
    task_list = TaskList.create("  Sprint  ", "  Plan  ")

    assert task_list.name == "Sprint"
    assert task_list.description == "Plan"
    assert task_list.created_at == task_list.updated_at
    assert task_list.created_at.tzinfo == UTC


@pytest.mark.parametrize("name", ["", " \u3000 ", "x" * 101])
def test_create_list_rejects_blank_or_oversized_names(name: str) -> None:
    with pytest.raises(InvalidRequest):
        TaskList.create(name, None)


def test_list_description_boundaries_and_duplicate_names_are_allowed() -> None:
    first = TaskList.create("Same", "x" * 1000)
    second = TaskList.create("Same", " \t ")

    assert first.description == "x" * 1000
    assert second.description is None
    assert first.id != second.id
    with pytest.raises(InvalidRequest):
        TaskList.create("Valid", "x" * 1001)


def test_update_preserves_omitted_fields_and_detects_no_op() -> None:
    task_list = TaskList.create("Old", "Description")
    original_updated_at = task_list.updated_at

    assert task_list.update("New", None, False)
    assert task_list.name == "New"
    assert task_list.description == "Description"
    assert task_list.updated_at > original_updated_at
    changed_updated_at = task_list.updated_at
    assert not task_list.update("New", None, False)
    assert task_list.updated_at == changed_updated_at
    assert task_list.update(None, None, True)
    assert task_list.description is None


def test_update_validates_every_field_before_mutation() -> None:
    task_list = TaskList.create("Old", "Description")
    original_updated_at = task_list.updated_at

    with pytest.raises(InvalidRequest):
        task_list.update("New", "x" * 1001, True)

    assert task_list.name == "Old"
    assert task_list.description == "Description"
    assert task_list.updated_at == original_updated_at
