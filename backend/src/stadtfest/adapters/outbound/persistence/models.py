"""SQLAlchemy table mappings. The schema itself is owned by Alembic migrations."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import ARRAY, Computed, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all tables."""

    # All timestamp columns are `timestamptz` (migrations); bind aware datetimes as such.
    type_annotation_map: ClassVar[dict[Any, Any]] = {datetime: DateTime(timezone=True)}


class CategoryRow(Base):
    """Table `category`."""

    __tablename__ = "category"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str]
    emoji: Mapped[str]
    color: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")


class RegionRow(Base):
    """Table `region` (E-05: a region is a set of postal codes)."""

    __tablename__ = "region"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    postal_codes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)


class AppUserRow(Base):
    """Table `app_user` (R05). No email address and no provider list (E-08)."""

    __tablename__ = "app_user"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    idp_subject: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str] = mapped_column(default="")
    last_name: Mapped[str] = mapped_column(default="")
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")


class EventRow(Base):
    """Table `event`."""

    __tablename__ = "event"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    region_id: Mapped[UUID] = mapped_column(ForeignKey("region.id"))
    name: Mapped[str]
    short_name: Mapped[str]
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("category.id"))
    status: Mapped[str] = mapped_column(String, default="draft")
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    opening_hours: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    price: Mapped[str | None]
    place: Mapped[str] = mapped_column(default="")
    address: Mapped[str] = mapped_column(default="")
    city: Mapped[str] = mapped_column(default="")
    postal_code: Mapped[str | None]
    location: Mapped[object | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    description: Mapped[str | None]
    transit: Mapped[str | None]
    parking: Mapped[str | None]
    website_url: Mapped[str | None]
    cancel_reason: Mapped[str | None]
    source: Mapped[str] = mapped_column(default="manual")
    source_url: Mapped[str | None]
    ai_job_id: Mapped[UUID | None]
    found_at: Mapped[datetime | None]
    favorite_count: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=1)
    created_by: Mapped[UUID | None]
    updated_by: Mapped[UUID | None]
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(server_default="now()")
    published_at: Mapped[datetime | None]
    deleted_at: Mapped[datetime | None]
    search_text: Mapped[str] = mapped_column(
        Computed(
            "immutable_unaccent(lower(name || ' ' || short_name || ' ' || place || ' ' || city))"
        )
    )


class ProgramItemRow(Base):
    """Table `program_item`."""

    __tablename__ = "program_item"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("event.id", ondelete="CASCADE"))
    date: Mapped[date]
    time_label: Mapped[str] = mapped_column(default="")
    title: Mapped[str]
    subtitle: Mapped[str | None]
    position: Mapped[int] = mapped_column(default=0)


class UploadRow(Base):
    """Table `upload` (R08): signed upload slots of moderators."""

    __tablename__ = "upload"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    content_type: Mapped[str]
    size_bytes: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    consumed_at: Mapped[datetime | None]


class EventImageRow(Base):
    """Table `event_image` (R08). Variant keys are derived from the ID."""

    __tablename__ = "event_image"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("event.id", ondelete="CASCADE"))
    upload_id: Mapped[UUID | None] = mapped_column(ForeignKey("upload.id", ondelete="SET NULL"))
    position: Mapped[int] = mapped_column(default=0)
    width: Mapped[int | None]
    height: Mapped[int | None]
    status: Mapped[str] = mapped_column(default="processing")
    created_at: Mapped[datetime] = mapped_column(server_default="now()")


class FavoriteRow(Base):
    """Table `favorite` (R06)."""

    __tablename__ = "favorite"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("event.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default="now()")


class OutboxRow(Base):
    """Table `outbox` (R07, ADR 0005): domain events written with the change itself."""

    __tablename__ = "outbox"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    type: Mapped[str]
    payload: Mapped[dict[str, object]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(server_default="now()")
    dispatched_at: Mapped[datetime | None]


class AiSearchJobRow(Base):
    """Table `ai_search_job` (R10). The log holds no user data."""

    __tablename__ = "ai_search_job"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    moderator_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL")
    )
    region_id: Mapped[UUID] = mapped_column(ForeignKey("region.id"))
    postal_code: Mapped[str]
    place_name: Mapped[str] = mapped_column(default="")
    status: Mapped[str] = mapped_column(default="queued")
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    new_event_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID(as_uuid=True)), default=list)
    skipped_duplicate: Mapped[int] = mapped_column(default=0)
    skipped_out_of_region: Mapped[int] = mapped_column(default=0)
    skipped_invalid: Mapped[int] = mapped_column(default=0)
    skipped_unverified_source: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None]
    log: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)


class RejectedSourceRow(Base):
    """Table `rejected_source` (R10-US4): discarded AI sources are never suggested again."""

    __tablename__ = "rejected_source"

    region_id: Mapped[UUID] = mapped_column(ForeignKey("region.id"), primary_key=True)
    url_normalized: Mapped[str] = mapped_column(primary_key=True)
    rejected_at: Mapped[datetime] = mapped_column(server_default="now()")
