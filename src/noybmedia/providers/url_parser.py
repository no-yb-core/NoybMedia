"""Parse Wistia media URLs and identifiers.

Supported formats
-----------------
- ``https://<account>.wistia.com/medias/<id>``
- ``https://wistia.com/medias/<id>``
- ``https://wistia.net/medias/<id>``
- ``https://fast.wistia.com/embed/iframe/<id>``
- ``https://fast.wistia.net/embed/iframe/<id>``
- ``https://fast.wistia.com/embed/medias/<id>``
- ``https://fast.wistia.net/embed/medias/<id>``
- Raw media identifier: 10 lowercase alphanumeric characters ``[a-z0-9]{10}``.

Whitespace around the input is ignored. Query strings and fragments are ignored
once the URL structure is recognized.

Limitations
-----------
- Does not support shortened URLs, ``.json`` endpoints, or undocumented paths.
- Does not make network requests.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from noybmedia.exceptions import ValidationError

_MEDIA_ID_RE = re.compile(r"^[a-z0-9]{10}$")
_SUPPORTED_SCHEMES = frozenset({"http", "https"})
_SUPPORTED_HOSTS = frozenset({"wistia.com", "wistia.net"})
_SUPPORTED_HOST_SUFFIXES = (".wistia.com", ".wistia.net")


class InvalidWistiaUrlError(ValidationError):
    """Raised when a value is not a supported Wistia URL or media identifier."""


def _is_supported_wistia_hostname(hostname: str | None) -> bool:
    if not hostname:
        return False

    host = hostname.lower()
    if host in _SUPPORTED_HOSTS:
        return True

    return host.endswith(_SUPPORTED_HOST_SUFFIXES)


def _extract_media_id_from_path(path: str) -> str | None:
    normalized_path = path.rstrip("/")
    if not normalized_path:
        return None

    parts = normalized_path.split("/")
    # parts[0] is empty because the path starts with "/".
    if len(parts) == 3 and parts[1] == "medias":
        return parts[2]

    if len(parts) == 4 and parts[1] == "embed" and parts[2] in {"iframe", "medias"}:
        return parts[3]

    return None


def parse_wistia_url(value: str) -> str:
    """Return the normalized Wistia media identifier from *value*.

    Accepts supported Wistia media URLs, embed URLs, or a raw media identifier.
    Leading and trailing whitespace is ignored. Raises ``InvalidWistiaUrlError``
    for empty input, malformed URLs, unsupported schemes or hosts, and invalid
    media identifiers.
    """

    candidate = value.strip()
    if not candidate:
        raise InvalidWistiaUrlError("Wistia URL or identifier must not be empty.")

    if _MEDIA_ID_RE.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate)

    if parsed.scheme.lower() not in _SUPPORTED_SCHEMES:
        raise InvalidWistiaUrlError(f"Unsupported URL scheme: {parsed.scheme!r}")

    if not _is_supported_wistia_hostname(parsed.hostname):
        raise InvalidWistiaUrlError(f"Unsupported Wistia hostname: {parsed.hostname!r}")

    media_id = _extract_media_id_from_path(parsed.path)
    if media_id is None or not _MEDIA_ID_RE.fullmatch(media_id):
        raise InvalidWistiaUrlError(
            "URL does not contain a valid Wistia media identifier."
        )

    return media_id
