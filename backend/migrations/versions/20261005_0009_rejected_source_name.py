"""Rejected AI sources per page and event name (R10b).

A calendar page is the source of many events; rejecting one find must not block the
others. Existing rows keep name "" and still block the whole page.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE rejected_source ADD COLUMN name_normalized text NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE rejected_source DROP CONSTRAINT rejected_source_pkey")
    op.execute("ALTER TABLE rejected_source ADD PRIMARY KEY (url_normalized, name_normalized)")


def downgrade() -> None:
    # Keep one row per page: the stricter rule from before (the whole page is rejected).
    op.execute(
        "DELETE FROM rejected_source a USING rejected_source b "
        "WHERE a.url_normalized = b.url_normalized AND a.name_normalized > b.name_normalized"
    )
    op.execute("ALTER TABLE rejected_source DROP CONSTRAINT rejected_source_pkey")
    op.execute("ALTER TABLE rejected_source DROP COLUMN name_normalized")
    op.execute("ALTER TABLE rejected_source ADD PRIMARY KEY (url_normalized)")
