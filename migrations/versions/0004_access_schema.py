"""Add accounts, membership, invitations, and nullable assignment columns."""

from alembic import op
import sqlalchemy as sa

revision = "0004_access_schema"
down_revision = "0003_name_task_list_foreign_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "char_length(display_name) BETWEEN 1 AND 100",
            name="ck_users_display_name_length",
        ),
        sa.CheckConstraint(
            "display_name = btrim(display_name)",
            name="ck_users_display_name_trimmed",
        ),
        sa.CheckConstraint(
            "email = lower(email) AND char_length(email) BETWEEN 3 AND 254",
            name="ck_users_email_canonical",
        ),
        sa.CheckConstraint("updated_at >= created_at", name="ck_users_timestamp_order"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.add_column("task_lists", sa.Column("owner_id", sa.Uuid(as_uuid=True)))
    op.create_foreign_key(
        "fk_task_lists_owner_id_users",
        "task_lists",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_task_lists_owner_created_id",
        "task_lists",
        ["owner_id", "created_at", "id"],
    )
    op.add_column("tasks", sa.Column("assignee_id", sa.Uuid(as_uuid=True)))
    op.create_foreign_key(
        "fk_tasks_assignee_id_users",
        "tasks",
        "users",
        ["assignee_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "list_memberships",
        sa.Column(
            "list_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("task_lists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_list_memberships_user_list", "list_memberships", ["user_id", "list_id"]
    )
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "list_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("task_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invited_by_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("recipient_email", sa.String(length=254), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("simulation_subject", sa.Text(), nullable=False),
        sa.Column("simulation_status", sa.String(length=16), nullable=False),
        sa.Column("simulated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'revoked', 'expired')",
            name="ck_invitations_status",
        ),
        sa.CheckConstraint(
            "simulation_status = 'simulated'", name="ck_invitations_simulation_status"
        ),
        sa.CheckConstraint("expires_at > created_at", name="ck_invitations_expiry"),
        sa.CheckConstraint(
            "(status = 'accepted' AND accepted_at IS NOT NULL AND revoked_at IS NULL) "
            "OR (status = 'revoked' AND revoked_at IS NOT NULL "
            "AND accepted_at IS NULL) "
            "OR (status IN ('pending', 'expired') AND accepted_at IS NULL "
            "AND revoked_at IS NULL)",
            name="ck_invitations_terminal_timestamps",
        ),
        sa.UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
    )
    op.create_index(
        "uq_invitations_pending_recipient",
        "invitations",
        ["list_id", "recipient_email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_invitations_list_created_id", "invitations", ["list_id", "created_at", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_invitations_list_created_id", table_name="invitations")
    op.drop_index("uq_invitations_pending_recipient", table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("ix_list_memberships_user_list", table_name="list_memberships")
    op.drop_table("list_memberships")
    op.drop_constraint("fk_tasks_assignee_id_users", "tasks", type_="foreignkey")
    op.drop_column("tasks", "assignee_id")
    op.drop_index("ix_task_lists_owner_created_id", table_name="task_lists")
    op.drop_constraint("fk_task_lists_owner_id_users", "task_lists", type_="foreignkey")
    op.drop_column("task_lists", "owner_id")
    op.drop_table("users")
