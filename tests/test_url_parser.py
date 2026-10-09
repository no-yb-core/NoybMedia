import pytest

from noybmedia.providers.url_parser import InvalidWistiaUrlError, parse_wistia_url

VALID_MEDIA_ID = "abc123def4"


@pytest.mark.parametrize(
    "url",
    [
        f"https://home.wistia.com/medias/{VALID_MEDIA_ID}",
        f"https://mycompany.wistia.com/medias/{VALID_MEDIA_ID}",
        f"https://wistia.com/medias/{VALID_MEDIA_ID}",
        f"https://wistia.net/medias/{VALID_MEDIA_ID}",
        f"https://fast.wistia.com/embed/iframe/{VALID_MEDIA_ID}",
        f"https://fast.wistia.net/embed/iframe/{VALID_MEDIA_ID}",
        f"https://fast.wistia.com/embed/medias/{VALID_MEDIA_ID}",
        f"https://fast.wistia.net/embed/medias/{VALID_MEDIA_ID}",
        f"http://home.wistia.com/medias/{VALID_MEDIA_ID}",
        f"https://home.wistia.com/medias/{VALID_MEDIA_ID}/",
        f"https://fast.wistia.net/embed/iframe/{VALID_MEDIA_ID}/",
    ],
)
def test_parse_supported_wistia_urls(url: str) -> None:
    assert parse_wistia_url(url) == VALID_MEDIA_ID


@pytest.mark.parametrize(
    "value",
    [
        VALID_MEDIA_ID,
        f"  {VALID_MEDIA_ID}  ",
        f"\t{VALID_MEDIA_ID}\n",
    ],
)
def test_parse_raw_media_identifier(value: str) -> None:
    assert parse_wistia_url(value) == VALID_MEDIA_ID


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_empty_or_whitespace_only_input_raises(value: str) -> None:
    with pytest.raises(InvalidWistiaUrlError):
        parse_wistia_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "not a url",
        "http://",
        "https://",
        "https:///medias/abc123def4",
        "https://wistia.com",
        "https://wistia.com/medias",
        "https://wistia.com/medias/",
        "https://wistia.com/medias/abc",
        "https://wistia.com/medias/abc123def45",
        "https://wistia.com/medias/abc123def4/extra",
        "https://wistia.com/videos/abc123def4",
        "https://fast.wistia.net/embed/player/abc123def4",
        "https://fast.wistia.net/embed/iframe/",
        "https://fast.wistia.net/embed/medias/abc123def4.json",
    ],
)
def test_malformed_or_unsupported_urls_raise(value: str) -> None:
    with pytest.raises(InvalidWistiaUrlError):
        parse_wistia_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "ftp://wistia.com/medias/abc123def4",
        "file://wistia.com/medias/abc123def4",
        "javascript:alert(1)",
    ],
)
def test_unsupported_schemes_raise(value: str) -> None:
    with pytest.raises(InvalidWistiaUrlError):
        parse_wistia_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/medias/abc123def4",
        "https://notwistia.com/medias/abc123def4",
        "https://wistia.example.com/medias/abc123def4",
        "https://wistia.com.example.org/medias/abc123def4",
        "https://evilwistia.com/medias/abc123def4",
        "https://wistia.com.evil.org/medias/abc123def4",
        "https://wistia.net.evil.org/embed/iframe/abc123def4",
    ],
)
def test_unrelated_or_spoofed_hostnames_raise(value: str) -> None:
    with pytest.raises(InvalidWistiaUrlError):
        parse_wistia_url(value)


@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "abc123def",
        "abc123def45",
        "abc123def!",
        "abc123def_4",
        "ABC123DEF4",
        "abc 123def4",
    ],
)
def test_invalid_raw_media_identifiers_raise(value: str) -> None:
    with pytest.raises(InvalidWistiaUrlError):
        parse_wistia_url(value)


@pytest.mark.parametrize(
    "url, expected",
    [
        (f"https://wistia.com/medias/{VALID_MEDIA_ID}?foo=bar", VALID_MEDIA_ID),
        (f"https://wistia.com/medias/{VALID_MEDIA_ID}#section", VALID_MEDIA_ID),
        (f"https://wistia.com/medias/{VALID_MEDIA_ID}?wvideo=other", VALID_MEDIA_ID),
        (
            f"https://fast.wistia.net/embed/iframe/{VALID_MEDIA_ID}?videoId=other",
            VALID_MEDIA_ID,
        ),
    ],
)
def test_query_strings_and_fragments_are_ignored(url: str, expected: str) -> None:
    assert parse_wistia_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://wistia.com/medias/?id=abc123def4",
        "https://wistia.com/medias/?wvideo=abc123def4",
        "https://wistia.com/?id=abc123def4",
        "https://fast.wistia.net/embed/iframe/?videoId=abc123def4",
    ],
)
def test_ids_in_query_parameters_are_not_accepted(url: str) -> None:
    with pytest.raises(InvalidWistiaUrlError):
        parse_wistia_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://wistia.com/medias/abc123def4/download",
        "https://wistia.com/medias/abc123def4/other",
        "https://fast.wistia.net/embed/iframe/abc123def4/extra",
        "https://fast.wistia.net/embed/medias/abc123def4.json",
    ],
)
def test_unexpected_paths_raise(url: str) -> None:
    with pytest.raises(InvalidWistiaUrlError):
        parse_wistia_url(url)
