"""Friendships and friend links (R12); notifications may name an actor.

Friendships are stored symmetrically (two rows). The friend link token is stored in plain
text so the link can be shown again; it only grants befriending and can be rotated. The
new `notification.actor_user_id` (e.g. who accepted the link) goes with that account.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE friendship (
            user_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            friend_id uuid NOT NULL REFERENCES app_user (id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, friend_id),
            CHECK (user_id <> friend_id)
        )
        """
    )
    op.execute("CREATE INDEX friendship_friend_idx ON friendship (friend_id)")
    op.execute(
        """
        CREATE TABLE friend_link (
            user_id uuid PRIMARY KEY REFERENCES app_user (id) ON DELETE CASCADE,
            token text NOT NULL UNIQUE,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "ALTER TABLE notification ADD COLUMN actor_user_id uuid "
        "REFERENCES app_user (id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE notification DROP COLUMN actor_user_id")
    op.execute("DROP TABLE friend_link")
    op.execute("DROP TABLE friendship")
