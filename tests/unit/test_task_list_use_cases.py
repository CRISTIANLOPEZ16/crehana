from contextlib import nullcontext
from typing import cast
from unittest.mock import Mock
from uuid import UUID

import pytest

from task_manager.application.commands import CreateTaskList, UNSET, UpdateTaskList
from task_manager.application.errors import ResourceNotFound
from task_manager.application.ports import TaskListStore, UnitOfWork, UnitOfWorkFactory
from task_manager.application.task_lists.operations import (
    CreateTaskListUseCase,
    UpdateTaskListUseCase,
)
from task_manager.application.task_lists.queries import GetTaskListUseCase
from task_manager.domain.task_list import TaskList
from tests.fixtures.identities import TEST_OWNER_ID

pytestmark = pytest.mark.unit


def test_create_use_case_commits_before_returning() -> None:
    store = Mock(spec=TaskListStore)
    unit_of_work = Mock(spec=UnitOfWork)
    unit_of_work.task_lists = store
    factory = cast(UnitOfWorkFactory, lambda _: nullcontext(unit_of_work))

    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Planning", TEST_OWNER_ID)
    )

    store.create.assert_called_once_with(task_list)
    unit_of_work.commit.assert_called_once_with()


def test_get_use_case_returns_missing_resource_failure() -> None:
    store = Mock(spec=TaskListStore)
    store.get.return_value = None
    unit_of_work = Mock(spec=UnitOfWork)
    unit_of_work.task_lists = store
    factory = cast(UnitOfWorkFactory, lambda _: nullcontext(unit_of_work))

    with pytest.raises(ResourceNotFound):
        GetTaskListUseCase(factory).execute(
            UUID("11111111-1111-4111-8111-111111111111"), TEST_OWNER_ID
        )


def test_update_use_case_preserves_omission_and_commits_changes() -> None:
    task_list = TaskList.create("Old", TEST_OWNER_ID, "Keep")
    store = Mock(spec=TaskListStore)
    store.get_for_update.return_value = task_list
    unit_of_work = Mock(spec=UnitOfWork)
    unit_of_work.task_lists = store
    factory = cast(UnitOfWorkFactory, lambda _: nullcontext(unit_of_work))

    updated = UpdateTaskListUseCase(factory).execute(
        task_list.id, TEST_OWNER_ID, UpdateTaskList(description=UNSET, name="New")
    )

    assert updated.name == "New"
    assert updated.description == "Keep"
    store.update.assert_called_once_with(task_list, frozenset({"name"}))
    unit_of_work.commit.assert_called_once_with()
