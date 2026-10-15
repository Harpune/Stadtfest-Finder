"""Invitations (R14): one invitation per host and event, invitees with their answer.

The message is user free text (never logged). Invitations go with the host's account,
invitee rows with the invitee's account. Notifications may reference an invitation.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE invitation (
            id uuid PRIMARY KEY,
            event_id uuid NOT NULL REFERENCES event (id) ON DELETE CASCADE,
            host_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            message text CHECK (char_length(message) <= 280),
            link_token text UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now(),
            last_reminder_at timestamptz,
            UNIQUE (event_id, host_id)
        )
        """
    )
    op.execute("CREATE INDEX invitation_host_idx ON invitation (host_id)")
    op.execute(
        """
        CREATE TABLE invitee (
            invitation_id uuid NOT NULL REFERENCES invitation (id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            status text NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'accepted', 'declined')),
            invited_at timestamptz NOT NULL DEFAULT now(),
            responded_at timestamptz,
            PRIMARY KEY (invitation_id, user_id)
        )
        """
    )
    op.execute("CREATE INDEX invitee_user_idx ON invitee (user_id)")
    op.execute(
        "ALTER TABLE notification ADD COLUMN invitation_id uuid "
        "REFERENCES invitation (id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE notification DROP COLUMN invitation_id")
    op.execute("DROP TABLE invitee")
    op.execute("DROP TABLE invitation")
