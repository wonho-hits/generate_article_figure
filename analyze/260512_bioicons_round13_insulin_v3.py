"""
Analysis: round 13 — insulin v3 with explicit cascade coordinate template
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Round 12 added a high-level "go vertical for 5+ step cascades"
    prompt rule. The LLM did go vertical but introduced new failure
    modes (viewBox too narrow, edge clipping, whitespace gaps,
    label/badge collisions). Final critic score 19 (4 HIGH) vs
    round 11's 13 (3 HIGH) — slight regression.

    Round 13 adds CONCRETE NUMERICAL COORDINATES to the cascade-density
    rule (specific viewBox, step y-positions, label x-positions, etc.).
    Hypothesis: explicit coordinates eliminate the LLM's spatial-
    estimation failure mode.

Compare with round 11 (horizontal-cramped) and round 12 (vertical-but-
sloppy):
    Round 11 final score 13 (3H + L)
    Round 12 final score 19 (4H + M + L)
    Round 13 ??? — goal: <13

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round13_insulin_v3.py
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
    "Insulin signaling pathway: insulin binds the insulin receptor "
    "(an RTK) on the cell membrane. The receptor recruits IRS-1, "
    "which activates PI3K. PI3K phosphorylates the membrane lipid "
    "PIP2 to PIP3. PIP3 recruits and activates AKT (kinase). "
    "Activated AKT phosphorylates downstream targets that mediate "
    "glucose uptake. Show the lipid second messenger conversion and "
    "the kinase cascade with phosphorylation badges. Label every "
    "component."
)


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260512_bioicons_round13_insulin_v3.svg"
    out_png = OUT_DIR / "260512_bioicons_round13_insulin_v3.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())}")
    for k, v in sorted(refs.items()):
        print(f"    {k:30s} ×{v}")
    # Check viewBox aspect (should be tall, matching the template)
    vb_match = re.search(r'<svg[^>]*viewBox="([^"]+)"', svg)
    if vb_match:
        vbx, vby, vbw, vbh = [float(n) for n in vb_match.group(1).split()]
        aspect = vbw / vbh
        print(f"  viewBox: {vb_match.group(1)} (aspect w/h = {aspect:.2f})")
        if aspect < 1.0:
            print(f"  ✓ Portrait aspect — vertical-cascade template followed")
        else:
            print(f"  ⚠ Landscape aspect — template ignored")
    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG: {out_png.name}  ({len(png):,} B)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
