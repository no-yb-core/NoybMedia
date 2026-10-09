"""FastAPI application exposing NoybMedia over HTTP.

Endpoints
---------
- ``GET /health``         liveness check
- ``POST /api/metadata``  parse a Wistia URL/ID and return metadata

The app delegates to the parser and provider modules; it does not
reimplement their logic. HTTP clients are provided via FastAPI dependency
injection so tests can substitute a mock transport.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel

from noybmedia.domain.media import MediaFormat, MediaMetadata
from noybmedia.exceptions import (
    MediaNotFoundError,
    ProviderError,
    ProviderResponseError,
    ValidationError,
)
from noybmedia.providers.url_parser import parse_wistia_url
from noybmedia.providers.wistia import WistiaProvider

app = FastAPI(
    title="NoybMedia",
    description=(
        "Fetch metadata for Wistia media that you own or are otherwise "
        "authorized to access."
    ),
    version="0.1.0",
)


class MetadataRequest(BaseModel):
    """Request body for ``POST /api/metadata``."""

    url: str


class FormatOut(BaseModel):
    """A single downloadable representation exposed over HTTP."""

    url: str
    width: int | None = None
    height: int | None = None
    bitrate_kbps: int | None = None
    container: str | None = None
    size_bytes: int | None = None


class MetadataOut(BaseModel):
    """Response body for ``POST /api/metadata``."""

    media_id: str
    name: str
    duration_seconds: float | None = None
    description: str | None = None
    formats: list[FormatOut]


async def get_client() -> AsyncIterator[httpx.AsyncClient]:
    """Yield an HTTP client for the duration of a request.

    Tests override this dependency with a mock-transport client.
    """
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        yield client


def get_provider(
    client: Annotated[httpx.AsyncClient, Depends(get_client)],
) -> WistiaProvider:
    """Return a Wistia provider bound to the request's HTTP client."""
    return WistiaProvider(client)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple liveness response."""
    return {"status": "ok"}


@app.post("/api/metadata", response_model=MetadataOut)
async def fetch_metadata(
    request: MetadataRequest,
    provider: Annotated[WistiaProvider, Depends(get_provider)],
) -> MetadataOut:
    """Resolve ``request.url`` and return the media's metadata."""

    try:
        media_id = parse_wistia_url(request.url)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    try:
        metadata = await provider.fetch_metadata(media_id)
    except MediaNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ProviderResponseError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return _to_metadata_out(metadata)


def _to_format_out(fmt: MediaFormat) -> FormatOut:
    return FormatOut(
        url=fmt.url,
        width=fmt.width,
        height=fmt.height,
        bitrate_kbps=fmt.bitrate_kbps,
        container=fmt.container,
        size_bytes=fmt.size_bytes,
    )


def _to_metadata_out(metadata: MediaMetadata) -> MetadataOut:
    return MetadataOut(
        media_id=metadata.media_id,
        name=metadata.name,
        duration_seconds=metadata.duration_seconds,
        description=metadata.description,
        formats=[_to_format_out(f) for f in metadata.formats_by_quality()],
    )
