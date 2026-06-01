"""Path D icon post-process: raw generated icon → embeddable transparent PNG.

The icon image model returns a large JPEG (≈1408×768) with the subject on a
solid white field and wide white margins. Embedding that as-is bloats the SVG
to ~600-900 KB per icon. This module turns it into a tight, transparent,
quantized PNG (≈25-85 KB) suitable for a `data:` URI inside Path D SVG.

Pipeline (verified in [[analyze/260601_path_d_icon_postprocess_size.py]]):
  white-threshold alpha → crop to alpha bbox → downscale to cap →
  quantize(N colors, alpha preserved) → optimized PNG.

No rembg / onnxruntime: the icon style prompt mandates clean dark outlines, so
a plain white threshold removes the background cleanly (H60). Pillow only.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image

# Defaults validated by the size probe: worst icon 84 KB, no visible
# degradation at display size. Tune DISPLAY_CAP down (256) or QUANTIZE_COLORS
# down (48) to shave further if SVG size ever becomes a constraint.
DEFAULT_DISPLAY_CAP = 320  # px on the long edge (~2× a typical icon box)
DEFAULT_QUANTIZE_COLORS = 64
DEFAULT_WHITE_THRESHOLD = 240  # R,G,B all ≥ this → background → alpha 0


@dataclass(frozen=True)
class ProcessedIcon:
    """A post-processed icon ready to embed as a data URI."""

    png_bytes: bytes
    width: int
    height: int

    @property
    def aspect(self) -> float:
        """width / height. Used to re-fit the placeholder box without stretch."""
        return self.width / self.height if self.height else 1.0


def _threshold_alpha(img: Image.Image, threshold: int) -> Image.Image:
    """Make near-white pixels transparent. Returns RGBA."""
    rgba = img.convert("RGBA")
    out = [
        (r, g, b, 0)
        if (r >= threshold and g >= threshold and b >= threshold)
        else (r, g, b, a)
        for (r, g, b, a) in rgba.getdata()
    ]
    rgba.putdata(out)
    return rgba


def postprocess_icon(
    raw: bytes,
    *,
    display_cap: int = DEFAULT_DISPLAY_CAP,
    quantize_colors: int = DEFAULT_QUANTIZE_COLORS,
    white_threshold: int = DEFAULT_WHITE_THRESHOLD,
) -> ProcessedIcon:
    """Turn a raw generated icon into a tight transparent quantized PNG.

    Raises ValueError on empty input or an image that is entirely background
    (nothing left after thresholding → no bbox).
    """
    if not raw:
        raise ValueError("raw icon bytes are empty")

    try:
        src = Image.open(BytesIO(raw))
        src.load()
    except Exception as exc:  # noqa: BLE001 — Pillow raises a zoo of errors
        raise ValueError(f"unreadable icon image: {exc}") from exc

    rgba = _threshold_alpha(src, white_threshold)

    bbox = rgba.getbbox()  # tight box of non-transparent content
    if bbox is None:
        raise ValueError("icon is entirely background after threshold removal")
    cropped = rgba.crop(bbox)
    cropped.thumbnail((display_cap, display_cap), Image.LANCZOS)

    # Quantize the RGB channels (flat art compresses well) while preserving the
    # alpha mask — quantizing RGBA directly would dither the transparency.
    alpha = cropped.getchannel("A")
    rgb = (
        cropped.convert("RGB")
        .quantize(colors=quantize_colors, method=Image.FASTOCTREE)
        .convert("RGB")
    )
    out = rgb.convert("RGBA")
    out.putalpha(alpha)

    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    return ProcessedIcon(png_bytes=buf.getvalue(), width=out.width, height=out.height)
