"""Transactional outbox for domain events (R07, ADR 0005).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE outbox (
            id uuid PRIMARY KEY,
            type text NOT NULL,
            payload jsonb NOT NULL,
            occurred_at timestamptz NOT NULL DEFAULT now(),
            dispatched_at timestamptz
        )
        """
    )
    # The relay reads undispatched entries in order; the purge job deletes old dispatched ones.
    op.execute(
        "CREATE INDEX outbox_pending_idx ON outbox (occurred_at) WHERE dispatched_at IS NULL"
    )
    op.execute(
        "CREATE INDEX outbox_dispatched_idx ON outbox (dispatched_at) "
        "WHERE dispatched_at IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE outbox")
