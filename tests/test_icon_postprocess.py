"""Tests for the Path D icon post-process pipeline."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.tools.icon_postprocess import ProcessedIcon, postprocess_icon


def _make_icon_jpeg(canvas=(400, 200), box=(150, 60, 250, 140), color=(40, 90, 160)) -> bytes:
    """White JPEG with a colored rectangle subject (mimics a generated icon)."""
    img = Image.new("RGB", canvas, (255, 255, 255))
    for x in range(box[0], box[2]):
        for y in range(box[1], box[3]):
            img.putpixel((x, y), color)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def test_crops_to_subject_bbox() -> None:
    raw = _make_icon_jpeg(canvas=(400, 200), box=(150, 60, 250, 140))
    icon = postprocess_icon(raw)
    # subject was 100x80 → output keeps that aspect, not the 400x200 canvas
    assert isinstance(icon, ProcessedIcon)
    assert icon.width <= 320 and icon.height <= 320
    assert abs(icon.aspect - (100 / 80)) < 0.2  # JPEG fuzz tolerance


def test_output_is_png_with_alpha() -> None:
    raw = _make_icon_jpeg()
    icon = postprocess_icon(raw)
    out = Image.open(BytesIO(icon.png_bytes))
    assert out.format == "PNG"
    assert out.mode == "RGBA"


def test_white_background_becomes_transparent() -> None:
    raw = _make_icon_jpeg()
    icon = postprocess_icon(raw)
    out = Image.open(BytesIO(icon.png_bytes)).convert("RGBA")
    # corners (were white margin, cropped away) — check the cropped edge is the
    # subject; sample a transparent vs opaque pixel count instead.
    alphas = [p[3] for p in out.getdata()]
    assert min(alphas) == 0  # some fully transparent pixels exist
    assert max(alphas) == 255  # subject is opaque


def test_downscale_cap_respected() -> None:
    raw = _make_icon_jpeg(canvas=(1408, 768), box=(100, 100, 1300, 700))
    icon = postprocess_icon(raw, display_cap=320)
    assert max(icon.width, icon.height) <= 320


def test_empty_input_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        postprocess_icon(b"")


def test_all_white_image_raises() -> None:
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    with pytest.raises(ValueError, match="entirely background"):
        postprocess_icon(buf.getvalue())
