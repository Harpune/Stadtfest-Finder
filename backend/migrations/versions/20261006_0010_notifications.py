"""Notifications, notification settings and push devices (R11).

Notifications are stored structurally (type + IDs, E-09); `dedupe_key` enforces the
idempotency rules per user (one reminder per event and day, one change per event and hour,
one entry per event for `near` and `cancel`). The home is the ZIP code center (E-10).
All rows go with the user account (`ON DELETE CASCADE`, Art. 17 GDPR).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE notification (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            type text NOT NULL,
            event_id uuid REFERENCES event (id) ON DELETE CASCADE,
            dedupe_key text NOT NULL,
            read boolean NOT NULL DEFAULT false,
            pushed boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (user_id, dedupe_key)
        )
        """
    )
    op.execute(
        "CREATE INDEX notification_user_idx ON notification (user_id, created_at DESC, id DESC)"
    )
    op.execute("CREATE INDEX notification_created_idx ON notification (created_at)")
    op.execute(
        """
        CREATE TABLE notification_settings (
            user_id uuid PRIMARY KEY REFERENCES app_user (id) ON DELETE CASCADE,
            remind boolean NOT NULL,
            remind_days_before smallint NOT NULL CHECK (remind_days_before IN (1, 3, 7)),
            near boolean NOT NULL,
            home_postal_code text CHECK (home_postal_code ~ '^[0-9]{5}$'),
            home_place_name text,
            home_location geography(Point, 4326),
            near_radius_km smallint NOT NULL
                CHECK (near_radius_km BETWEEN 5 AND 150 AND near_radius_km % 5 = 0),
            change boolean NOT NULL,
            invite boolean NOT NULL,
            rsvp boolean NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now(),
            CHECK (
                (home_postal_code IS NULL) = (home_place_name IS NULL)
                AND (home_postal_code IS NULL) = (home_location IS NULL)
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX notification_settings_home_idx "
        "ON notification_settings USING gist (home_location)"
    )
    op.execute(
        """
        CREATE TABLE device (
            token text PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            platform text NOT NULL CHECK (platform IN ('ios', 'android')),
            provider text NOT NULL CHECK (provider IN ('expo', 'direct')),
            created_at timestamptz NOT NULL DEFAULT now(),
            last_seen_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX device_user_idx ON device (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE device")
    op.execute("DROP TABLE notification_settings")
    op.execute("DROP TABLE notification")
