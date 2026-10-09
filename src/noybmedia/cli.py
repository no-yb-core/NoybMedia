"""Command-line interface for NoybMedia.

Wires the URL parser, Wistia provider, and download service behind Typer
commands. All HTTP access goes through :func:`_build_client`, which tests
monkeypatch to inject ``httpx.MockTransport``.
"""

from __future__ import annotations

from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Annotated

import anyio
import httpx
import typer

from noybmedia.domain.media import MediaFormat, MediaMetadata
from noybmedia.exceptions import DownloadError, NoybMediaError
from noybmedia.providers.url_parser import parse_wistia_url
from noybmedia.providers.wistia import WistiaProvider
from noybmedia.services.downloader import Downloader, DownloadResult, safe_filename

app = typer.Typer(
    name="noybmedia",
    help=("Download Wistia media that you own or are otherwise authorized to access."),
    no_args_is_help=True,
    add_completion=False,
)


def _build_client() -> httpx.AsyncClient:
    """Return the HTTP client used by CLI commands.

    Kept as a module-level function so tests can monkeypatch it with a
    mock transport. No CLI code constructs ``httpx.AsyncClient`` directly.
    """
    return httpx.AsyncClient(timeout=30.0, follow_redirects=True)


@app.command()
def version() -> None:
    """Print the installed NoybMedia version."""
    typer.echo(_pkg_version("noybmedia"))


@app.command()
def download(
    url: Annotated[
        str,
        typer.Argument(help="Wistia media URL, embed URL, or media identifier."),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Directory to write the downloaded file into.",
        ),
    ] = Path(),
    quality: Annotated[
        int | None,
        typer.Option(
            "--quality",
            "-q",
            help=(
                "Preferred height in pixels (e.g. 1080). Picks the highest "
                "available format at or below this height."
            ),
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Replace the destination file if it already exists.",
        ),
    ] = False,
) -> None:
    """Download a Wistia media file."""
    try:
        media_id = parse_wistia_url(url)
    except NoybMediaError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    try:
        result = anyio.run(_download_async, media_id, output, quality, overwrite)
    except NoybMediaError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Downloaded {result.path} ({result.bytes_written} bytes)")


async def _download_async(
    media_id: str,
    output: Path,
    preferred_height: int | None,
    overwrite: bool,
) -> DownloadResult:
    async with _build_client() as client:
        provider = WistiaProvider(client)
        metadata = await provider.fetch_metadata(media_id)
        chosen = _select_format(metadata, preferred_height)
        extension = chosen.container or _extension_from_url(chosen.url) or "bin"
        filename = safe_filename(metadata.name, extension)
        destination = output / filename
        downloader = Downloader(client)
        return await downloader.download(chosen.url, destination, overwrite=overwrite)


def _select_format(
    metadata: MediaMetadata, preferred_height: int | None
) -> MediaFormat:
    """Return the best available format for the requested height.

    With no preference, returns the highest-quality format. With a
    preference, returns the highest format at or below that height.
    Raises :class:`DownloadError` when no suitable format exists.
    """
    if not metadata.formats:
        raise DownloadError(f"Media {metadata.media_id!r} has no downloadable formats.")

    if preferred_height is None:
        return metadata.formats_by_quality()[0]

    at_or_below = [
        fmt
        for fmt in metadata.formats
        if fmt.height is not None and fmt.height <= preferred_height
    ]
    if not at_or_below:
        raise DownloadError(
            f"No format at or below {preferred_height}p is available for "
            f"media {metadata.media_id!r}."
        )
    return max(at_or_below, key=lambda fmt: fmt.height or 0)


def _extension_from_url(url: str) -> str | None:
    """Return a bare extension (no dot) from *url*'s path, if any."""
    path = httpx.URL(url).path
    if "." not in path:
        return None
    candidate = path.rsplit(".", 1)[-1].strip().lower()
    if not candidate or not candidate.isalnum():
        return None
    return candidate[:10]
