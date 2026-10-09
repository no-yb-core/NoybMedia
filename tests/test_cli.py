"""CLI tests using Typer's CliRunner with a mocked HTTP transport."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

import noybmedia.cli as cli_module
from noybmedia.cli import app
from noybmedia.services.downloader import safe_filename

Handler = Callable[[httpx.Request], Coroutine[Any, Any, httpx.Response]]

MEDIA_ID = "abc123def4"
PAYLOAD = b"streamed media bytes" * 64


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _install_client(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> None:
    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(cli_module, "_build_client", factory)


def _metadata_payload(
    *,
    name: str = "Demo Video",
    assets: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if assets is None:
        assets = [
            {
                "url": "https://embed-ssl.wistia.com/deliveries/hi.mp4",
                "width": 1920,
                "height": 1080,
                "ext": "mp4",
            },
            {
                "url": "https://embed-ssl.wistia.com/deliveries/mid.mp4",
                "width": 1280,
                "height": 720,
                "ext": "mp4",
            },
            {
                "url": "https://embed-ssl.wistia.com/deliveries/lo.mp4",
                "width": 640,
                "height": 360,
                "ext": "mp4",
            },
        ]
    return {"media": {"name": name, "assets": assets}}


def _make_handler(
    payload: dict[str, object],
    *,
    metadata_status: int = 200,
    cdn_status: int = 200,
    cdn_body: bytes = PAYLOAD,
) -> Handler:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(".json"):
            return httpx.Response(metadata_status, json=payload)
        return httpx.Response(cdn_status, content=cdn_body)

    return handler


# --- version --------------------------------------------------------------


def test_version_prints_package_version(runner: CliRunner) -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


# --- happy path -----------------------------------------------------------


def test_download_writes_file_to_output_directory(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_client(monkeypatch, _make_handler(_metadata_payload()))

    out_dir = tmp_path / "downloads"
    result = runner.invoke(app, ["download", MEDIA_ID, "--output", str(out_dir)])

    assert result.exit_code == 0, result.stdout
    files = list(out_dir.iterdir())
    assert len(files) == 1
    target = files[0]
    assert target.name == "Demo_Video.mp4"
    assert target.read_bytes() == PAYLOAD
    assert "Downloaded" in result.stdout


def test_download_picks_highest_quality_by_default(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if request.url.path.endswith(".json"):
            return httpx.Response(200, json=_metadata_payload())
        return httpx.Response(200, content=PAYLOAD)

    _install_client(monkeypatch, handler)

    result = runner.invoke(app, ["download", MEDIA_ID, "-o", str(tmp_path)])

    assert result.exit_code == 0, result.stdout
    download_urls = [u for u in seen_urls if not u.endswith(".json")]
    assert download_urls == ["https://embed-ssl.wistia.com/deliveries/hi.mp4"]


def test_download_accepts_full_wistia_url(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_client(monkeypatch, _make_handler(_metadata_payload()))

    result = runner.invoke(
        app,
        [
            "download",
            f"https://home.wistia.com/medias/{MEDIA_ID}",
            "-o",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "Demo_Video.mp4").exists()


# --- quality selection ----------------------------------------------------


def test_quality_flag_selects_format_at_or_below_requested_height(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if request.url.path.endswith(".json"):
            return httpx.Response(200, json=_metadata_payload())
        return httpx.Response(200, content=PAYLOAD)

    _install_client(monkeypatch, handler)

    result = runner.invoke(
        app,
        ["download", MEDIA_ID, "-o", str(tmp_path), "--quality", "720"],
    )

    assert result.exit_code == 0, result.stdout
    download_urls = [u for u in seen_urls if not u.endswith(".json")]
    assert download_urls == ["https://embed-ssl.wistia.com/deliveries/mid.mp4"]


def test_quality_flag_falls_back_to_nearest_below(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if request.url.path.endswith(".json"):
            return httpx.Response(200, json=_metadata_payload())
        return httpx.Response(200, content=PAYLOAD)

    _install_client(monkeypatch, handler)

    result = runner.invoke(
        app,
        ["download", MEDIA_ID, "-o", str(tmp_path), "--quality", "800"],
    )

    assert result.exit_code == 0, result.stdout
    download_urls = [u for u in seen_urls if not u.endswith(".json")]
    assert download_urls == ["https://embed-ssl.wistia.com/deliveries/mid.mp4"]


def test_quality_flag_with_no_lower_format_exits_with_error(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_client(monkeypatch, _make_handler(_metadata_payload()))

    result = runner.invoke(
        app,
        ["download", MEDIA_ID, "-o", str(tmp_path), "--quality", "240"],
    )

    assert result.exit_code == 1
    assert "240p" in result.stderr


def test_metadata_with_no_formats_exits_with_error(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_client(
        monkeypatch,
        _make_handler(_metadata_payload(assets=[])),
    )

    result = runner.invoke(app, ["download", MEDIA_ID, "-o", str(tmp_path)])

    assert result.exit_code == 1
    assert "no downloadable formats" in result.stderr.lower()


# --- overwrite behavior ---------------------------------------------------


def test_existing_file_without_overwrite_exits_with_error(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = tmp_path / "Demo_Video.mp4"
    existing.write_bytes(b"old contents")

    _install_client(monkeypatch, _make_handler(_metadata_payload()))

    result = runner.invoke(app, ["download", MEDIA_ID, "-o", str(tmp_path)])

    assert result.exit_code == 1
    assert existing.read_bytes() == b"old contents"


def test_overwrite_flag_replaces_existing_file(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    existing = tmp_path / "Demo_Video.mp4"
    existing.write_bytes(b"old contents")

    _install_client(monkeypatch, _make_handler(_metadata_payload()))

    result = runner.invoke(
        app,
        ["download", MEDIA_ID, "-o", str(tmp_path), "--overwrite"],
    )

    assert result.exit_code == 0, result.stdout
    assert existing.read_bytes() == PAYLOAD


# --- error paths ----------------------------------------------------------


@pytest.mark.parametrize(
    "bad_input",
    ["", "   ", "not a url", "https://example.com/medias/abc123def4"],
)
def test_invalid_url_exits_with_code_2(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_input: str,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call should be made for invalid input")

    _install_client(monkeypatch, handler)

    result = runner.invoke(app, ["download", bad_input, "-o", str(tmp_path)])

    assert result.exit_code == 2


def test_media_not_found_exits_with_code_1(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_client(
        monkeypatch, _make_handler(_metadata_payload(), metadata_status=404)
    )

    result = runner.invoke(app, ["download", MEDIA_ID, "-o", str(tmp_path)])

    assert result.exit_code == 1
    assert not any(tmp_path.iterdir())


# --- safe_filename unit tests (live with the CLI-adjacent behavior) -------


@pytest.mark.parametrize(
    ("name", "extension", "expected"),
    [
        ("Demo Video", "mp4", "Demo_Video.mp4"),
        ("Demo   Video", "MP4", "Demo_Video.mp4"),
        ("hello/world", "mp4", "hello_world.mp4"),
        ("../../etc/passwd", "", "etc_passwd"),
        ("", "mp4", "media.mp4"),
        ("   ", "mp4", "media.mp4"),
        ("!!!", "mp4", "media.mp4"),
        ("name", "", "name"),
        ("name", ".mp4", "name.mp4"),
    ],
)
def test_safe_filename(name: str, extension: str, expected: str) -> None:
    assert safe_filename(name, extension) == expected
