"""Interactively assign an explicitly selected account to historical lists."""

import getpass
import sys

from task_manager.application.accounts.bootstrap import BootstrapHistoricalOwnerUseCase
from task_manager.domain.errors import DomainValidationError
from task_manager.domain.user import User, canonicalize_email
from task_manager.infrastructure.persistence.database import (
    create_database_engine,
    create_unit_of_work_factory,
)
from task_manager.infrastructure.security.passwords import Argon2PasswordService
from sqlalchemy import Engine
from task_manager.application.ports import UnitOfWorkFactory


def main() -> int:
    if not sys.stdin.isatty():
        print("Owner bootstrap requires an interactive terminal.", file=sys.stderr)
        return 2
    engine: Engine = create_database_engine()
    unit_of_work_factory: UnitOfWorkFactory = create_unit_of_work_factory(engine)
    try:
        email_address: str = input("Historical owner email: ")
        canonical_email: str = canonicalize_email(email_address)
        with unit_of_work_factory(True) as unit_of_work:
            existing_user: User | None = unit_of_work.users.get_by_email(
                canonical_email
            )
        if existing_user is None:
            display_name: str | None = input("Owner display name: ")
            password: str = getpass.getpass("New owner password: ")
            password_confirmation: str = getpass.getpass("Confirm password: ")
            if password != password_confirmation:
                print("Passwords do not match; no changes were made.", file=sys.stderr)
                return 2
        else:
            display_name = None
            password = ""
        owner: User = BootstrapHistoricalOwnerUseCase(
            unit_of_work_factory, Argon2PasswordService()
        ).execute(canonical_email, display_name, password if password else None)
        print(f"Historical lists are assigned to account {owner.id}.")
        return 0
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except DomainValidationError as error:
        reasons: str = "; ".join(
            f"{violation.field}: {violation.message}" for violation in error.violations
        )
        print(reasons, file=sys.stderr)
        return 2
    except Exception:
        print("Owner bootstrap failed; no changes were committed.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
