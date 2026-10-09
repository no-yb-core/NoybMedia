"""Offline tests for the Wistia provider.

All HTTP interactions go through ``httpx.MockTransport``; no test here
touches the network.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import httpx
import pytest

from noybmedia.domain.media import MediaFormat, MediaMetadata
from noybmedia.exceptions import (
    MediaNotFoundError,
    ProviderError,
    ProviderResponseError,
    ValidationError,
)
from noybmedia.providers.wistia import WistiaProvider

MEDIA_ID = "abc123def4"

Handler = Callable[[httpx.Request], Coroutine[Any, Any, httpx.Response]]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _make_client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _ok_payload() -> dict[str, object]:
    return {
        "media": {
            "name": "Demo Video",
            "duration": 123.4,
            "description": "A short demo.",
            "assets": [
                {
                    "url": "https://embed-ssl.wistia.com/deliveries/hi.mp4",
                    "width": 1920,
                    "height": 1080,
                    "bitrate": 4500,
                    "ext": "mp4",
                    "size": 12_345_678,
                },
                {
                    "url": "https://embed-ssl.wistia.com/deliveries/lo.mp4",
                    "width": 640,
                    "height": 360,
                    "bitrate": 800,
                    "ext": "mp4",
                    "size": 1_234_567,
                },
            ],
        }
    }


@pytest.mark.anyio
async def test_fetch_metadata_returns_parsed_metadata() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_payload())

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        metadata = await provider.fetch_metadata(MEDIA_ID)

    assert isinstance(metadata, MediaMetadata)
    assert metadata.media_id == MEDIA_ID
    assert metadata.name == "Demo Video"
    assert metadata.duration_seconds == pytest.approx(123.4)
    assert metadata.description == "A short demo."
    assert len(metadata.formats) == 2

    hi = next(f for f in metadata.formats if f.height == 1080)
    assert hi == MediaFormat(
        url="https://embed-ssl.wistia.com/deliveries/hi.mp4",
        width=1920,
        height=1080,
        bitrate_kbps=4500,
        container="mp4",
        size_bytes=12_345_678,
    )

    assert metadata.formats_by_quality()[0].height == 1080


@pytest.mark.anyio
async def test_fetch_metadata_requests_expected_url() -> None:
    seen: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=_ok_payload())

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        await provider.fetch_metadata(MEDIA_ID)

    assert seen["url"] == f"https://fast.wistia.com/embed/medias/{MEDIA_ID}.json"


@pytest.mark.anyio
async def test_custom_base_url_is_used() -> None:
    seen: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json=_ok_payload())

    async with _make_client(handler) as client:
        provider = WistiaProvider(client, base_url="https://example.test/")
        await provider.fetch_metadata(MEDIA_ID)

    assert seen["url"] == f"https://example.test/embed/medias/{MEDIA_ID}.json"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "media_id",
    [
        "",
        "   ",
        "abc",
        "abc123def",
        "abc123def45",
        "ABC123DEF4",
        "abc123def!",
        "abc 123def4",
    ],
)
async def test_invalid_media_id_raises_validation_error(media_id: str) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP call should not be made for invalid IDs.")

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ValidationError):
            await provider.fetch_metadata(media_id)


@pytest.mark.anyio
async def test_leading_and_trailing_whitespace_in_media_id_is_ignored() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ok_payload())

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        metadata = await provider.fetch_metadata(f"  {MEDIA_ID}  ")

    assert metadata.media_id == MEDIA_ID


@pytest.mark.anyio
async def test_empty_base_url_is_rejected() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with _make_client(handler) as client:
        with pytest.raises(ValidationError):
            WistiaProvider(client, base_url="   ")


@pytest.mark.anyio
async def test_404_raises_media_not_found() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(MediaNotFoundError):
            await provider.fetch_metadata(MEDIA_ID)


@pytest.mark.anyio
@pytest.mark.parametrize("status", [401, 403])
async def test_access_denied_raises_provider_error(status: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "denied"})

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ProviderError) as excinfo:
            await provider.fetch_metadata(MEDIA_ID)

    assert "access" in str(excinfo.value).lower()


@pytest.mark.anyio
@pytest.mark.parametrize("status", [400, 429])
async def test_other_4xx_raises_provider_error(status: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ProviderError):
            await provider.fetch_metadata(MEDIA_ID)


@pytest.mark.anyio
@pytest.mark.parametrize("status", [500, 502, 503])
async def test_5xx_raises_provider_error(status: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ProviderError):
            await provider.fetch_metadata(MEDIA_ID)


@pytest.mark.anyio
async def test_timeout_raises_provider_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ProviderError):
            await provider.fetch_metadata(MEDIA_ID)


@pytest.mark.anyio
async def test_connect_error_raises_provider_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ProviderError):
            await provider.fetch_metadata(MEDIA_ID)


@pytest.mark.anyio
async def test_non_json_response_raises_response_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ProviderResponseError):
            await provider.fetch_metadata(MEDIA_ID)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "payload",
    [
        ["not", "an", "object"],
        "a string",
        42,
        None,
        {},
        {"media": "not an object"},
        {"media": {}},
        {"media": {"name": ""}},
        {"media": {"name": "   "}},
        {"media": {"name": 123}},
    ],
)
async def test_malformed_payload_raises_response_error(payload: object) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        with pytest.raises(ProviderResponseError):
            await provider.fetch_metadata(MEDIA_ID)


@pytest.mark.anyio
async def test_missing_assets_yields_no_formats() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"media": {"name": "Only name"}})

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        metadata = await provider.fetch_metadata(MEDIA_ID)

    assert metadata.name == "Only name"
    assert metadata.formats == ()
    assert metadata.has_formats is False
    assert metadata.duration_seconds is None


@pytest.mark.anyio
async def test_malformed_assets_are_skipped() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "media": {
                    "name": "Mixed",
                    "assets": [
                        "not a dict",
                        {},
                        {"url": ""},
                        {"url": "   "},
                        {"url": 42},
                        {
                            "url": "https://cdn.example.test/ok.mp4",
                            "width": 0,
                            "height": "1080",
                            "bitrate": -100,
                            "ext": "  MP4  ",
                            "size": -1,
                        },
                    ],
                }
            },
        )

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        metadata = await provider.fetch_metadata(MEDIA_ID)

    assert len(metadata.formats) == 1
    fmt = metadata.formats[0]
    assert fmt.url == "https://cdn.example.test/ok.mp4"
    assert fmt.width is None
    assert fmt.height is None
    assert fmt.bitrate_kbps is None
    assert fmt.container == "mp4"
    assert fmt.size_bytes is None


@pytest.mark.anyio
async def test_unknown_fields_are_ignored() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "media": {
                    "name": "Extra fields",
                    "unknown_top": "ignored",
                    "assets": [
                        {
                            "url": "https://cdn.example.test/v.mp4",
                            "extra": {"nested": True},
                        }
                    ],
                },
                "unrelated": "ignored",
            },
        )

    async with _make_client(handler) as client:
        provider = WistiaProvider(client)
        metadata = await provider.fetch_metadata(MEDIA_ID)

    assert metadata.name == "Extra fields"
    assert len(metadata.formats) == 1
