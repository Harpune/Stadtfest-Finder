"""Notification settings of a user (R11-US2).

Settings only decide whether a push is sent; every notification is listed regardless
("Stumm geschaltete Arten erscheinen weiterhin in der Liste").
"""

from __future__ import annotations

from dataclasses import dataclass

from stadtfest.domain.events.geo import GeoPoint
from stadtfest.domain.notifications.notification import NotificationType

REMIND_DAYS = frozenset({1, 3, 7})
NEAR_RADIUS_MIN_KM = 5
NEAR_RADIUS_MAX_KM = 150
NEAR_RADIUS_STEP_KM = 5
PLACE_NAME_MAX = 100


class InvalidSettingsError(ValueError):
    """Settings out of range; `fields` maps API field names to the problem."""

    def __init__(self, fields: dict[str, str]) -> None:
        """Create the error."""
        super().__init__(", ".join(fields))
        self.fields = fields


@dataclass(frozen=True, slots=True)
class Home:
    """Home for "new near your home": ZIP code, place name and ZIP code center (E-10).

    Never an exact GPS position.
    """

    postal_code: str
    place_name: str
    location: GeoPoint


@dataclass(frozen=True, slots=True)
class NotificationSettings:
    """Which types are pushed. The defaults apply until the user changes something."""

    remind: bool = True
    remind_days_before: int = 1
    near: bool = True
    home: Home | None = None
    near_radius_km: int = 25
    change: bool = True
    invite: bool = True
    rsvp: bool = True

    def __post_init__(self) -> None:
        """Validate the ranges.

        Raises:
            InvalidSettingsError: With the API field names of all invalid values.
        """
        problems: dict[str, str] = {}
        if self.remind_days_before not in REMIND_DAYS:
            problems["remindDaysBefore"] = "invalid"
        radius = self.near_radius_km
        if not NEAR_RADIUS_MIN_KM <= radius <= NEAR_RADIUS_MAX_KM or radius % NEAR_RADIUS_STEP_KM:
            problems["nearRadiusKm"] = "invalid"
        if self.home is not None and not 0 < len(self.home.place_name) <= PLACE_NAME_MAX:
            problems["home.placeName"] = "invalid"
        if problems:
            raise InvalidSettingsError(problems)

    def pushes(self, notification_type: NotificationType) -> bool:
        """Whether a notification of this type is also sent as push."""
        match notification_type:
            case NotificationType.REMIND:
                return self.remind
            case NotificationType.NEAR:
                return self.near and self.home is not None
            case NotificationType.CHANGE | NotificationType.CANCEL:
                return self.change
            case NotificationType.FRIEND_ADDED:
                return False  # list only (R12-US2)
