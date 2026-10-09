"""Application-specific exception types for NoybMedia."""

from __future__ import annotations


class NoybMediaError(Exception):
    """Base class for all NoybMedia errors."""


class ValidationError(NoybMediaError, ValueError):
    """Raised when user input or domain data fails validation."""


class InvalidWistiaUrlError(ValidationError):
    """Raised when a value is not a supported Wistia URL or media identifier."""
