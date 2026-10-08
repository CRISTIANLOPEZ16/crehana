"""Require every task list to have an explicitly selected owner."""

from alembic import op
import sqlalchemy as sa

revision = "0005_require_list_owners"
down_revision = "0004_access_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection: sa.Connection = op.get_bind()
    ownerless_count: int | None = connection.scalar(
        sa.text("SELECT count(*) FROM task_lists WHERE owner_id IS NULL")
    )
    if ownerless_count:
        raise RuntimeError(
            "Cannot require list owners: existing task lists are ownerless. "
            "Run the offline owner bootstrap command, then retry Alembic upgrade head."
        )
    op.alter_column("task_lists", "owner_id", nullable=False)


def downgrade() -> None:
    op.alter_column("task_lists", "owner_id", nullable=True)
