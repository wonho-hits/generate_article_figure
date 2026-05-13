"""
Analysis: round 12 — anaphase wrapper + cascade-density rule verification
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Two gaps from round 11 dogfood, both addressed in this round:
- Missing `bioicons_mitosis_anaphase` wrapper (LLM had to draw anaphase
  from primitives in round 11 mitosis dogfood).
- Dense horizontal cascade layout fail (round 11 insulin: pass 1 score
  32, six HIGH severities; pass 2 still 3 HIGH).

Verification:
- Test A: re-run the round 11 mitosis prompt. Does the LLM now reach
  for `bioicons_mitosis_anaphase` instead of primitives?
- Test B: re-run the round 11 insulin prompt. Does the LLM follow the
  new "vertical or multi-row when ≥ 5 steps" rule?

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round12_anaphase_layout.py
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

PROMPTS = {
    "mitosis_stages_v2": (
        "Draw a figure showing the major stages of mitosis (interphase, "
        "prophase, prometaphase, metaphase, anaphase, telophase) in a "
        "single eukaryotic cell. Show each stage as a separate labelled "
        "panel arranged left-to-right. Title the figure 'Mitosis: stages "
        "of nuclear division'."
    ),
    "insulin_signaling_v2": (
        "Insulin signaling pathway: insulin binds the insulin receptor "
        "(an RTK) on the cell membrane. The receptor recruits IRS-1, "
        "which activates PI3K. PI3K phosphorylates the membrane lipid "
        "PIP2 to PIP3. PIP3 recruits and activates AKT (kinase). "
        "Activated AKT phosphorylates downstream targets that mediate "
        "glucose uptake. Show the lipid second messenger conversion and "
        "the kinase cascade with phosphorylation badges. Label every "
        "component."
    ),
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260512_bioicons_round12_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round12_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())} ({len(refs)} unique)")
    for k, v in sorted(refs.items()):
        print(f"    {k:35s} ×{v}")
    # Sanity-check all <use> have dims
    use_tags = re.findall(r"<use\b[^/]+/>", svg)
    missing_dims = [
        t for t in use_tags
        if not (re.search(r"\bwidth\s*=", t) and re.search(r"\bheight\s*=", t))
    ]
    print(f"  <use> tags: {len(use_tags)}, missing dims: {len(missing_dims)}")
    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG: {out_png.name}  ({len(png):,} B)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


async def main() -> None:
    for name, prompt in PROMPTS.items():
        await run_one(name, prompt)


if __name__ == "__main__":
    asyncio.run(main())
