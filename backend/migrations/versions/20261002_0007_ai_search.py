"""AI search jobs and rejected sources (R10).

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE ai_search_job (
            id uuid PRIMARY KEY,
            moderator_id uuid REFERENCES app_user (id) ON DELETE SET NULL,
            region_id uuid NOT NULL REFERENCES region (id),
            postal_code text NOT NULL CHECK (postal_code ~ '^[0-9]{5}$'),
            place_name text NOT NULL DEFAULT '',
            status text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'completed', 'failed')),
            created_at timestamptz NOT NULL DEFAULT now(),
            started_at timestamptz,
            finished_at timestamptz,
            new_event_ids uuid[] NOT NULL DEFAULT '{}',
            skipped_duplicate integer NOT NULL DEFAULT 0,
            skipped_out_of_region integer NOT NULL DEFAULT 0,
            skipped_invalid integer NOT NULL DEFAULT 0,
            skipped_unverified_source integer NOT NULL DEFAULT 0,
            error_code text,
            log jsonb NOT NULL DEFAULT '{}'
        )
        """
    )
    op.execute(
        "CREATE INDEX ai_search_job_moderator_idx ON ai_search_job (moderator_id, created_at)"
    )
    op.execute(
        "CREATE INDEX ai_search_job_active_idx ON ai_search_job (created_at) "
        "WHERE status IN ('queued', 'running')"
    )
    op.execute(
        """
        CREATE TABLE rejected_source (
            region_id uuid NOT NULL REFERENCES region (id),
            url_normalized text NOT NULL,
            rejected_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (region_id, url_normalized)
        )
        """
    )
    op.execute(
        "CREATE INDEX event_source_url_idx ON event (region_id) WHERE source_url IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX event_source_url_idx")
    op.execute("DROP TABLE rejected_source")
    op.execute("DROP TABLE ai_search_job")
