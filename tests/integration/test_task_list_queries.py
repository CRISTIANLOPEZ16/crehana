from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from task_manager.application.commands import CreateTaskList, ListTaskLists
from task_manager.application.ports import UnitOfWork
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.task_lists.queries import (
    GetTaskListUseCase,
    ListTaskListsUseCase,
)
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory

pytestmark = pytest.mark.integration


def test_task_list_persists_after_commit_and_across_sessions(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    created = CreateTaskListUseCase(factory).execute(
        CreateTaskList("  Integration list  ", "  ")
    )

    retrieved = GetTaskListUseCase(factory).execute(created.id)

    assert retrieved.id == created.id
    assert retrieved.name == "Integration list"
    assert retrieved.description is None
    assert retrieved.created_at == retrieved.updated_at
    with postgres_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM task_lists")) == 1


def test_postgresql_constraints_reject_blank_list_name(postgres_engine: Engine) -> None:
    with pytest.raises(IntegrityError):
        with postgres_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO task_lists "
                    "(id, name, description, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), '', NULL, now(), now())"
                )
            )


def test_list_page_uses_one_repeatable_read_snapshot(postgres_engine: Engine) -> None:
    regular_factory = create_unit_of_work_factory(postgres_engine)
    original = CreateTaskListUseCase(regular_factory).execute(
        CreateTaskList("Original")
    )
    inserted_during_read = False

    def interleaving_factory(
        read_only_snapshot: bool,
    ) -> AbstractContextManager[UnitOfWork]:
        @contextmanager
        def create_unit_of_work() -> Iterator[UnitOfWork]:
            nonlocal inserted_during_read
            with regular_factory(read_only_snapshot) as unit_of_work:
                if read_only_snapshot and not inserted_during_read:
                    assert unit_of_work.task_lists.get(original.id) is not None
                    inserted_during_read = True
                    CreateTaskListUseCase(regular_factory).execute(
                        CreateTaskList("Committed during read")
                    )
                yield unit_of_work

        return create_unit_of_work()

    first_page = ListTaskListsUseCase(interleaving_factory).execute(ListTaskLists())
    assert first_page.total == 1
    assert [task_list.name for task_list in first_page.items] == ["Original"]

    next_page = ListTaskListsUseCase(regular_factory).execute(ListTaskLists())
    assert next_page.total == 2
    tied_timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    with postgres_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE task_lists SET created_at=:created_at, updated_at=:updated_at"
            ),
            {"created_at": tied_timestamp, "updated_at": tied_timestamp},
        )
    ordered_page = ListTaskListsUseCase(regular_factory).execute(ListTaskLists(limit=2))
    assert [item.id for item in ordered_page.items] == sorted(
        item.id for item in ordered_page.items
    )
