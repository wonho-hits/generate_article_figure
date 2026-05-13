"""
Analysis: round 18 — autophagy / mitophagy dogfood
Date: 2026-05-13
Related: docs/progress/260512_bioicons_pilot.md

Round 18 adds 2 hand-written autophagy icons (autophagosome,
lysosome). Both fill specific gaps no existing organelle/vesicle
icon covered:
  • autophagosome = double-membrane vesicle with cargo (defining
    feature: TWO concentric rings) — distinct from endocytosis
    (single-membrane, extracellular cargo) and mitochondrion.
  • lysosome = acidic single-membrane compartment with hydrolases —
    distinct from generic vesicles by purple acidic palette.

Dogfood: open prompt describing mitophagy (selective autophagy of a
damaged mitochondrion). Test whether the LLM picks BOTH new icons
without hints.

Usage:
    PYTHONPATH=. uv run python analyze/260513_bioicons_round18_autophagy.py
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

PROMPT = (
    "Draw a mitophagy figure showing how a cell selectively degrades a "
    "damaged mitochondrion. The sequence: (1) a damaged mitochondrion in "
    "the cytoplasm, (2) it gets enclosed by a forming double-membraned "
    "autophagosome, (3) the autophagosome fuses with a lysosome to form "
    "an autolysosome, (4) the lysosomal acidic hydrolases degrade the "
    "mitochondrion. Label each stage. Title the figure 'Mitophagy: "
    "selective autophagy of damaged mitochondria'."
)

EXPECTED = {"autophagosome", "lysosome", "mitochondrion"}


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260513_bioicons_round18_autophagy.svg"
    out_png = OUT_DIR / "260513_bioicons_round18_autophagy.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    found = EXPECTED & refs.keys()
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  expected ∩ found: {len(found)}/{len(EXPECTED)}")
    print(f"    found:   {sorted(found)}")
    print(f"    missing: {sorted(EXPECTED - refs.keys())}")
    print(f"  full refs:")
    for k, v in sorted(refs.items()):
        marker = " ←expected" if k in EXPECTED else ""
        print(f"    {k:32s} ×{v}{marker}")
    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG: {out_png.name}  ({len(png):,} B)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
