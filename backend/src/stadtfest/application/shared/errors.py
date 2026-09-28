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

    def __init__(self, fields: dict[str, str]) -> None:
        """Create the error.

        Args:
            fields: Field name -> machine-readable problem.
        """
        super().__init__(", ".join(fields))
        self.fields = fields


class ServiceUnavailableError(ApplicationError):
    """A required external service is unavailable."""

    def __init__(self, code: str) -> None:
        """Create the error.

        Args:
            code: Machine-readable error code, e.g. `geocoding_unavailable`.
        """
        super().__init__(code)
        self.code = code
