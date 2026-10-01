"""Favorites (R06): which user marked which event, cascading with user and event.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE favorite (
            user_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            event_id uuid NOT NULL REFERENCES event (id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, event_id)
        )
        """
    )
    # Lookups by event (counter repair, R11 reminders) do not use the primary key.
    op.execute("CREATE INDEX favorite_event_id_idx ON favorite (event_id)")


def downgrade() -> None:
    op.execute("DROP TABLE favorite")
