"""Drop moderation regions (ADR 0015): table `region` and `event.region_id`.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-05
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX event_region_idx")
    op.execute("ALTER TABLE event DROP COLUMN region_id")
    op.execute("DROP TABLE region")


def downgrade() -> None:
    # Structure only: the regions and the assignment of events are not restored, so the
    # column stays nullable (load regions with the seed of revision 0007 if needed).
    op.execute(
        """
        CREATE TABLE region (
            id uuid PRIMARY KEY,
            key text NOT NULL UNIQUE,
            name text NOT NULL,
            postal_codes text[] NOT NULL DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX region_postal_codes_idx ON region USING gin (postal_codes)")
    op.execute("ALTER TABLE event ADD COLUMN region_id uuid REFERENCES region (id)")
    op.execute("CREATE INDEX event_region_idx ON event (region_id) WHERE deleted_at IS NULL")
