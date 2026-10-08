from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import Engine

from task_manager.application.commands import AcceptInvitation, CreateInvitation
from task_manager.application.errors import ResourceConflict, ResourceNotFound
from task_manager.application.invitations import (
    AcceptInvitationUseCase,
    CreateInvitationUseCase,
    RevokeInvitationUseCase,
)
from task_manager.application.task_lists.operations import CreateTaskListUseCase
from task_manager.application.commands import CreateTaskList
from task_manager.infrastructure.persistence.database import create_unit_of_work_factory
from task_manager.infrastructure.security.invitation_tokens import (
    SecureInvitationTokenService,
)
from task_manager.domain.user import User
from task_manager.domain.invitation import Invitation
from tests.fixtures.identities import TEST_OWNER_ID
from task_manager.infrastructure.persistence.invitation_store import (
    SQLAlchemyInvitationStore,
)

pytestmark = pytest.mark.integration


def test_acceptance_is_atomic_idempotent_and_verifier_only(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    tokens = SecureInvitationTokenService()
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Launch", TEST_OWNER_ID)
    )
    recipient = User.register("Recipient", "recipient@example.com", "test-hash")
    with factory(False) as unit:
        unit.users.create(recipient)
        unit.commit()
    issued = CreateInvitationUseCase(factory, tokens).execute(
        CreateInvitation(task_list.id, TEST_OWNER_ID, recipient.email)
    )
    assert issued.invitation.expires_at > issued.invitation.created_at
    assert issued.acceptance_token not in repr(issued.invitation)
    with postgres_engine.connect() as connection:
        stored_hash: bytes = connection.exec_driver_sql(
            "SELECT token_hash FROM invitations WHERE id=%s", (issued.invitation.id,)
        ).scalar_one()
    assert stored_hash == tokens.digest(issued.acceptance_token)
    assert issued.acceptance_token.encode() != stored_hash

    acceptance = AcceptInvitationUseCase(factory, tokens)
    with pytest.raises(ResourceNotFound):
        acceptance.execute(AcceptInvitation(issued.acceptance_token, TEST_OWNER_ID))
    first = acceptance.execute(AcceptInvitation(issued.acceptance_token, recipient.id))
    retry = acceptance.execute(AcceptInvitation(issued.acceptance_token, recipient.id))
    assert retry == first
    with postgres_engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM list_memberships WHERE list_id=%s AND user_id=%s",
                (task_list.id, recipient.id),
            ).scalar_one()
            == 1
        )

    start_together = Barrier(3)
    second_recipient = User.register("Second", "second@example.com", "test-hash")
    with factory(False) as unit:
        unit.users.create(second_recipient)
        unit.commit()
    second = CreateInvitationUseCase(factory, tokens).execute(
        CreateInvitation(task_list.id, TEST_OWNER_ID, second_recipient.email)
    )

    def accept_once() -> bool:
        start_together.wait(timeout=5)
        try:
            acceptance.execute(
                AcceptInvitation(second.acceptance_token, second_recipient.id)
            )
            return True
        except ResourceConflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_call = executor.submit(accept_once)
        second_call = executor.submit(accept_once)
        start_together.wait(timeout=5)
        assert first_call.result(timeout=10)
        assert second_call.result(timeout=10)


def test_concurrent_duplicate_invitation_has_one_committed_record(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    tokens = SecureInvitationTokenService()
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Duplicate race", TEST_OWNER_ID)
    )
    use_case = CreateInvitationUseCase(factory, tokens)
    start_together = Barrier(3)

    def create() -> bool:
        start_together.wait(timeout=5)
        try:
            use_case.execute(
                CreateInvitation(task_list.id, TEST_OWNER_ID, "same@example.com")
            )
            return True
        except ResourceConflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(create)
        second = executor.submit(create)
        start_together.wait(timeout=5)
        assert sorted([first.result(timeout=10), second.result(timeout=10)]) == [
            False,
            True,
        ]
    with postgres_engine.connect() as connection:
        assert (
            connection.exec_driver_sql(
                "SELECT count(*) FROM invitations WHERE list_id=%s", (task_list.id,)
            ).scalar_one()
            == 1
        )


def test_acceptance_and_revocation_serialize_to_one_valid_outcome(
    postgres_engine: Engine,
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    tokens = SecureInvitationTokenService()
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Lifecycle race", TEST_OWNER_ID)
    )
    recipient = User.register("Race recipient", "lifecycle@example.com", "test-hash")
    with factory(False) as unit:
        unit.users.create(recipient)
        unit.commit()
    issued = CreateInvitationUseCase(factory, tokens).execute(
        CreateInvitation(task_list.id, TEST_OWNER_ID, recipient.email)
    )
    barrier = Barrier(3)

    def accept() -> bool:
        barrier.wait(timeout=5)
        try:
            AcceptInvitationUseCase(factory, tokens).execute(
                AcceptInvitation(issued.acceptance_token, recipient.id)
            )
            return True
        except ResourceConflict:
            return False

    def revoke() -> bool:
        barrier.wait(timeout=5)
        try:
            RevokeInvitationUseCase(factory).execute(
                task_list.id, issued.invitation.id, TEST_OWNER_ID
            )
            return True
        except ResourceConflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        accepted = executor.submit(accept)
        revoked = executor.submit(revoke)
        barrier.wait(timeout=5)
        outcomes = (accepted.result(timeout=10), revoked.result(timeout=10))
    assert sum(outcomes) == 1
    with factory(True) as unit:
        saved = unit.invitations.get(task_list.id, issued.invitation.id)
        is_member = unit.memberships.is_member(task_list.id, recipient.id)
    assert saved is not None
    assert (saved.status.value == "accepted") is is_member


def test_membership_is_rolled_back_when_acceptance_write_fails(
    postgres_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = create_unit_of_work_factory(postgres_engine)
    tokens = SecureInvitationTokenService()
    task_list = CreateTaskListUseCase(factory).execute(
        CreateTaskList("Atomic acceptance", TEST_OWNER_ID)
    )
    recipient = User.register("Recipient", "atomic@example.com", "test-hash")
    with factory(False) as unit:
        unit.users.create(recipient)
        unit.commit()
    issued = CreateInvitationUseCase(factory, tokens).execute(
        CreateInvitation(task_list.id, TEST_OWNER_ID, recipient.email)
    )

    def fail_update(self: SQLAlchemyInvitationStore, invitation: Invitation) -> None:
        raise RuntimeError("Injected invitation persistence failure.")

    monkeypatch.setattr(SQLAlchemyInvitationStore, "update", fail_update)
    with pytest.raises(RuntimeError, match="Injected invitation persistence failure"):
        AcceptInvitationUseCase(factory, tokens).execute(
            AcceptInvitation(issued.acceptance_token, recipient.id)
        )
    monkeypatch.undo()
    with factory(True) as unit:
        assert not unit.memberships.is_member(task_list.id, recipient.id)
        saved = unit.invitations.get(task_list.id, issued.invitation.id)
    assert saved is not None and saved.status.value == "pending"
