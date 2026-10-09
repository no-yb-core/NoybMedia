"""Offline tests for the download service.

All HTTP interactions go through ``httpx.MockTransport``; no test here
touches the network. Filesystem assertions use pytest's ``tmp_path``.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import httpx
import pytest

from noybmedia.exceptions import DownloadError, ValidationError
from noybmedia.services.downloader import Downloader, DownloadResult

Handler = Callable[[httpx.Request], Coroutine[Any, Any, httpx.Response]]

PAYLOAD = b"hello media bytes " * 100  # 1800 bytes


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _make_client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _unreachable(request: httpx.Request) -> httpx.Response:
    raise AssertionError("HTTP call should not have been made.")


@pytest.mark.anyio
async def test_successful_download_writes_file_and_returns_result(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "out.mp4"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=PAYLOAD)

    async with _make_client(handler) as client:
        result = await Downloader(client).download(
            "https://example.test/v.mp4", destination
        )

    assert isinstance(result, DownloadResult)
    assert result.path == destination
    assert result.bytes_written == len(PAYLOAD)
    assert destination.read_bytes() == PAYLOAD


@pytest.mark.anyio
async def test_missing_parent_directory_is_created(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "deeper" / "out.mp4"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=PAYLOAD)

    async with _make_client(handler) as client:
        result = await Downloader(client).download(
            "https://example.test/v.mp4", destination
        )

    assert result.path == destination
    assert destination.read_bytes() == PAYLOAD


@pytest.mark.anyio
async def test_no_part_file_left_after_success(tmp_path: Path) -> None:
    destination = tmp_path / "out.mp4"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=PAYLOAD)

    async with _make_client(handler) as client:
        await Downloader(client).download("https://example.test/v.mp4", destination)

    assert list(tmp_path.glob("*.part")) == []
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.anyio
async def test_existing_destination_without_overwrite_is_refused(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "out.mp4"
    destination.write_bytes(b"existing content")

    async with _make_client(_unreachable) as client:
        with pytest.raises(DownloadError):
            await Downloader(client).download("https://example.test/v.mp4", destination)

    assert destination.read_bytes() == b"existing content"


@pytest.mark.anyio
async def test_existing_destination_with_overwrite_replaces_file(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "out.mp4"
    destination.write_bytes(b"existing content")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=PAYLOAD)

    async with _make_client(handler) as client:
        result = await Downloader(client).download(
            "https://example.test/v.mp4", destination, overwrite=True
        )

    assert result.bytes_written == len(PAYLOAD)
    assert destination.read_bytes() == PAYLOAD


@pytest.mark.anyio
@pytest.mark.parametrize("status", [400, 403, 404, 500, 502])
async def test_error_status_raises_download_error(tmp_path: Path, status: int) -> None:
    destination = tmp_path / "out.mp4"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status)

    async with _make_client(handler) as client:
        with pytest.raises(DownloadError) as excinfo:
            await Downloader(client).download("https://example.test/v.mp4", destination)

    assert str(status) in str(excinfo.value)
    assert not destination.exists()
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.anyio
async def test_timeout_raises_download_error(tmp_path: Path) -> None:
    destination = tmp_path / "out.mp4"

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with _make_client(handler) as client:
        with pytest.raises(DownloadError):
            await Downloader(client).download("https://example.test/v.mp4", destination)

    assert not destination.exists()
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.anyio
async def test_connect_error_raises_download_error(tmp_path: Path) -> None:
    destination = tmp_path / "out.mp4"

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    async with _make_client(handler) as client:
        with pytest.raises(DownloadError):
            await Downloader(client).download("https://example.test/v.mp4", destination)

    assert not destination.exists()
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.anyio
async def test_empty_response_raises_and_leaves_no_file(tmp_path: Path) -> None:
    destination = tmp_path / "out.mp4"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with _make_client(handler) as client:
        with pytest.raises(DownloadError):
            await Downloader(client).download("https://example.test/v.mp4", destination)

    assert not destination.exists()
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.anyio
async def test_progress_reports_bytes_and_total(tmp_path: Path) -> None:
    destination = tmp_path / "out.mp4"
    events: list[tuple[int, int | None]] = []

    def on_progress(written: int, total: int | None) -> None:
        events.append((written, total))

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=PAYLOAD)

    async with _make_client(handler) as client:
        await Downloader(client).download(
            "https://example.test/v.mp4", destination, progress=on_progress
        )

    assert events[0] == (0, len(PAYLOAD))
    assert events[-1] == (len(PAYLOAD), len(PAYLOAD))
    assert all(a[0] <= b[0] for a, b in zip(events, events[1:], strict=False))


@pytest.mark.anyio
async def test_progress_total_is_none_without_content_length(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "out.mp4"
    events: list[tuple[int, int | None]] = []

    def on_progress(written: int, total: int | None) -> None:
        events.append((written, total))

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=httpx.ByteStream(b"payload"))

    async with _make_client(handler) as client:
        await Downloader(client).download(
            "https://example.test/v.mp4", destination, progress=on_progress
        )

    assert events, "progress should have been called at least once"
    assert events[0] == (0, None)


@pytest.mark.anyio
async def test_progress_callback_oserror_triggers_cleanup(tmp_path: Path) -> None:
    destination = tmp_path / "out.mp4"
    calls: list[int] = []

    def on_progress(written: int, total: int | None) -> None:
        calls.append(written)
        if len(calls) >= 2:
            raise OSError("simulated disk failure")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=PAYLOAD)

    async with _make_client(handler) as client:
        with pytest.raises(DownloadError):
            await Downloader(client).download(
                "https://example.test/v.mp4",
                destination,
                progress=on_progress,
            )

    assert not destination.exists()
    assert list(tmp_path.glob("*.part")) == []


@pytest.mark.anyio
@pytest.mark.parametrize("url", ["", "   ", "\t\n"])
async def test_empty_url_rejected(tmp_path: Path, url: str) -> None:
    async with _make_client(_unreachable) as client:
        with pytest.raises(ValidationError):
            await Downloader(client).download(url, tmp_path / "out.mp4")


@pytest.mark.anyio
@pytest.mark.parametrize("chunk_size", [0, -1, -1024])
async def test_invalid_chunk_size_rejected(tmp_path: Path, chunk_size: int) -> None:
    async with _make_client(_unreachable) as client:
        with pytest.raises(ValidationError):
            await Downloader(client).download(
                "https://example.test/v.mp4",
                tmp_path / "out.mp4",
                chunk_size=chunk_size,
            )


@pytest.mark.anyio
async def test_destination_is_not_created_when_url_is_invalid(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "out.mp4"

    async with _make_client(_unreachable) as client:
        with pytest.raises(ValidationError):
            await Downloader(client).download("", destination)

    assert not destination.exists()
