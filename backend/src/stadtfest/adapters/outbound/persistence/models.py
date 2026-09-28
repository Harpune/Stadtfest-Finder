"""SQLAlchemy table mappings. The schema itself is owned by Alembic migrations."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import ARRAY, Computed, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all tables."""


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


class EventImageRow(Base):
    """Table `event_image` (filled from R08 on)."""

    __tablename__ = "event_image"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("event.id", ondelete="CASCADE"))
    object_key: Mapped[str]
    thumb_key: Mapped[str | None]
    position: Mapped[int] = mapped_column(default=0)
    width: Mapped[int | None]
    height: Mapped[int | None]
    status: Mapped[str] = mapped_column(default="processing")
