"""Catalog: categories, regions, events, program items, event images.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # unaccent() is only STABLE; an IMMUTABLE wrapper allows generated columns and indexes.
    op.execute(
        """
        CREATE FUNCTION immutable_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        """
    )
    op.execute(
        """
        CREATE TABLE category (
            id uuid PRIMARY KEY,
            name text NOT NULL CHECK (length(name) BETWEEN 1 AND 40),
            emoji text NOT NULL,
            color text NOT NULL CHECK (color ~ '^#[0-9A-F]{6}$'),
            active boolean NOT NULL DEFAULT true,
            sort_order integer NOT NULL DEFAULT 0,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX category_name_key ON category (lower(name))")
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
    op.execute(
        """
        CREATE TABLE event (
            id uuid PRIMARY KEY,
            region_id uuid NOT NULL REFERENCES region (id),
            name text NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
            short_name text NOT NULL,
            category_id uuid REFERENCES category (id),
            status text NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'published', 'cancelled')),
            start_date date,
            end_date date,
            opening_hours text[] NOT NULL DEFAULT '{}',
            price text,
            place text NOT NULL DEFAULT '',
            address text NOT NULL DEFAULT '',
            city text NOT NULL DEFAULT '',
            postal_code text CHECK (postal_code ~ '^[0-9]{5}$'),
            location geography(Point, 4326),
            description text,
            transit text,
            parking text,
            website_url text,
            cancel_reason text,
            source text NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'ai')),
            source_url text,
            ai_job_id uuid,
            found_at timestamptz,
            favorite_count integer NOT NULL DEFAULT 0 CHECK (favorite_count >= 0),
            version integer NOT NULL DEFAULT 1,
            created_by uuid,
            updated_by uuid,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            published_at timestamptz,
            deleted_at timestamptz,
            search_text text GENERATED ALWAYS AS (
                immutable_unaccent(lower(name || ' ' || short_name || ' ' || place || ' ' || city))
            ) STORED,
            CONSTRAINT event_dates_ordered CHECK (end_date >= start_date),
            CONSTRAINT event_public_complete CHECK (
                status = 'draft' OR (
                    category_id IS NOT NULL AND start_date IS NOT NULL
                    AND end_date IS NOT NULL AND location IS NOT NULL
                )
            )
        )
        """
    )
    op.execute("CREATE INDEX event_location_idx ON event USING gist (location)")
    op.execute("CREATE INDEX event_search_text_idx ON event USING gin (search_text gin_trgm_ops)")
    op.execute(
        "CREATE INDEX event_listed_idx ON event (end_date, start_date)"
        " WHERE deleted_at IS NULL AND status IN ('published', 'cancelled')"
    )
    op.execute("CREATE INDEX event_region_idx ON event (region_id) WHERE deleted_at IS NULL")
    op.execute("CREATE INDEX event_category_idx ON event (category_id)")
    op.execute(
        """
        CREATE TABLE program_item (
            id uuid PRIMARY KEY,
            event_id uuid NOT NULL REFERENCES event (id) ON DELETE CASCADE,
            date date NOT NULL,
            time_label text NOT NULL DEFAULT '',
            title text NOT NULL,
            subtitle text,
            position integer NOT NULL DEFAULT 0
        )
        """
    )
    op.execute("CREATE INDEX program_item_event_idx ON program_item (event_id, position)")
    op.execute(
        """
        CREATE TABLE event_image (
            id uuid PRIMARY KEY,
            event_id uuid NOT NULL REFERENCES event (id) ON DELETE CASCADE,
            object_key text NOT NULL,
            thumb_key text,
            position integer NOT NULL DEFAULT 0,
            width integer,
            height integer,
            status text NOT NULL DEFAULT 'processing'
                CHECK (status IN ('processing', 'ready', 'failed'))
        )
        """
    )
    op.execute("CREATE INDEX event_image_event_idx ON event_image (event_id, position)")


def downgrade() -> None:
    op.execute("DROP TABLE event_image")
    op.execute("DROP TABLE program_item")
    op.execute("DROP TABLE event")
    op.execute("DROP TABLE region")
    op.execute("DROP TABLE category")
    op.execute("DROP FUNCTION immutable_unaccent(text)")
