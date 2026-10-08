"""Create task lists."""

from alembic import op
import sqlalchemy as sa

revision = "0001_task_lists"
down_revision = None
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
        "task_lists",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(name) BETWEEN 1 AND 100", name="ck_task_lists_name_length"
        ),
        sa.CheckConstraint(
            f"name = btrim(name, {_TRIM_SET})", name="ck_task_lists_name_trimmed"
        ),
        sa.CheckConstraint(
            "description IS NULL OR char_length(description) BETWEEN 1 AND 1000",
            name="ck_task_lists_description_length",
        ),
        sa.CheckConstraint(
            f"description IS NULL OR description = btrim(description, {_TRIM_SET})",
            name="ck_task_lists_description_trimmed",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at", name="ck_task_lists_timestamp_order"
        ),
    )
    op.create_index("ix_task_lists_created_id", "task_lists", ["created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_task_lists_created_id", table_name="task_lists")
    op.drop_table("task_lists")
