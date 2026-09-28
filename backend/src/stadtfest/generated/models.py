# Generated from api/openapi.yaml by `make gen` - DO NOT EDIT.

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


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
