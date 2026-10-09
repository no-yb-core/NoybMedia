# NoybMedia

[![Latest Release](https://img.shields.io/github/v/release/no-yb-core/NoybMedia)](https://github.com/no-yb-core/NoybMedia/releases/latest)
[![CI](https://github.com/no-yb-core/NoybMedia/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/no-yb-core/NoybMedia/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/no-yb-core/NoybMedia)](https://github.com/no-yb-core/NoybMedia/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB)](https://www.python.org/downloads/)

Download Wistia-hosted videos that **you own or are otherwise authorized
to access**, from the command line or through a small HTTP API.

NoybMedia is built as a provider-aware downloader: URL parsing, provider
metadata retrieval, and byte streaming are separated into distinct,
independently tested modules.

> **Responsible use.** NoybMedia is intended for media you own or have
> permission to download. It does not bypass authentication, DRM, or
> access controls, and it does not attempt to work around Wistia's
> permissions or terms. Respect applicable laws and platform terms.

## Status

| Area | State |
|---|---|
| Wistia URL parser | ✅ Implemented, tested |
| Provider-independent domain models | ✅ Implemented, tested |
| Wistia metadata provider | ✅ Implemented, tested |
| Streaming download service | ✅ Implemented, tested |
| CLI (`noybmedia download`) | ✅ Implemented, tested |
| FastAPI metadata endpoint | ✅ Implemented, tested |
| FastAPI download endpoint | ❌ Planned |
| Interactive web UI | ❌ Planned |
| Deployment / hosting | ❌ Planned |

## Supported inputs

The parser accepts only explicitly supported Wistia URLs and identifiers:

- `https://<account>.wistia.com/medias/<id>`
- `https://wistia.com/medias/<id>`
- `https://wistia.net/medias/<id>`
- `https://fast.wistia.com/embed/iframe/<id>`
- `https://fast.wistia.net/embed/iframe/<id>`
- `https://fast.wistia.com/embed/medias/<id>`
- `https://fast.wistia.net/embed/medias/<id>`
- A raw media identifier: exactly 10 lowercase alphanumeric characters (`[a-z0-9]{10}`).

Leading and trailing whitespace is ignored. Query strings and fragments
are ignored once the URL structure is recognized. Unrelated domains,
look-alike hosts (e.g. `wistia.example.com`, `wistia.com.example.org`),
and undocumented paths are rejected.

## Installation

### Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

### From source

Clone the repository and install the project dependencies:

```bash
git clone https://github.com/no-yb-core/noybmedia.git
cd noybmedia
uv sync
```

Verify that the project environment is ready:

```bash
uv run noybmedia --help
```

This displays the available CLI commands and their options.

## Usage

### Check the installed version

```bash
uv run noybmedia version
```

### Download a Wistia video

Provide a supported Wistia media URL, embed URL, or media identifier:

```bash
uv run noybmedia download "https://example.wistia.com/medias/abc123def4"
```

The file is downloaded to the current directory by default.

The example URL is a placeholder, not a guaranteed real media resource.

### Choose an output directory

Use `--output` or `-o` to specify where the downloaded file should be saved:

```bash
uv run noybmedia download "https://example.wistia.com/medias/abc123def4" \
  --output ./downloads
```

### Set a preferred video quality

Use `--quality` or `-q` to specify a preferred video height in pixels. NoybMedia selects the highest available format at or below the requested height.

```bash
uv run noybmedia download "https://example.wistia.com/medias/abc123def4" \
  --quality 1080
```

### Allow overwriting existing files

By default, existing destination files are not overwritten. Use `--overwrite` to allow replacement:

```bash
uv run noybmedia download "https://example.wistia.com/medias/abc123def4" \
  --output ./downloads \
  --overwrite
```

Replace the example URL with a supported Wistia URL or media identifier for content you own or are authorized to download.

## HTTP API

NoybMedia includes a FastAPI application that exposes a health check and a metadata endpoint.

### Start the API server

Run the following command from the repository root:

```bash
uv run uvicorn noybmedia.web.app:app --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`.

Interactive API documentation is available at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Check whether the API is responding. |
| `POST` | `/api/metadata` | Retrieve metadata and available formats for supported Wistia media. |

### Health check

```bash
curl http://127.0.0.1:8000/health
```

Example response:

```json
{
  "status": "ok"
}
```

### Retrieve media metadata

Send a JSON object containing a supported Wistia URL or media identifier:

```bash
curl -X POST http://127.0.0.1:8000/api/metadata \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.wistia.com/medias/abc123def4"}'
```

The response contains the media ID, name, duration, description, and available formats. Each format may include its URL, dimensions, bitrate, container, and file size.

Example response structure:

```json
{
  "media_id": "abc123def4",
  "name": "Example video",
  "duration_seconds": 120.5,
  "description": null,
  "formats": [
    {
      "url": "https://example.com/media.mp4",
      "width": 1920,
      "height": 1080,
      "bitrate_kbps": 4500,
      "container": "mp4",
      "size_bytes": 50000000
    }
  ]
}
```

The response above is illustrative; actual metadata and available formats depend on the requested media.

### Error responses

| HTTP status | Meaning |
|---|---|
| `400 Bad Request` | The supplied URL or identifier is invalid or unsupported. |
| `404 Not Found` | The requested media could not be found. |
| `502 Bad Gateway` | The upstream provider returned an error or could not provide a valid response. |

NoybMedia does not currently expose an HTTP download endpoint. Use the CLI to download supported media.

## Development

### Set up the development environment

Clone the repository and install all dependencies, including development tools:

```bash
uv sync --all-groups
```

### Run the test suite

```bash
uv run pytest
```

### Run tests with coverage

```bash
uv run pytest --cov=noybmedia --cov-report=term-missing --cov-fail-under=90
```

### Check code quality

Run the same quality checks used by GitHub Actions:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv lock --check
```

### Continuous integration

GitHub Actions runs the test suite, coverage check, linting, formatting verification, and static type checking on pushes to `main` and pull requests.

All checks should pass before a change is merged.