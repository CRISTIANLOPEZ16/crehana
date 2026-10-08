from uuid import UUID

from task_manager.application.errors import ResourceConflict
from task_manager.application.ports import PasswordService, UnitOfWorkFactory
from task_manager.domain.user import User, canonicalize_email, validate_password


class BootstrapHistoricalOwnerUseCase:
    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, password_service: PasswordService
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._password_service = password_service

    def execute(
        self, email_address: str, display_name: str | None, password: str | None
    ) -> User:
        canonical_email: str = canonicalize_email(email_address)
        with self._unit_of_work_factory(False) as unit_of_work:
            user: User | None = unit_of_work.users.get_by_email(canonical_email)
            if user is None:
                if display_name is None or password is None:
                    raise ValueError("New owner requires a name and password.")
                validate_password(password)
                password_hash: str = self._password_service.hash(password)
                user = User.register(display_name, canonical_email, password_hash)
                unit_of_work.users.create(user)
            existing_owner_ids: set[UUID] = unit_of_work.task_lists.owner_ids()
            if any(owner_id != user.id for owner_id in existing_owner_ids):
                raise ResourceConflict(
                    "Task lists already have a different owner; existing ownership "
                    "was not changed."
                )
            unit_of_work.task_lists.assign_missing_owner(user.id)
            unit_of_work.commit()
            return user
