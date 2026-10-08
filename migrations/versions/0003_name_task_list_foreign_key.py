"""Name the task-to-list foreign key explicitly."""

from alembic import op

revision = "0003_name_task_list_foreign_key"
down_revision = "0002_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE tasks RENAME CONSTRAINT tasks_list_id_fkey "
        "TO fk_tasks_list_id_task_lists"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE tasks RENAME CONSTRAINT fk_tasks_list_id_task_lists "
        "TO tasks_list_id_fkey"
    )
