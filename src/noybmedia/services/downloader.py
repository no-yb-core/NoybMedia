"""Stream media downloads to disk.

This service is provider-independent: it takes a URL and a destination
path, streams bytes over HTTP, and writes them atomically via a
``.part`` file. It knows nothing about Wistia, metadata, or quality
selection — the caller supplies a validated URL and target path.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx

from noybmedia.exceptions import DownloadError, ValidationError

__all__ = ["DownloadResult", "Downloader", "ProgressCallback"]

ProgressCallback = Callable[[int, int | None], None]
"""Called as ``progress(bytes_written, total_bytes_or_None)``."""

_DEFAULT_CHUNK_SIZE: Final = 64 * 1024
_PART_SUFFIX: Final = ".part"


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """Outcome of a successful download."""

    path: Path
    bytes_written: int


class Downloader:
    """Stream URLs to disk using an injected HTTP client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def download(
        self,
        url: str,
        destination: Path,
        *,
        overwrite: bool = False,
        progress: ProgressCallback | None = None,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
    ) -> DownloadResult:
        """Stream *url* to *destination*.

        Writes to ``<destination>.part`` first and atomically renames it on
        success. On any failure the partial file is removed and the
        destination is left untouched. Refuses to overwrite an existing
        destination unless ``overwrite=True``. Raises :class:`ValidationError`
        for empty URLs or non-positive ``chunk_size``, and
        :class:`DownloadError` for HTTP, transport, filesystem, or empty-body
        failures.
        """

        normalized_url = url.strip()
        if not normalized_url:
            raise ValidationError("Downloader.download url must not be empty.")
        if chunk_size <= 0:
            raise ValidationError("chunk_size must be a positive integer.")
        if destination.exists() and not overwrite:
            raise DownloadError(
                f"Destination already exists: {destination} "
                f"(pass overwrite=True to replace it)."
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        part_path = destination.with_name(destination.name + _PART_SUFFIX)

        written = 0
        try:
            async with self._client.stream("GET", normalized_url) as response:
                if response.status_code >= 400:
                    raise DownloadError(
                        f"Server returned HTTP {response.status_code} "
                        f"for {normalized_url!r}."
                    )

                total = _content_length(response)
                if progress is not None:
                    progress(0, total)

                with part_path.open("wb") as file:
                    async for chunk in response.aiter_bytes(chunk_size):
                        if not chunk:
                            continue
                        file.write(chunk)
                        written += len(chunk)
                        if progress is not None:
                            progress(written, total)

            if written == 0:
                raise DownloadError(
                    f"Server returned an empty response for {normalized_url!r}."
                )

            os.replace(part_path, destination)
        except httpx.HTTPError as exc:
            raise DownloadError(
                f"HTTP error downloading {normalized_url!r}: {exc}"
            ) from exc
        except OSError as exc:
            raise DownloadError(
                f"Filesystem error writing {destination!r}: {exc}"
            ) from exc
        finally:
            if part_path.exists():
                try:
                    part_path.unlink()
                except OSError:
                    pass

        return DownloadResult(path=destination, bytes_written=written)


def _content_length(response: httpx.Response) -> int | None:
    raw = response.headers.get("content-length")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


_UNSAFE_FILENAME_CHARS: Final = re.compile(r"[^\w\-. ]", flags=re.UNICODE)
_FILENAME_SEPARATORS: Final = re.compile(r"[_\s]+")
_MAX_FILENAME_BASE_LENGTH: Final = 100


def safe_filename(name: str, extension: str = "") -> str:
    """Return a filename derived from *name* that is safe on common filesystems.

    Replaces characters outside ``[A-Za-z0-9._- ]`` with ``_``, collapses runs
    of whitespace and underscores, trims leading/trailing separators and dots
    (so path traversal segments can't survive), and truncates the base to a
    reasonable length. Falls back to ``"media"`` when nothing usable remains.
    """
    base = _UNSAFE_FILENAME_CHARS.sub("_", name).strip()
    base = _FILENAME_SEPARATORS.sub("_", base).strip("_. ")
    base = base[:_MAX_FILENAME_BASE_LENGTH].rstrip("_. ") or "media"

    ext = extension.strip().lower().lstrip(".")
    return f"{base}.{ext}" if ext else base
