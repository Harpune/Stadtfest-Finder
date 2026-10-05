"""Application errors. Inbound adapters map them to protocol-specific responses."""

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for expected, user-facing errors."""

    code = "application_error"


class NotFoundError(ApplicationError):
    """The resource does not exist or is not visible to the caller."""

    code = "not_found"


class InvalidInputError(ApplicationError):
    """Input is syntactically valid but semantically wrong."""

    code = "validation_failed"

    def __init__(self, fields: dict[str, str], code: str = "validation_failed") -> None:
        """Create the error.

        Args:
            fields: Field name -> machine-readable problem.
            code: Error code, e.g. `region_mismatch`.
        """
        super().__init__(", ".join(fields))
        self.fields = fields
        self.code = code


class ForbiddenError(ApplicationError):
    """The caller is authenticated but lacks the role (e.g. `moderator`)."""

    code = "forbidden"


class ConflictError(ApplicationError):
    """The request conflicts with the current state (`version_conflict`, `invalid_transition`)."""

    def __init__(self, code: str, fields: dict[str, str] | None = None) -> None:
        """Create the error.

        Args:
            code: Machine-readable error code.
            fields: Optional details, e.g. the running job's ID.
        """
        super().__init__(code)
        self.code = code
        self.fields = fields


class TooManyRequestsError(ApplicationError):
    """A per-user limit is reached (e.g. the daily AI search limit)."""

    def __init__(self, code: str) -> None:
        """Create the error.

        Args:
            code: Machine-readable error code, e.g. `daily_limit`.
        """
        super().__init__(code)
        self.code = code


class ServiceUnavailableError(ApplicationError):
    """A required external service is unavailable."""

    def __init__(self, code: str) -> None:
        """Create the error.

        Args:
            code: Machine-readable error code, e.g. `geocoding_unavailable`.
        """
        super().__init__(code)
        self.code = code
