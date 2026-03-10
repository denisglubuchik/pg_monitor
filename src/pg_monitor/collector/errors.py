from __future__ import annotations


class CollectorError(RuntimeError):
    """Base class for collector-related errors."""


class CollectorConnectionError(CollectorError):
    """Raised when collector cannot connect to PostgreSQL."""


class CollectorQueryError(CollectorError):
    """Raised when SQL execution for collector fails."""


class CollectorPrerequisiteError(CollectorError):
    """Raised when required PostgreSQL prerequisites are not satisfied."""
