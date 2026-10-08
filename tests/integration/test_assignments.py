from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from sqlalchemy import Engine

from task_manager.application.access.operations import RemoveListMemberUseCase
from task_manager.application.commands import (
    CreateTask,
    CreateTaskList,
    UpdateTask,
)
from task_manager.application.errors import InvalidRequest
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.tasks.operations import CreateTaskUseCase
from task_manager.application.tasks.update import UpdateTaskUseCase
from task_manager.application.ports import UnitOfWorkFactory
from task_manager.domain.access import ListMembership
from task_manager.domain.task import TaskStatus
from task_manager.domain.user import User
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from tests.fixtures.identities import TEST_OWNER_ID

pytestmark = pytest.mark.integration


def _add_member(factory: UnitOfWorkFactory, email: str) -> User:
    member: User = User.register("Member", email, "test-hash")
    with factory(False) as unit_of_work:
        unit_of_work.users.create(member)
        unit_of_work.commit()
    return member


def test_remove_member_clears_assignments_and_keeps_completion_unchanged(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    member: User = _add_member(factory, "assigned.member@example.com")
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Assignments", TEST_OWNER_ID)
    )
    with factory(False) as unit_of_work:
        unit_of_work.memberships.create(
            ListMembership(task_list.id, member.id, datetime.now(UTC))
        )
        unit_of_work.commit()
    completed_task = CreateTaskUseCase(factory).execute(
        CreateTask(
            task_list.id,
            "Completed task",
            status=TaskStatus.COMPLETED,
            assignee_id=member.id,
        ),
        TEST_OWNER_ID,
    )
    other_task = CreateTaskUseCase(factory).execute(
        CreateTask(task_list.id, "Unassigned task", assignee_id=member.id),
        TEST_OWNER_ID,
    )
    original_list_updated_at: datetime = task_list.updated_at

    RemoveListMemberUseCase(factory).execute(task_list.id, TEST_OWNER_ID, member.id)

    with factory(True) as unit_of_work:
        saved_task = unit_of_work.tasks.get(task_list.id, completed_task.id)
        saved_other_task = unit_of_work.tasks.get(task_list.id, other_task.id)
        assert not unit_of_work.memberships.has_access(task_list.id, member.id)
        persisted_list = unit_of_work.task_lists.get(task_list.id)
        summary_page = unit_of_work.task_queries.query(task_list.id, None, None, 20, 0)
    assert saved_task is not None and saved_task.assignee_id is None
    assert saved_task.updated_at > completed_task.updated_at
    assert saved_task.status is TaskStatus.COMPLETED
    assert saved_other_task is not None
    assert saved_other_task.assignee_id is None
    assert saved_other_task.updated_at > other_task.updated_at
    assert persisted_list is not None
    assert persisted_list.updated_at == original_list_updated_at
    assert summary_page.summary.total_tasks == 2
    assert summary_page.summary.completed_tasks == 1
    assert summary_page.summary.completion_percentage == 50


def test_assignment_racing_member_removal_never_commits_ineligible_assignee(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    member: User = _add_member(factory, "race.member@example.com")
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Assignment race", TEST_OWNER_ID)
    )
    with factory(False) as unit_of_work:
        unit_of_work.memberships.create(
            ListMembership(task_list.id, member.id, datetime.now(UTC))
        )
        unit_of_work.commit()
    task = CreateTaskUseCase(factory).execute(
        CreateTask(task_list.id, "Race task"), TEST_OWNER_ID
    )
    start_together = Barrier(3)

    def assign_member() -> str:
        start_together.wait(timeout=5)
        try:
            UpdateTaskUseCase(factory).execute(
                task_list.id,
                task.id,
                TEST_OWNER_ID,
                UpdateTask(assignee_id=member.id),
            )
            return "assigned"
        except InvalidRequest:
            return "removed-first"

    def remove_member() -> None:
        start_together.wait(timeout=5)
        RemoveListMemberUseCase(factory).execute(task_list.id, TEST_OWNER_ID, member.id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        assignment_result = executor.submit(assign_member)
        removal_result = executor.submit(remove_member)
        start_together.wait(timeout=5)
        assignment_outcome: str = assignment_result.result(timeout=10)
        removal_result.result(timeout=10)

    with factory(True) as unit_of_work:
        persisted_task = unit_of_work.tasks.get(task_list.id, task.id)
        assert not unit_of_work.memberships.has_access(task_list.id, member.id)
    assert persisted_task is not None
    assert persisted_task.assignee_id is None
    assert assignment_outcome in {"assigned", "removed-first"}
