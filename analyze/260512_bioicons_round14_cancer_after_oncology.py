"""
Analysis: round 14 — cancer invasion dogfood after adding oncology icons
Date: 2026-05-13
Related: docs/progress/260512_bioicons_pilot.md

Round 10 dogfooded a cancer-invasion prompt — LLM picked 30 use refs
(15 collagen + 10 mmp + 3 fibronectin + 2 proteoglycan) but had to
draw the tumor cell from primitives (just used a labelled rounded
rect). Round 14 adds 2 bundled oncology icons (bioicons_cancer_cell,
bioicons_tumor) and re-runs the SAME prompt to see if the LLM now
uses the cancer cell icon AND whether overall composition improves.

Same prompt as round 10:
    "Cancer-cell invasion through the extracellular matrix. A tumor
    cell sits in an ECM rich in collagen fibres. The tumor cell
    secretes proteases that cleave the collagen, opening a path for
    the cell to migrate through. Show the proteolytic cleavage
    explicitly (broken collagen fibres at the cleavage points) and
    label the proteases. Add a small movement arrow showing where
    the cell will migrate. Title the figure."

Comparison:
    Round 10 (no cancer icon): tumor cell drawn as primitive ellipse;
        30 use refs (15 collagen + 10 mmp + 3 fibronectin + 2 proteoglycan)
        critic pass 1 score 5 (1 high + 1 low), pass 2 score 6
    Round 14 (oncology added): expect bioicons_cancer_cell to be picked
        instead of a primitive shape

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round14_cancer_after_oncology.py
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
    "Cancer-cell invasion through the extracellular matrix. A tumor "
    "cell sits in an ECM rich in collagen fibres. The tumor cell "
    "secretes proteases that cleave the collagen, opening a path for "
    "the cell to migrate through. Show the proteolytic cleavage "
    "explicitly (broken collagen fibres at the cleavage points) and "
    "label the proteases. Add a small movement arrow showing where "
    "the cell will migrate. Title the figure."
)


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260512_bioicons_round14_cancer_after_oncology.svg"
    out_png = OUT_DIR / "260512_bioicons_round14_cancer_after_oncology.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())} ({len(refs)} unique)")
    for k, v in sorted(refs.items()):
        marker = ""
        if k == "bioicons_cancer_cell":
            marker = " ← NEW (was generic_protein in round 10)"
        elif k == "bioicons_tumor":
            marker = " ← NEW"
        print(f"    {k:30s} ×{v}{marker}")
    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG: {out_png.name}  ({len(png):,} B)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
