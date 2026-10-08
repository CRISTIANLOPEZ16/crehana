from datetime import UTC
from uuid import UUID, uuid4

import pytest

from task_manager.application.errors import InvalidRequest
from task_manager.domain.task_list import TaskList

pytestmark = pytest.mark.unit
OWNER_ID: UUID = uuid4()


def test_create_list_normalizes_and_sets_equal_utc_timestamps() -> None:
    task_list = TaskList.create("  Sprint  ", OWNER_ID, "  Plan  ")

    assert task_list.name == "Sprint"
    assert task_list.description == "Plan"
    assert task_list.created_at == task_list.updated_at
    assert task_list.created_at.tzinfo == UTC


@pytest.mark.parametrize("name", ["", " \u3000 ", "x" * 101])
def test_create_list_rejects_blank_or_oversized_names(name: str) -> None:
    with pytest.raises(InvalidRequest):
        TaskList.create(name, OWNER_ID)


def test_list_description_boundaries_and_duplicate_names_are_allowed() -> None:
    first = TaskList.create("Same", OWNER_ID, "x" * 1000)
    second = TaskList.create("Same", OWNER_ID, " \t ")

    assert first.description == "x" * 1000
    assert second.description is None
    assert first.id != second.id
    with pytest.raises(InvalidRequest):
        TaskList.create("Valid", OWNER_ID, "x" * 1001)


def test_update_preserves_omitted_fields_and_detects_no_op() -> None:
    task_list = TaskList.create("Old", OWNER_ID, "Description")
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
    task_list = TaskList.create("Old", OWNER_ID, "Description")
    original_updated_at = task_list.updated_at

    with pytest.raises(InvalidRequest):
        task_list.update("New", "x" * 1001, True)

    assert task_list.name == "Old"
    assert task_list.description == "Description"
    assert task_list.updated_at == original_updated_at


def test_list_rejects_unpersistable_text_without_mutating() -> None:
    with pytest.raises(InvalidRequest) as name_error:
        TaskList.create("bad\x00name", OWNER_ID)
    assert name_error.value.violations[0].field == "name"
    with pytest.raises(InvalidRequest):
        TaskList.create("Valid", OWNER_ID, "bad\x00description")

    task_list = TaskList.create("Valid", OWNER_ID, "Keep")
    original_updated_at = task_list.updated_at
    with pytest.raises(InvalidRequest):
        task_list.update(None, "bad\x00description", True)
    assert task_list.description == "Keep"
    assert task_list.updated_at == original_updated_at
