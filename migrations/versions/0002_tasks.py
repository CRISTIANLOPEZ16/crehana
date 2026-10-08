"""Create tasks and cascade them with their parent list."""

from alembic import op
import sqlalchemy as sa

revision = "0002_tasks"
down_revision = "0001_task_lists"
branch_labels = None
depends_on = None

_TRIM_SET = " || ".join(
    f"chr({codepoint})"
    for codepoint in (
        9,
        10,
        11,
        12,
        13,
        28,
        29,
        30,
        31,
        32,
        133,
        160,
        5760,
        8192,
        8193,
        8194,
        8195,
        8196,
        8197,
        8198,
        8199,
        8200,
        8201,
        8202,
        8232,
        8233,
        8239,
        8287,
        12288,
    )
)


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "list_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("task_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(title) BETWEEN 1 AND 200", name="ck_tasks_title_length"
        ),
        sa.CheckConstraint(
            f"title = btrim(title, {_TRIM_SET})", name="ck_tasks_title_trimmed"
        ),
        sa.CheckConstraint(
            "description IS NULL OR char_length(description) BETWEEN 1 AND 2000",
            name="ck_tasks_description_length",
        ),
        sa.CheckConstraint(
            "description IS NULL OR description = " f"btrim(description, {_TRIM_SET})",
            name="ck_tasks_description_trimmed",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="ck_tasks_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high')", name="ck_tasks_priority"
        ),
        sa.CheckConstraint("updated_at >= created_at", name="ck_tasks_timestamp_order"),
    )
    op.create_index(
        "ix_tasks_list_created_id", "tasks", ["list_id", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_list_created_id", table_name="tasks")
    op.drop_table("tasks")
