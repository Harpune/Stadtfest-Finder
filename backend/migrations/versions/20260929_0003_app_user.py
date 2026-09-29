"""User accounts (R05): IdP subject and name only, no email (E-08).

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE app_user (
            id uuid PRIMARY KEY,
            idp_subject text NOT NULL UNIQUE,
            first_name text NOT NULL DEFAULT '' CHECK (length(first_name) <= 50),
            last_name text NOT NULL DEFAULT '' CHECK (length(last_name) <= 50),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE app_user")
