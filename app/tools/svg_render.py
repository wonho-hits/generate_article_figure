"""SVG → PNG rasterization for the vision-based layout critic.

Renderer priority:
  1. cairosvg (cross-platform; requires `cairo` system library)
  2. qlmanage subprocess (macOS only; built-in)

On any unrecoverable error, raises SVGRenderError. Callers should fall back
to a no-critic path on failure.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class SVGRenderError(RuntimeError):
    """Raised when no SVG renderer is available or all renderers fail."""


def rasterize_svg(svg_string: str, *, width: int = 1600) -> bytes:
    """Render an SVG string to PNG bytes at the given width (height = aspect-fit)."""
    if not svg_string or not svg_string.strip():
        raise SVGRenderError("empty SVG input")

    errors: list[str] = []

    try:
        return _render_via_cairosvg(svg_string, width=width)
    except Exception as exc:
        errors.append(f"cairosvg: {type(exc).__name__}: {exc}")
        logger.debug("svg_render.cairosvg_failed", error=str(exc))

    try:
        return _render_via_qlmanage(svg_string, width=width)
    except FileNotFoundError as exc:
        errors.append(f"qlmanage: not available ({exc})")
    except Exception as exc:
        errors.append(f"qlmanage: {type(exc).__name__}: {exc}")
        logger.debug("svg_render.qlmanage_failed", error=str(exc))

    raise SVGRenderError(
        "all SVG renderers failed: " + " | ".join(errors)
    )


def _render_via_cairosvg(svg_string: str, *, width: int) -> bytes:
    import cairosvg  # type: ignore[import-not-found]

    return cairosvg.svg2png(
        bytestring=svg_string.encode("utf-8"),
        output_width=width,
    )


def _render_via_qlmanage(svg_string: str, *, width: int) -> bytes:
    if shutil.which("qlmanage") is None:
        raise FileNotFoundError("qlmanage not on PATH (macOS-only fallback)")

    with tempfile.TemporaryDirectory(prefix="svg_render_") as tmpdir:
        tmp = Path(tmpdir)
        in_path = tmp / "input.svg"
        in_path.write_text(svg_string, encoding="utf-8")

        result = subprocess.run(
            ["qlmanage", "-t", "-s", str(width), "-o", str(tmp), str(in_path)],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"qlmanage exit {result.returncode}: "
                f"{result.stderr.decode(errors='replace')[:200]}"
            )

        # qlmanage writes "<filename>.png" next to the input file's name
        png_path = tmp / f"{in_path.name}.png"
        if not png_path.exists():
            raise RuntimeError(f"qlmanage produced no PNG at {png_path}")
        return png_path.read_bytes()
