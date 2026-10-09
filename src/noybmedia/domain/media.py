"""Provider-independent media domain models.

These models describe *what* a media item is and *which* downloadable
formats a provider has reported. They perform no I/O and contain no
provider-specific logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from noybmedia.exceptions import ValidationError

__all__ = ["MediaFormat", "MediaMetadata"]


@dataclass(frozen=True, slots=True)
class MediaFormat:
    """A single downloadable representation of a media item.

    Only fields actually reported by the provider should be populated.
    Unknown values stay ``None`` rather than being guessed.
    """

    url: str
    width: int | None = None
    height: int | None = None
    bitrate_kbps: int | None = None
    container: str | None = None
    size_bytes: int | None = None

    def __post_init__(self) -> None:
        normalized_url = self.url.strip()
        if not normalized_url:
            raise ValidationError("MediaFormat.url must not be empty.")
        if normalized_url != self.url:
            object.__setattr__(self, "url", normalized_url)

        if self.width is not None and self.width <= 0:
            raise ValidationError("MediaFormat.width must be a positive integer.")
        if self.height is not None and self.height <= 0:
            raise ValidationError("MediaFormat.height must be a positive integer.")
        if self.bitrate_kbps is not None and self.bitrate_kbps <= 0:
            raise ValidationError(
                "MediaFormat.bitrate_kbps must be a positive integer."
            )
        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValidationError("MediaFormat.size_bytes must be non-negative.")
        if self.container is not None:
            normalized = self.container.strip().lower().lstrip(".")
            if not normalized:
                raise ValidationError("MediaFormat.container must not be blank.")
            object.__setattr__(self, "container", normalized)

    @property
    def resolution_label(self) -> str | None:
        """Return a human-readable resolution such as ``"1080p"``, if known."""
        if self.height is None:
            return None
        return f"{self.height}p"


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    """Metadata describing a media item and its available formats."""

    media_id: str
    name: str
    duration_seconds: float | None = None
    description: str | None = None
    formats: Sequence[MediaFormat] = ()

    def __post_init__(self) -> None:
        normalized_id = self.media_id.strip()
        if not normalized_id:
            raise ValidationError("MediaMetadata.media_id must not be empty.")
        if normalized_id != self.media_id:
            object.__setattr__(self, "media_id", normalized_id)

        normalized_name = self.name.strip()
        if not normalized_name:
            raise ValidationError("MediaMetadata.name must not be empty.")
        if normalized_name != self.name:
            object.__setattr__(self, "name", normalized_name)

        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValidationError(
                "MediaMetadata.duration_seconds must be non-negative."
            )
        if not isinstance(self.formats, tuple):
            object.__setattr__(self, "formats", tuple(self.formats))

    @property
    def has_formats(self) -> bool:
        """Return ``True`` if at least one downloadable format is available."""
        return len(self.formats) > 0

    def formats_by_quality(self) -> tuple[MediaFormat, ...]:
        """Return formats ordered from highest to lowest quality.

        Ordering is by resolution first, then width, then bitrate.
        Formats with no resolution information rank below those that have it.
        """
        return tuple(
            sorted(
                self.formats,
                key=lambda f: (f.height or 0, f.width or 0, f.bitrate_kbps or 0),
                reverse=True,
            )
        )
