"""Wistia provider: fetch and parse media metadata over HTTP.

This module owns Wistia-specific I/O. URL parsing lives in
:mod:`noybmedia.providers.url_parser` and stays pure. This module performs
network requests only through an injected ``httpx.AsyncClient`` so tests can
swap in ``httpx.MockTransport`` without touching the network.

Scope
-----
- Retrieve metadata for a single, already-validated media identifier.
- Parse the documented Wistia embed JSON payload into :class:`MediaMetadata`.

Out of scope
------------
- Downloading media bytes.
- Quality selection.
- Authentication, cookies, DRM, or access-control bypass.
- Retries, caching, or rate limiting.
"""

from __future__ import annotations

import re
from typing import Final, cast

import httpx

from noybmedia.domain.media import MediaFormat, MediaMetadata
from noybmedia.exceptions import (
    MediaNotFoundError,
    ProviderError,
    ProviderResponseError,
    ValidationError,
)

__all__ = ["WistiaProvider"]

_MEDIA_ID_RE: Final = re.compile(r"^[a-z0-9]{10}$")
_DEFAULT_BASE_URL: Final = "https://fast.wistia.com"


class WistiaProvider:
    """Fetch Wistia media metadata using an injected HTTP client."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str = _DEFAULT_BASE_URL,
    ) -> None:
        if not base_url.strip():
            raise ValidationError("WistiaProvider.base_url must not be empty.")
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def fetch_metadata(self, media_id: str) -> MediaMetadata:
        """Return metadata for *media_id*.

        ``media_id`` must match the documented identifier format. Raises
        :class:`ValidationError` for malformed identifiers,
        :class:`MediaNotFoundError` for 404 responses, and
        :class:`ProviderError` / :class:`ProviderResponseError` for transport
        or payload failures. Never raises ``httpx`` exceptions to callers.
        """

        normalized = media_id.strip()
        if not _MEDIA_ID_RE.fullmatch(normalized):
            raise ValidationError(f"Invalid Wistia media identifier: {media_id!r}")

        url = f"{self._base_url}/embed/medias/{normalized}.json"

        try:
            response = await self._client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                f"Timed out requesting metadata for media {normalized!r}."
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                f"HTTP error requesting metadata for media {normalized!r}: {exc}"
            ) from exc

        self._raise_for_status(response, normalized)

        try:
            payload: object = response.json()
        except ValueError as exc:
            raise ProviderResponseError("Wistia response was not valid JSON.") from exc

        return _parse_metadata_payload(normalized, payload)

    @staticmethod
    def _raise_for_status(response: httpx.Response, media_id: str) -> None:
        status = response.status_code
        if 200 <= status < 300:
            return
        if status == 404:
            raise MediaNotFoundError(
                f"Wistia media {media_id!r} was not found (HTTP 404)."
            )
        if status in (401, 403):
            raise ProviderError(
                f"Access denied for Wistia media {media_id!r} (HTTP {status})."
            )
        if 400 <= status < 500:
            raise ProviderError(
                f"Wistia rejected the request for media {media_id!r} (HTTP {status})."
            )
        raise ProviderError(f"Wistia returned HTTP {status} for media {media_id!r}.")


def _as_object_dict(value: object) -> dict[str, object] | None:
    """Return ``value`` as a JSON object mapping, or ``None``."""
    if isinstance(value, dict):
        return cast("dict[str, object]", value)
    return None


def _as_object_list(value: object) -> list[object] | None:
    """Return ``value`` as a JSON array, or ``None``."""
    if isinstance(value, list):
        return cast("list[object]", value)
    return None


def _parse_metadata_payload(media_id: str, payload: object) -> MediaMetadata:
    """Parse a Wistia embed JSON payload into :class:`MediaMetadata`.

    Pure function; no I/O. Only fields actually present and well-typed are
    populated. Individual malformed assets are skipped rather than failing
    the whole response.
    """

    root = _as_object_dict(payload)
    if root is None:
        raise ProviderResponseError("Wistia response root must be a JSON object.")

    media = _as_object_dict(root.get("media"))
    if media is None:
        raise ProviderResponseError("Wistia response is missing the 'media' object.")

    name = media.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ProviderResponseError("Wistia media is missing a valid 'name'.")

    duration_seconds = _coerce_float(media.get("duration"))

    raw_description = media.get("description")
    description = (
        raw_description
        if isinstance(raw_description, str) and raw_description.strip()
        else None
    )

    formats: list[MediaFormat] = []
    raw_assets = _as_object_list(media.get("assets"))
    if raw_assets is not None:
        for asset in raw_assets:
            parsed = _parse_asset(asset)
            if parsed is not None:
                formats.append(parsed)

    return MediaMetadata(
        media_id=media_id,
        name=name,
        duration_seconds=duration_seconds,
        description=description,
        formats=tuple(formats),
    )


def _parse_asset(asset: object) -> MediaFormat | None:
    """Return a :class:`MediaFormat` for *asset*, or ``None`` if unusable."""

    data = _as_object_dict(asset)
    if data is None:
        return None

    url = data.get("url")
    if not isinstance(url, str) or not url.strip():
        return None

    container = _coerce_non_empty_str(data.get("ext"))

    try:
        return MediaFormat(
            url=url,
            width=_coerce_positive_int(data.get("width")),
            height=_coerce_positive_int(data.get("height")),
            bitrate_kbps=_coerce_positive_int(data.get("bitrate")),
            container=container,
            size_bytes=_coerce_non_negative_int(data.get("size")),
        )
    except ValidationError:
        return None


def _coerce_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0 and value.is_integer():
        return int(value)
    return None


def _coerce_non_negative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


def _coerce_non_empty_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
