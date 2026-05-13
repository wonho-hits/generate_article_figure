"""
Analysis: round 15 — dogfood early-development sequence (sperm → blastocyst)
Date: 2026-05-13
Related: docs/progress/260512_bioicons_pilot.md

Round 15 adds 3 new bundled icons (bioicons_sperm + bioicons_embryo_morula
+ bioicons_embryo_blastocyst) completing the early-development arc that
started with bioicons_zygote + bioicons_embryo_2cell in round 1.

Dogfood: open prompt describing the developmental sequence WITHOUT
mentioning any icon names. Test:
  1. Does the LLM pick all 5 stage icons?
  2. Are they laid out as a sequence with arrows?
  3. Critic outcome.

Usage:
    PYTHONPATH=. uv run python analyze/260513_bioicons_round15_development_dogfood.py
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
    "Draw a figure showing the early stages of mammalian development from "
    "fertilization to blastocyst. Show: (1) a sperm meeting an egg, (2) the "
    "resulting zygote with two pronuclei, (3) the 2-cell embryo after first "
    "cleavage, (4) the morula stage (~16-cell cluster), and (5) the early "
    "blastocyst with its fluid-filled cavity and inner cell mass. Arrange the "
    "five stages left-to-right with arrows between them, label each panel, "
    "and add a title."
)

EXPECTED = {
    "bioicons_sperm", "bioicons_zygote", "bioicons_embryo_2cell",
    "bioicons_embryo_morula", "bioicons_embryo_blastocyst",
}


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260513_bioicons_round15_development.svg"
    out_png = OUT_DIR / "260513_bioicons_round15_development.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    found_expected = EXPECTED & refs.keys()
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())} ({len(refs)} unique)")
    print(f"  expected ∩ found: {len(found_expected)}/{len(EXPECTED)}")
    print(f"    found:   {sorted(found_expected)}")
    print(f"    missing: {sorted(EXPECTED - refs.keys())}")
    print(f"  full ref count:")
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
