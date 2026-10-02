"""JSON encoding of read models for the cache (public data only)."""

from __future__ import annotations

from datetime import date
from typing import cast
from uuid import UUID

from stadtfest.application.events.views import (
    CategoryView,
    EventCountView,
    EventPageView,
    EventSummaryView,
    ImageView,
)
from stadtfest.application.shared.ports import JsonValue
from stadtfest.domain.events.event import EventStatus
from stadtfest.domain.events.geo import GeoPoint

type JsonObject = dict[str, JsonValue]


def _image_to_json(image: ImageView | None) -> JsonValue:
    if image is None:
        return None
    return {
        "url": image.url,
        "thumb": image.thumb_url,
        "card": image.card_url,
        "jpeg": image.jpeg_url,
        "w": image.width,
        "h": image.height,
    }


def _image_from_json(value: JsonValue) -> ImageView | None:
    if not isinstance(value, dict):
        return None
    return ImageView(
        url=str(value["url"]),
        thumb_url=str(value["thumb"]),
        width=cast("int | None", value.get("w")),
        height=cast("int | None", value.get("h")),
        card_url=cast("str | None", value.get("card")),
        jpeg_url=cast("str | None", value.get("jpeg")),
    )


def summary_to_json(item: EventSummaryView) -> JsonObject:
    """Encode an event summary."""
    return {
        "id": str(item.id),
        "name": item.name,
        "shortName": item.short_name,
        "status": item.status.value,
        "start": item.start_date.isoformat(),
        "end": item.end_date.isoformat(),
        "place": item.place,
        "city": item.city,
        "lat": item.location.lat,
        "lon": item.location.lon,
        "categoryId": str(item.category_id),
        "distanceKm": item.distance_km,
        "cover": _image_to_json(item.cover_image),
    }


def summary_from_json(value: JsonObject) -> EventSummaryView:
    """Decode an event summary."""
    distance = value["distanceKm"]
    return EventSummaryView(
        id=UUID(str(value["id"])),
        name=str(value["name"]),
        short_name=str(value["shortName"]),
        status=EventStatus(str(value["status"])),
        start_date=date.fromisoformat(str(value["start"])),
        end_date=date.fromisoformat(str(value["end"])),
        place=str(value["place"]),
        city=str(value["city"]),
        location=GeoPoint(float(cast("float", value["lat"])), float(cast("float", value["lon"]))),
        category_id=UUID(str(value["categoryId"])),
        distance_km=float(cast("float", distance)) if distance is not None else None,
        cover_image=_image_from_json(value["cover"]),
    )


def page_to_json(page: EventPageView) -> JsonObject:
    """Encode a result page."""
    return {"items": [summary_to_json(item) for item in page.items], "next": page.next_cursor}


def page_from_json(value: JsonObject) -> EventPageView:
    """Decode a result page."""
    items = cast("list[JsonObject]", value["items"])
    next_cursor = value["next"]
    return EventPageView(
        items=tuple(summary_from_json(item) for item in items),
        next_cursor=str(next_cursor) if next_cursor is not None else None,
    )


def count_to_json(count: EventCountView) -> JsonObject:
    """Encode counts."""
    return {"total": count.total, "byCategory": {str(k): v for k, v in count.by_category.items()}}


def count_from_json(value: JsonObject) -> EventCountView:
    """Decode counts."""
    by_category = cast("dict[str, int]", value["byCategory"])
    return EventCountView(
        total=int(cast("int", value["total"])),
        by_category={UUID(k): int(v) for k, v in by_category.items()},
    )


def categories_to_json(categories: list[CategoryView]) -> list[JsonValue]:
    """Encode categories."""
    return [
        {"id": str(c.id), "name": c.name, "emoji": c.emoji, "color": c.color, "order": c.sort_order}
        for c in categories
    ]


def categories_from_json(value: list[JsonValue]) -> list[CategoryView]:
    """Decode categories."""
    result: list[CategoryView] = []
    for raw in value:
        item = cast("JsonObject", raw)
        result.append(
            CategoryView(
                id=UUID(str(item["id"])),
                name=str(item["name"]),
                emoji=str(item["emoji"]),
                color=str(item["color"]),
                sort_order=int(cast("int", item["order"])),
            )
        )
    return result
