"""Uploads and event images (R08).

Variant keys are derived from the image ID, so the key columns of R02 are dropped.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE upload (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            content_type text NOT NULL
                CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp')),
            size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 10485760),
            created_at timestamptz NOT NULL DEFAULT now(),
            consumed_at timestamptz
        )
        """
    )
    # The daily clean-up looks for old uploads that were never attached.
    op.execute("CREATE INDEX upload_stale_idx ON upload (created_at) WHERE consumed_at IS NULL")
    op.execute("CREATE INDEX upload_user_idx ON upload (user_id)")

    op.execute("ALTER TABLE event_image DROP COLUMN object_key, DROP COLUMN thumb_key")
    op.execute(
        """
        ALTER TABLE event_image
            ADD COLUMN upload_id uuid REFERENCES upload (id) ON DELETE SET NULL,
            ADD COLUMN created_at timestamptz NOT NULL DEFAULT now(),
            ADD CONSTRAINT event_image_position_check CHECK (position >= 0),
            ADD CONSTRAINT event_image_position_key UNIQUE (event_id, position)
                DEFERRABLE INITIALLY DEFERRED
        """
    )
    op.execute("CREATE UNIQUE INDEX event_image_upload_key ON event_image (upload_id)")
    op.execute("DROP INDEX event_image_event_idx")


def downgrade() -> None:
    op.execute("CREATE INDEX event_image_event_idx ON event_image (event_id, position)")
    op.execute("DROP INDEX event_image_upload_key")
    op.execute(
        """
        ALTER TABLE event_image
            DROP CONSTRAINT event_image_position_key,
            DROP CONSTRAINT event_image_position_check,
            DROP COLUMN created_at,
            DROP COLUMN upload_id,
            ADD COLUMN object_key text NOT NULL DEFAULT '',
            ADD COLUMN thumb_key text
        """
    )
    op.execute("DROP TABLE upload")
