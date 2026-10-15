"""Shared lists (R13): lists, members, events; notifications may reference a list.

All members have the same rights. `created_by` / `added_by` are kept for traceability and
set to null when that account is deleted; memberships go with the account, and a list
without members is deleted by `DeleteAccount`.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE shared_list (
            id uuid PRIMARY KEY,
            name text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 60),
            created_by uuid REFERENCES app_user (id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE list_member (
            list_id uuid NOT NULL REFERENCES shared_list (id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            added_by uuid REFERENCES app_user (id) ON DELETE SET NULL,
            added_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (list_id, user_id)
        )
        """
    )
    op.execute("CREATE INDEX list_member_user_idx ON list_member (user_id)")
    op.execute(
        """
        CREATE TABLE list_event (
            list_id uuid NOT NULL REFERENCES shared_list (id) ON DELETE CASCADE,
            event_id uuid NOT NULL REFERENCES event (id) ON DELETE CASCADE,
            added_by uuid REFERENCES app_user (id) ON DELETE SET NULL,
            added_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (list_id, event_id)
        )
        """
    )
    op.execute("CREATE INDEX list_event_event_idx ON list_event (event_id)")
    op.execute(
        "ALTER TABLE notification ADD COLUMN list_id uuid "
        "REFERENCES shared_list (id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE notification DROP COLUMN list_id")
    op.execute("DROP TABLE list_event")
    op.execute("DROP TABLE list_member")
    op.execute("DROP TABLE shared_list")
