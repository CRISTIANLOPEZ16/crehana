from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import cast

import pytest
from sqlalchemy import Engine, event, inspect, text
from sqlalchemy.orm import Session

from task_manager.application.commands import CreateTask, CreateTaskList
from task_manager.application.errors import ResourceNotFound
from task_manager.application.task_lists.operations import (
    CreateTaskListUseCase,
    DeleteTaskListUseCase,
)
from task_manager.application.task_lists.queries import GetTaskListUseCase
from task_manager.application.tasks.operations import (
    CreateTaskUseCase,
)
from task_manager.application.tasks.queries import GetTaskUseCase
from task_manager.application.invitations import CreateInvitationUseCase
from task_manager.application.commands import CreateInvitation
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from task_manager.infrastructure.security.invitation_tokens import (
    SecureInvitationTokenService,
)
from tests.fixtures.identities import TEST_OWNER_ID
from tests.integration.concurrency_support import wait_for_database_lock

pytestmark = pytest.mark.integration


def test_task_table_has_named_cascading_list_foreign_key(
    postgres_engine: Engine,
) -> None:
    foreign_keys = inspect(postgres_engine).get_foreign_keys("tasks")

    list_foreign_key: dict[str, object] = cast(
        dict[str, object],
        next(
            foreign_key
            for foreign_key in foreign_keys
            if foreign_key["constrained_columns"] == ["list_id"]
        ),
    )
    assert list_foreign_key["name"] == "fk_tasks_list_id_task_lists"
    assert list_foreign_key["referred_table"] == "task_lists"
    assert list_foreign_key["options"] == {"ondelete": "CASCADE"}


def test_parent_delete_serializes_with_task_creation(postgres_engine: Engine) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Parent", TEST_OWNER_ID)
    )
    connection = postgres_engine.connect()
    transaction = connection.begin()
    connection.execute(
        text("SELECT id FROM task_lists WHERE id=:list_id FOR UPDATE"),
        {"list_id": task_list.id},
    )
    worker_started = Event()

    def create_child() -> None:
        worker_started.set()
        CreateTaskUseCase(factory).execute(
            CreateTask(task_list.id, "Child"), TEST_OWNER_ID
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            creation_future = executor.submit(create_child)
            assert worker_started.wait(timeout=5)
            assert wait_for_database_lock(postgres_engine, "task_lists")
            connection.execute(
                text("DELETE FROM task_lists WHERE id=:list_id"),
                {"list_id": task_list.id},
            )
            transaction.commit()
            with pytest.raises(ResourceNotFound):
                creation_future.result(timeout=5)
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()

    with postgres_engine.connect() as database_connection:
        assert database_connection.scalar(text("SELECT count(*) FROM tasks")) == 0


def test_cascade_delete_rolls_back_when_commit_fails(postgres_engine: Engine) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Parent", TEST_OWNER_ID)
    )
    task = CreateTaskUseCase(factory).execute(
        CreateTask(task_list.id, "Child"), TEST_OWNER_ID
    )
    CreateInvitationUseCase(factory, SecureInvitationTokenService()).execute(
        CreateInvitation(task_list.id, TEST_OWNER_ID, "cascade@example.com")
    )

    def reject_commit(session: Session) -> None:
        raise RuntimeError("Injected pre-commit failure.")

    event.listen(Session, "before_commit", reject_commit)
    try:
        with pytest.raises(RuntimeError, match="Injected pre-commit failure"):
            DeleteTaskListUseCase(factory).execute(task_list.id, TEST_OWNER_ID)
    finally:
        event.remove(Session, "before_commit", reject_commit)

    assert (
        GetTaskListUseCase(factory).execute(task_list.id, TEST_OWNER_ID).id
        == task_list.id
    )
    assert (
        GetTaskUseCase(factory).execute(task_list.id, task.id, TEST_OWNER_ID).id
        == task.id
    )
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM tasks")) == 1
        assert connection.scalar(text("SELECT count(*) FROM invitations")) == 1

    DeleteTaskListUseCase(factory).execute(task_list.id, TEST_OWNER_ID)
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM invitations")) == 0
