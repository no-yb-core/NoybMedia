import dataclasses

import pytest

from noybmedia.domain.media import MediaFormat, MediaMetadata
from noybmedia.exceptions import ValidationError


class TestMediaFormat:
    def test_valid_minimal_format(self) -> None:
        fmt = MediaFormat(url="https://example.com/v.mp4")
        assert fmt.url == "https://example.com/v.mp4"
        assert fmt.width is None
        assert fmt.height is None
        assert fmt.container is None
        assert fmt.resolution_label is None

    def test_valid_full_format(self) -> None:
        fmt = MediaFormat(
            url="https://example.com/v.mp4",
            width=1920,
            height=1080,
            bitrate_kbps=4500,
            container="mp4",
            size_bytes=123_456_789,
        )
        assert fmt.resolution_label == "1080p"
        assert fmt.container == "mp4"
        assert fmt.size_bytes == 123_456_789

    def test_container_is_normalized(self) -> None:
        fmt = MediaFormat(url="https://example.com/v.mp4", container=".MP4")
        assert fmt.container == "mp4"

    @pytest.mark.parametrize("url", ["", "   "])
    def test_blank_url_rejected(self, url: str) -> None:
        with pytest.raises(ValidationError):
            MediaFormat(url=url)

    @pytest.mark.parametrize("width", [0, -1])
    def test_non_positive_width_rejected(self, width: int) -> None:
        with pytest.raises(ValidationError):
            MediaFormat(url="https://example.com/v.mp4", width=width)

    @pytest.mark.parametrize("height", [0, -1])
    def test_non_positive_height_rejected(self, height: int) -> None:
        with pytest.raises(ValidationError):
            MediaFormat(url="https://example.com/v.mp4", height=height)

    @pytest.mark.parametrize("bitrate", [0, -100])
    def test_non_positive_bitrate_rejected(self, bitrate: int) -> None:
        with pytest.raises(ValidationError):
            MediaFormat(url="https://example.com/v.mp4", bitrate_kbps=bitrate)

    def test_negative_size_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MediaFormat(url="https://example.com/v.mp4", size_bytes=-1)

    @pytest.mark.parametrize("container", ["", "   ", "."])
    def test_blank_container_rejected(self, container: str) -> None:
        with pytest.raises(ValidationError):
            MediaFormat(url="https://example.com/v.mp4", container=container)

    def test_is_frozen(self) -> None:
        meta = MediaMetadata(media_id="abc123def4", name="Sample")
        attr_name = "name"
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(meta, attr_name, "Other")

    def test_equality_is_by_value(self) -> None:
        a = MediaFormat(url="https://example.com/v.mp4", height=720)
        b = MediaFormat(url="https://example.com/v.mp4", height=720)
        assert a == b


class TestMediaMetadata:
    def test_valid_minimal_metadata(self) -> None:
        meta = MediaMetadata(media_id="abc123def4", name="Sample")
        assert meta.media_id == "abc123def4"
        assert meta.name == "Sample"
        assert meta.formats == ()
        assert meta.has_formats is False

    def test_metadata_with_formats(self) -> None:
        fmt = MediaFormat(url="https://example.com/v.mp4", height=720)
        meta = MediaMetadata(media_id="abc123def4", name="Sample", formats=(fmt,))
        assert meta.has_formats is True
        assert meta.formats == (fmt,)

    def test_media_id_required(self) -> None:
        with pytest.raises(ValidationError):
            MediaMetadata(media_id="", name="Sample")

    def test_name_required(self) -> None:
        with pytest.raises(ValidationError):
            MediaMetadata(media_id="abc123def4", name="")

    def test_negative_duration_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MediaMetadata(media_id="abc123def4", name="Sample", duration_seconds=-1.0)

    def test_formats_coerced_to_tuple(self) -> None:
        fmt = MediaFormat(url="https://example.com/v.mp4")
        meta = MediaMetadata(
            media_id="abc123def4",
            name="Sample",
            formats=[fmt],  # type: ignore[arg-type]
        )
        assert isinstance(meta.formats, tuple)
        assert meta.formats == (fmt,)

    def test_formats_by_quality_sorts_descending(self) -> None:
        low = MediaFormat(url="https://example.com/low.mp4", width=640, height=360)
        mid = MediaFormat(url="https://example.com/mid.mp4", width=1280, height=720)
        high = MediaFormat(url="https://example.com/high.mp4", width=1920, height=1080)
        meta = MediaMetadata(
            media_id="abc123def4",
            name="Sample",
            formats=(low, high, mid),
        )
        assert meta.formats_by_quality() == (high, mid, low)

    def test_formats_by_quality_ranks_unknown_below_known(self) -> None:
        unknown = MediaFormat(url="https://example.com/x.mp4")
        known = MediaFormat(url="https://example.com/k.mp4", height=720)
        meta = MediaMetadata(
            media_id="abc123def4",
            name="Sample",
            formats=(unknown, known),
        )
        assert meta.formats_by_quality() == (known, unknown)

    def test_is_frozen(self) -> None:
        meta = MediaMetadata(media_id="abc123def4", name="Sample")
        attr_name = "name"
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(meta, attr_name, "Other")
