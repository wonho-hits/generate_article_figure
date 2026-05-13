"""
Analysis: round 10b — MAPK dogfood prompt after the use-dimension fix
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    The round 10 MAPK figure was broken because the LLM emitted
    `<use href="#p_badge" x=.. y=.. />` without width/height, and SVG
    treats absent dimensions on `<use>` as 100% of the viewport — so
    the 24×24 P badges scaled to ~800-1000 px each and dominated the
    figure.

    Round 10b adds `_patch_use_dimensions` (defensive post-processing
    that injects catalog `default_w` / `default_h` on dimensionless
    <use> elements) and re-runs the same MAPK prompt to verify the
    visual quality.

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round10b_mapk_after_fix.py
"""

from __future__ import annotations

import asyncio
import re
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from app.tools.svg_render import rasterize_svg
from app.tools.vector_schematic import generate_vector_schematic

OUT_DIR = Path(__file__).resolve().parent

# Exactly the round 10 MAPK prompt — no icon hints.
PROMPT = (
    "Draw a clear pathway figure of MAPK signaling: EGF binds EGFR on "
    "the cell surface, activating the Ras-Raf-MEK-ERK kinase cascade. "
    "Activated ERK enters the nucleus and turns on a transcription "
    "factor that drives gene expression. Show phosphorylation events "
    "at each kinase step. Label each component."
)


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260512_bioicons_round10b_mapk_after_fix.svg"
    out_png = OUT_DIR / "260512_bioicons_round10b_mapk_after_fix.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs:  {sum(refs.values())}")
    for k, v in sorted(refs.items()):
        print(f"    {k:30s} ×{v}")

    # Check that p_badge in the body got dimensioned (the bug fix).
    use_tags = re.findall(r'<use[^/]*href="#p_badge"[^/]*/>', svg)
    print(f"\n  p_badge <use> tags in body: {len(use_tags)}")
    for t in use_tags[:3]:
        has_w = "width" in t
        has_h = "height" in t
        print(f"    {'OK' if has_w and has_h else 'MISSING DIMS'}: {t}")

    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG: {out_png.name}  ({len(png):,} B)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
