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


class CategoryEmoji(
    RootModel[Literal["🎪", "🎡", "🎄", "🐎", "🍺", "🍷", "🎭", "🎶", "🏰", "🎃", "🌸", "🔥"]]
):
    root: Annotated[
        Literal["🎪", "🎡", "🎄", "🐎", "🍺", "🍷", "🎭", "🎶", "🏰", "🎃", "🌸", "🔥"],
        Field(description="One of the 12 preset emojis (design reference §14)."),
    ]


class CategoryColor(
    RootModel[Literal["#FFB547", "#FF6B8B", "#5EEAD4", "#8B9CFF", "#7ED957", "#C792EA"]]
):
    root: Annotated[
        Literal["#FFB547", "#FF6B8B", "#5EEAD4", "#8B9CFF", "#7ED957", "#C792EA"],
        Field(description="One of the 6 preset colors (theme-farben.md)."),
    ]


class AiSearchStatus(RootModel[Literal["queued", "running", "completed", "failed"]]):
    root: Literal["queued", "running", "completed", "failed"]


class AiSearchRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    postal_code: Annotated[str, Field(alias="postalCode", pattern="^[0-9]{5}$")]


class AiSearchSkipped(BaseModel):
    """Finds that were not stored, by reason (counts only, no content)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    duplicate: Annotated[int, Field(ge=0)]
    out_of_area: Annotated[
        int,
        Field(
            alias="outOfArea",
            description="Outside the search radius around the postal code, or no location.",
            ge=0,
        ),
    ]
    invalid: Annotated[int, Field(ge=0)]
    unverified_source: Annotated[int, Field(alias="unverifiedSource", ge=0)]


class AiSearch(BaseModel):
    """An AI search job (R10)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    postal_code: Annotated[str, Field(alias="postalCode")]
    place_name: Annotated[str, Field(alias="placeName")]
    status: AiSearchStatus
    created_at: Annotated[AwareDatetime, Field(alias="createdAt")]
    started_at: Annotated[AwareDatetime | None, Field(alias="startedAt")] = None
    finished_at: Annotated[AwareDatetime | None, Field(alias="finishedAt")] = None
    new_event_ids: Annotated[list[UUID], Field(alias="newEventIds")]
    skipped: AiSearchSkipped
    error_code: Annotated[
        Literal["llm_unavailable", "search_unavailable", "timeout", "internal"] | None,
        Field(alias="errorCode"),
    ] = None


class ModCategory(BaseModel):
    """Category in the moderation view, including inactive ones."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    name: str
    emoji: str
    color: Annotated[str, Field(pattern="^#[0-9A-F]{6}$")]
    active: bool
    sort_order: Annotated[int, Field(alias="sortOrder", ge=0)]
    event_count: Annotated[
        int, Field(alias="eventCount", description="Events of all statuses except deleted.", ge=0)
    ]


class ModCategoryCreate(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    name: Annotated[str, Field(max_length=40, min_length=1)]
    emoji: CategoryEmoji
    color: CategoryColor
    active: bool | None = True


class ModCategoryPatch(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    name: Annotated[str | None, Field(max_length=40, min_length=1)] = None
    emoji: CategoryEmoji | None = None
    color: CategoryColor | None = None
    active: bool | None = None


class CategoryOrderRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    ids: Annotated[list[UUID], Field(max_length=100, min_length=1)]


class CategoryDeleted(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    moved_events: Annotated[
        int,
        Field(alias="movedEvents", description="Events moved to the replacement category.", ge=0),
    ]
    replacement_id: Annotated[UUID | None, Field(alias="replacementId")] = None


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
    """Event image variants (R08), WebP with immutable URLs: `url` (long edge 1,600 px),
    `cardUrl` (600 px), `thumbUrl` (200 px). `jpegUrl` is the full size as JPEG, e.g. for
    link previews.

    """

    model_config = ConfigDict(
        populate_by_name=True,
    )
    url: AnyUrl
    card_url: Annotated[AnyUrl | None, Field(alias="cardUrl")] = None
    thumb_url: Annotated[AnyUrl, Field(alias="thumbUrl")]
    jpeg_url: Annotated[AnyUrl | None, Field(alias="jpegUrl")] = None
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


class ModEventStatus(RootModel[Literal["draft", "published", "past", "cancelled"]]):
    root: Annotated[
        Literal["draft", "published", "past", "cancelled"],
        Field(
            description="Status in the moderation view. `past` is derived for published events whose end date\nis before today (Europe/Berlin).\n"
        ),
    ]


class EventSource(RootModel[Literal["manual", "ai"]]):
    root: Annotated[
        Literal["manual", "ai"],
        Field(description="`manual` or found by the AI search (`ai`, R10)."),
    ]


class ModEventSummary(BaseModel):
    """Row of the moderation overview."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    name: str
    status: ModEventStatus
    start_date: Annotated[date_aliased | None, Field(alias="startDate")] = None
    end_date: Annotated[date_aliased | None, Field(alias="endDate")] = None
    place: str
    city: str
    category_id: Annotated[UUID | None, Field(alias="categoryId")] = None
    favorite_count: Annotated[int, Field(alias="favoriteCount", ge=0)]
    source: EventSource
    version: Annotated[int, Field(ge=1)]


class ModEventList(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    items: list[ModEventSummary]


class ModProgramItem(BaseModel):
    """Program entry as entered by the moderator."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    date: date_aliased
    time_label: Annotated[str, Field(alias="timeLabel", max_length=40)]
    title: Annotated[str, Field(max_length=120, min_length=1)]
    subtitle: Annotated[str | None, Field(max_length=200)] = None


class ModImageStatus(RootModel[Literal["processing", "ready", "failed"]]):
    root: Literal["processing", "ready", "failed"]


class ModImage(BaseModel):
    """An event image in the moderation view. Variants only when `ready`."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    status: ModImageStatus
    position: Annotated[int, Field(description="0 is the cover image.", ge=0)]
    image: Annotated[Image | None, Field(description="Variants; `null` until the image is ready.")]


class UploadContentType(RootModel[Literal["image/jpeg", "image/png", "image/webp"]]):
    root: Literal["image/jpeg", "image/png", "image/webp"]


class UploadRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    content_type: Annotated[UploadContentType, Field(alias="contentType")]
    size_bytes: Annotated[
        int,
        Field(
            alias="sizeBytes",
            description="Exact file size; attaching the upload fails if the stored file differs.",
            ge=1,
            le=10485760,
        ),
    ]


class Upload(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    upload_id: Annotated[UUID, Field(alias="uploadId")]
    url: AnyUrl
    method: Literal["PUT"]
    headers: Annotated[
        dict[str, str], Field(description="Headers the upload request must send unchanged.")
    ]
    expires_at: Annotated[AwareDatetime, Field(alias="expiresAt")]


class AttachImageRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    upload_id: Annotated[UUID, Field(alias="uploadId")]
    position: Annotated[
        int | None, Field(description="Insert position; appended if missing.", ge=0, le=11)
    ] = None


class ImageOrderRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    image_ids: Annotated[list[UUID], Field(alias="imageIds", max_length=12, min_length=1)]


class OpeningHour(RootModel[str]):
    root: Annotated[str, Field(max_length=80)]


class ModEventFields(BaseModel):
    """Editable fields. Lengths: name 120, short name 18, description 5,000, 10 opening hour
    lines of 80, 50 program entries. Postal code and city come from geocoding.

    """

    model_config = ConfigDict(
        populate_by_name=True,
    )
    short_name: Annotated[
        str | None,
        Field(
            alias="shortName",
            description="Defaults to the name shortened to 18 characters.",
            max_length=18,
        ),
    ] = None
    category_id: Annotated[UUID | None, Field(alias="categoryId")] = None
    start_date: Annotated[date_aliased | None, Field(alias="startDate")] = None
    end_date: Annotated[date_aliased | None, Field(alias="endDate")] = None
    opening_hours: Annotated[
        list[OpeningHour] | None, Field(alias="openingHours", max_length=10)
    ] = None
    price: Annotated[str | None, Field(max_length=200)] = None
    place: Annotated[str | None, Field(max_length=120)] = None
    address: Annotated[str | None, Field(max_length=200)] = None
    city: Annotated[str | None, Field(max_length=120)] = None
    postal_code: Annotated[str | None, Field(alias="postalCode", pattern="^[0-9]{5}$")] = None
    lat: Annotated[float | None, Field(ge=-90.0, le=90.0)] = None
    lon: Annotated[float | None, Field(ge=-180.0, le=180.0)] = None
    description: Annotated[str | None, Field(max_length=5000)] = None
    program: Annotated[list[ModProgramItem] | None, Field(max_length=50)] = None
    transit: Annotated[str | None, Field(max_length=500)] = None
    parking: Annotated[str | None, Field(max_length=500)] = None
    website_url: Annotated[str | None, Field(alias="websiteUrl", max_length=500)] = None
    cancel_reason: Annotated[str | None, Field(alias="cancelReason", max_length=500)] = None


class ModEventCreate(ModEventFields):
    """New draft; only the name is required."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    name: Annotated[str, Field(max_length=120, min_length=1)]


class ModEventPatch(ModEventFields):
    """Merge patch of an event; all fields optional."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    name: Annotated[str | None, Field(max_length=120, min_length=1)] = None


class CancelRequest(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
    reason: Annotated[
        str | None, Field(description="Shown in the cancellation notice (R11).", max_length=500)
    ] = None


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
    street: Annotated[
        str | None,
        Field(description="Street and house number; only `/v1/mod/geocode/reverse` fills it."),
    ] = None
    postal_code: Annotated[str | None, Field(alias="postalCode", pattern="^[0-9]{5}$")] = None
    city: str
    label: str


class Role(RootModel[Literal["user", "moderator", "category_admin"]]):
    root: Literal["user", "moderator", "category_admin"]


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


class ModEventDetail(BaseModel):
    """Event with all editable fields; fields of drafts may be empty."""

    model_config = ConfigDict(
        populate_by_name=True,
    )
    id: UUID
    name: str
    short_name: Annotated[str, Field(alias="shortName")]
    status: ModEventStatus
    category_id: Annotated[UUID | None, Field(alias="categoryId")] = None
    start_date: Annotated[date_aliased | None, Field(alias="startDate")] = None
    end_date: Annotated[date_aliased | None, Field(alias="endDate")] = None
    opening_hours: Annotated[list[str], Field(alias="openingHours")]
    price: str | None = None
    place: str
    address: str
    city: str
    postal_code: Annotated[str | None, Field(alias="postalCode")] = None
    lat: float | None = None
    lon: float | None = None
    description: str | None = None
    program: list[ModProgramItem]
    transit: str | None = None
    parking: str | None = None
    website_url: Annotated[str | None, Field(alias="websiteUrl")] = None
    cancel_reason: Annotated[str | None, Field(alias="cancelReason")] = None
    published_at: Annotated[AwareDatetime | None, Field(alias="publishedAt")] = None
    favorite_count: Annotated[int, Field(alias="favoriteCount", ge=0)]
    source: EventSource
    source_url: Annotated[
        str | None, Field(alias="sourceUrl", description="Page an AI find came from (R10).")
    ] = None
    found_at: Annotated[AwareDatetime | None, Field(alias="foundAt")] = None
    ai_job_id: Annotated[UUID | None, Field(alias="aiJobId")] = None
    version: Annotated[int, Field(ge=1)]
    images: Annotated[
        list[ModImage],
        Field(description="All images in order, including processing and failed ones (R08)."),
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
