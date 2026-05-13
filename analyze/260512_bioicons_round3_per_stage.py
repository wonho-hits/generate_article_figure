"""
Analysis: round 3 — per-stage cell-cycle icons
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Round 1+2 surfaced H29: composite icons (one icon for the whole
    mitosis cycle) force the LLM to guess label positions and mis-align
    them. Per-stage icons (fertilization pattern) work cleanly.

    Round 3: decomposed `bioicons_mitosis` into 5 per-stage wrappers
    (interphase/prophase/prometaphase/metaphase/telophase) via thin
    viewBox-cropping symbols + transitive <use> resolution in lazy
    injection. Does the LLM now compose a clean stage-by-stage figure?

Judgment criteria:
    1. Output references multiple bioicons_mitosis_<stage> symbols (not
       a single bioicons_mitosis composite).
    2. Each <use> is co-located with its stage-name <text> label.
    3. Vision critic reports no HIGH-severity layout issues after the
       refine passes.
    4. Rendered PNG shows 5 cells with correctly-positioned labels.

Conclusion:
    [filled in after run]

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round3_per_stage.py
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
    "Cell cycle figure showing the five mitosis stages "
    "(interphase, prophase, prometaphase, metaphase, telophase) of a "
    "single eukaryotic cell. Place each stage in its own labelled panel "
    "in a horizontal row, left-to-right in the order listed. Add a title "
    "'Mitosis: phases of cell division' centred at the top of the figure."
)


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260512_bioicons_round3_per_stage.svg"
    out_png = OUT_DIR / "260512_bioicons_round3_per_stage.png"
    out_svg.write_text(svg)

    # Count which bioicons_* refs were used
    refs = re.findall(r'href="#(bioicons_\w+)"', svg)
    from collections import Counter
    counts = Counter(refs)
    per_stage_refs = {k: v for k, v in counts.items() if "_mitosis_" in k}
    composite_refs = counts.get("bioicons_mitosis", 0)

    print(f"SVG written: {out_svg}  ({len(svg):,} bytes)")
    print(f"  bioicons_mitosis composite refs:   {composite_refs}")
    print(f"  per-stage bioicons_mitosis_* refs:")
    for k, v in sorted(per_stage_refs.items()):
        print(f"    {k}: {v}")

    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG written: {out_png}")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
