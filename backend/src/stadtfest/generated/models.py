# Generated from api/openapi.yaml by `make gen` - DO NOT EDIT.

from __future__ import annotations

from datetime import date as date_aliased
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyUrl, AwareDatetime, BaseModel, ConfigDict, Field, RootModel


class Category(BaseModel):
    """Event category (filter chip, marker border color)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    name: Annotated[str, Field(examples=["Stadtfest"])]
    emoji: Annotated[str, Field(examples=["🎪"])]
    color: Annotated[str, Field(examples=["#FFB547"], pattern="^#[0-9A-F]{6}$")]
    sort_order: Annotated[int, Field(alias="sortOrder", ge=0)]


class CategoryRef(BaseModel):
    """Category as embedded in an event detail."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    name: str
    emoji: str
    color: Annotated[str, Field(pattern="^#[0-9A-F]{6}$")]


class PublicEventStatus(RootModel[Literal["published", "cancelled"]]):
    root: Annotated[
        Literal["published", "cancelled"],
        Field(description='Status of a publicly visible event. "Past" is derived from `endDate`.'),
    ]


class Image(BaseModel):
    """Event image variants (R08)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    url: AnyUrl
    thumb_url: Annotated[AnyUrl, Field(alias="thumbUrl")]
    width: Annotated[int | None, Field(ge=1)] = None
    height: Annotated[int | None, Field(ge=1)] = None


class EventSummary(BaseModel):
    """Event as shown in carousel, list and timeline."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    name: str
    short_name: Annotated[
        str, Field(alias="shortName", description="Short name for the selected map pin.")
    ]
    status: PublicEventStatus
    start_date: Annotated[date_aliased, Field(alias="startDate")]
    end_date: Annotated[date_aliased, Field(alias="endDate")]
    place: str
    city: str
    lat: float
    lon: float
    category_id: Annotated[UUID, Field(alias="categoryId")]
    distance_km: Annotated[
        float | None,
        Field(alias="distanceKm", description="Distance to the reference point, if one was given."),
    ] = None
    cover_image: Annotated[Image | None, Field(alias="coverImage")] = None


class EventPage(BaseModel):
    """One page of events."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    items: list[EventSummary]
    next_cursor: Annotated[
        str | None,
        Field(alias="nextCursor", description="Cursor for the next page, `null` on the last page."),
    ] = None


type ByCategoryAdditionalProperty = Annotated[int, Field(ge=0)]


class EventCount(BaseModel):
    """Result counts for filter previews."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    total: Annotated[int, Field(ge=0)]
    by_category: Annotated[
        dict[str, ByCategoryAdditionalProperty],
        Field(
            alias="byCategory",
            description="Category ID -> number of events matching all filters except categories.",
        ),
    ]


class ProgramItem(BaseModel):
    """Entry of the event program."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    date: date_aliased
    time_label: Annotated[str, Field(alias="timeLabel", examples=["10:45 Uhr"])]
    title: str
    subtitle: str | None = None


class EventDetail(BaseModel):
    """Full public event detail."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    name: str
    short_name: Annotated[str, Field(alias="shortName")]
    status: PublicEventStatus
    cancel_reason: Annotated[str | None, Field(alias="cancelReason")] = None
    category: CategoryRef
    start_date: Annotated[date_aliased, Field(alias="startDate")]
    end_date: Annotated[date_aliased, Field(alias="endDate")]
    opening_hours: Annotated[list[str], Field(alias="openingHours")]
    price: str | None = None
    place: str
    address: str
    city: str
    postal_code: Annotated[str, Field(alias="postalCode", pattern="^[0-9]{5}$")]
    lat: float
    lon: float
    description: str | None = None
    program: list[ProgramItem]
    transit: str | None = None
    parking: str | None = None
    website_url: Annotated[AnyUrl | None, Field(alias="websiteUrl")] = None
    images: list[Image]
    distance_km: Annotated[float | None, Field(alias="distanceKm")] = None
    is_favorite: Annotated[
        bool | None,
        Field(
            alias="isFavorite",
            description="Whether the caller marked the event as favorite. Only present with a token.",
        ),
    ] = None


class FavoriteEntry(EventSummary):
    """A favorite with its event, as shown in the timeline (R06-US2)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    category_name: Annotated[str, Field(alias="categoryName")]
    emoji: str
    favorited_at: Annotated[AwareDatetime, Field(alias="favoritedAt")]


class FavoriteList(BaseModel):
    """Favorites of the caller, ordered by start date."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    items: list[FavoriteEntry]


class GeocodeResult(BaseModel):
    """A geocoding suggestion."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    label: Annotated[str, Field(examples=["73430 Aalen"])]
    postal_code: Annotated[str | None, Field(alias="postalCode", pattern="^[0-9]{5}$")] = None
    city: str
    lat: float
    lon: float
    kind: Literal["postcode", "city", "address"]


class ReverseGeocodeResult(BaseModel):
    """Place for coordinates."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    postal_code: Annotated[str | None, Field(alias="postalCode", pattern="^[0-9]{5}$")] = None
    city: str
    label: str


class Role(RootModel[Literal["user", "moderator", "category_admin"]]):
    root: Literal["user", "moderator", "category_admin"]


class RegionRef(BaseModel):
    """Moderation region of a moderator."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    key: Annotated[str, Field(examples=["ostalb"])]
    name: Annotated[str, Field(examples=["Ostalbkreis"])]


class UpdateMeRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    first_name: Annotated[str, Field(alias="firstName", max_length=50, min_length=1)]
    last_name: Annotated[str, Field(alias="lastName", max_length=50, min_length=1)]


class Error(BaseModel):
    """Common error format for all non-2xx responses."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    error: Annotated[
        str,
        Field(
            description="Machine-readable error code, e.g. `validation_failed`, `not_found`.",
            examples=["validation_failed"],
        ),
    ]
    message: Annotated[
        str,
        Field(
            description="Human-readable message (German, suitable for display).",
            examples=["Bitte fülle die markierten Pflichtfelder aus"],
        ),
    ]
    fields: Annotated[
        dict[str, str] | None, Field(description="Field-level errors keyed by field name.")
    ] = None


class HealthStatus(BaseModel):
    """Result of the liveness probe."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    status: Literal["ok"]


class ReadinessStatus(BaseModel):
    """Result of the readiness probe with one entry per dependency."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    status: Literal["ok", "unavailable"]
    checks: Annotated[
        dict[str, Literal["ok", "unavailable"]],
        Field(description="Status per dependency, e.g. `database`, `redis`."),
    ]


class Me(BaseModel):
    """Profile of the signed-in user. Contains no email address (E-08)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: Annotated[UUID, Field(description="Internal user ID (not the IdP subject).")]
    first_name: Annotated[
        str,
        Field(
            alias="firstName",
            description="Empty if the IdP did not provide a name (e.g. Apple without name sharing).",
            max_length=50,
        ),
    ]
    last_name: Annotated[str, Field(alias="lastName", max_length=50)]
    roles: Annotated[list[Role], Field(description="Effective roles from the token.")]
    region: RegionRef | None = None
