"""
Analysis: round 4 — per-stage MEIOSIS icons
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Round 2's meiosis prompt failed: LLM used the bioicons_meiosis
    composite once and tried to overlay 8 stage labels at guessed pixel
    positions — about half landed wrong, Meiosis II row visually empty.

    Round 3 proved the per-stage decomposition approach works on mitosis.
    Round 4 applies the same pattern to meiosis: 8 per-stage wrappers
    (4 Meiosis I + 4 Meiosis II) cropped from `bioicons_meiosis` via
    viewBox-cropping. Does the LLM now compose a clean 8-stage figure?

Judgment criteria:
    1. LLM emits ≥ 4 `bioicons_meiosis_<stage>` refs (one per major stage).
    2. Each <use> is co-located with its stage-name <text> label.
    3. Vision critic returns no HIGH-severity issues after refine passes.
    4. Round-2's broken "empty Meiosis II row" failure mode is gone.

Conclusion:
    [filled in after run]

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round4_meiosis.py
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from app.tools.svg_render import rasterize_svg
from app.tools.vector_schematic import generate_vector_schematic

OUT_DIR = Path(__file__).resolve().parent

PROMPT = (
    "Show the stages of meiosis in a single eukaryotic cell, including "
    "both Meiosis I (reductional division: prophase I, metaphase I, "
    "anaphase I, telophase I) and Meiosis II (equational division: "
    "prophase II, metaphase II, anaphase II, telophase II). Place each "
    "of the 8 stages in its own labelled panel — arrange Meiosis I on "
    "the top row and Meiosis II on the bottom row. Title the figure "
    "'Meiosis: phases of reductional and equational division'."
)


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260512_bioicons_round4_meiosis.svg"
    out_png = OUT_DIR / "260512_bioicons_round4_meiosis.png"
    out_svg.write_text(svg)

    from collections import Counter
    refs = re.findall(r'href="#(bioicons_\w+)"', svg)
    counts = Counter(refs)
    per_stage = sorted(k for k in counts if "_meiosis_" in k)
    composite = counts.get("bioicons_meiosis", 0)

    print(f"SVG written: {out_svg}  ({len(svg):,} bytes)")
    print(f"  bioicons_meiosis composite refs (should be 0 in body): {composite}")
    print(f"  per-stage bioicons_meiosis_* refs:")
    for k in per_stage:
        print(f"    {k}: {counts[k]}")

    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG written: {out_png}")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
