# NoybMedia

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

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/no-yb-core/noybmedia.git
cd noybmedia
uv sync