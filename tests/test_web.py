"""Web-layer tests using FastAPI's TestClient and a mocked HTTP transport."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from noybmedia.web.app import app, get_client

Handler = Callable[[httpx.Request], Coroutine[Any, Any, httpx.Response]]

MEDIA_ID = "abc123def4"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def install_handler() -> Iterator[Callable[[Handler], None]]:
    def _install(handler: Handler) -> None:
        async def override() -> AsyncIterator[httpx.AsyncClient]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ) as http_client:
                yield http_client

        app.dependency_overrides[get_client] = override

    yield _install
    app.dependency_overrides.clear()


def _metadata_payload(
    *,
    name: str = "Demo Video",
    assets: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if assets is None:
        assets = [
            {
                "url": "https://embed-ssl.wistia.com/deliveries/mid.mp4",
                "width": 1280,
                "height": 720,
                "ext": "mp4",
                "size": 1_000_000,
            },
            {
                "url": "https://embed-ssl.wistia.com/deliveries/hi.mp4",
                "width": 1920,
                "height": 1080,
                "ext": "mp4",
                "size": 3_000_000,
            },
        ]
    return {"media": {"name": name, "assets": assets}}


# --- /health --------------------------------------------------------------


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- /api/metadata happy paths -------------------------------------------


def test_metadata_endpoint_returns_metadata_for_raw_id(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_metadata_payload())

    install_handler(handler)

    response = client.post("/api/metadata", json={"url": MEDIA_ID})

    assert response.status_code == 200
    body = response.json()
    assert body["media_id"] == MEDIA_ID
    assert body["name"] == "Demo Video"
    assert len(body["formats"]) == 2
    # Highest quality first
    assert body["formats"][0]["height"] == 1080
    assert body["formats"][1]["height"] == 720


def test_metadata_endpoint_accepts_full_wistia_url(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_metadata_payload())

    install_handler(handler)

    response = client.post(
        "/api/metadata",
        json={"url": f"https://home.wistia.com/medias/{MEDIA_ID}"},
    )

    assert response.status_code == 200
    assert response.json()["media_id"] == MEDIA_ID


def test_metadata_endpoint_accepts_embed_url(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_metadata_payload())

    install_handler(handler)

    response = client.post(
        "/api/metadata",
        json={"url": f"https://fast.wistia.net/embed/iframe/{MEDIA_ID}"},
    )

    assert response.status_code == 200
    assert response.json()["media_id"] == MEDIA_ID


def test_metadata_endpoint_includes_all_format_fields(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_metadata_payload())

    install_handler(handler)

    response = client.post("/api/metadata", json={"url": MEDIA_ID})
    formats = response.json()["formats"]

    assert formats[0] == {
        "url": "https://embed-ssl.wistia.com/deliveries/hi.mp4",
        "width": 1920,
        "height": 1080,
        "bitrate_kbps": None,
        "container": "mp4",
        "size_bytes": 3_000_000,
    }


# --- /api/metadata error paths -------------------------------------------


@pytest.mark.parametrize(
    "bad_url",
    ["", "   ", "not a url", "https://example.com/medias/abc123def4"],
)
def test_metadata_endpoint_returns_400_for_invalid_url(
    client: TestClient,
    install_handler: Callable[[Handler], None],
    bad_url: str,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call for invalid input")

    install_handler(handler)

    response = client.post("/api/metadata", json={"url": bad_url})

    assert response.status_code == 400
    assert "detail" in response.json()


def test_metadata_endpoint_returns_422_for_missing_body_field(
    client: TestClient,
) -> None:
    response = client.post("/api/metadata", json={})
    assert response.status_code == 422


def test_metadata_endpoint_returns_422_for_non_string_url(
    client: TestClient,
) -> None:
    response = client.post("/api/metadata", json={"url": 123})
    assert response.status_code == 422


def test_metadata_endpoint_returns_404_when_media_missing(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    install_handler(handler)

    response = client.post("/api/metadata", json={"url": MEDIA_ID})

    assert response.status_code == 404
    assert "detail" in response.json()


def test_metadata_endpoint_returns_502_on_provider_5xx(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    install_handler(handler)

    response = client.post("/api/metadata", json={"url": MEDIA_ID})

    assert response.status_code == 502


def test_metadata_endpoint_returns_502_on_malformed_payload(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    install_handler(handler)

    response = client.post("/api/metadata", json={"url": MEDIA_ID})

    assert response.status_code == 502


def test_metadata_endpoint_returns_502_on_transport_error(
    client: TestClient,
    install_handler: Callable[[Handler], None],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    install_handler(handler)

    response = client.post("/api/metadata", json={"url": MEDIA_ID})

    assert response.status_code == 502
