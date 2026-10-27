"""Optional filters of the AI search and the counter of non-matching finds (R10c).

The filters are public, moderator-independent values (period, category IDs, radius, fixed
focuses); no free text. Existing jobs keep "no filter".

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE ai_search_job "
        "ADD COLUMN filter_date_from date, "
        "ADD COLUMN filter_date_to date, "
        "ADD COLUMN filter_category_ids uuid[] NOT NULL DEFAULT '{}', "
        "ADD COLUMN filter_radius_km integer, "
        "ADD COLUMN filter_focus text[] NOT NULL DEFAULT '{}', "
        "ADD COLUMN skipped_not_matching integer NOT NULL DEFAULT 0"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE ai_search_job "
        "DROP COLUMN filter_date_from, "
        "DROP COLUMN filter_date_to, "
        "DROP COLUMN filter_category_ids, "
        "DROP COLUMN filter_radius_km, "
        "DROP COLUMN filter_focus, "
        "DROP COLUMN skipped_not_matching"
    )
