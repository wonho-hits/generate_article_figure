"""
Analysis: bioicons pilot — cell cycle prompt with bundled Servier icons
Date: 2026-05-12
Related progress log: docs/progress/260512_bioicons_pilot.md

Problem:
    Path A's hand-written symbol library can't render BioRender-quality
    cell-cycle figures. We've bundled 2 Servier line-art symbols
    (bioicons_mitosis, bioicons_chromosome) and updated the system prompt
    to advertise them. Does Path A now produce a recognisable mitosis-cycle
    figure that uses the new symbols?

Judgment criteria:
    1. SVG output contains at least one <use href="#bioicons_*"/> — i.e.,
       the LLM actually reaches for the new symbols.
    2. Rasterised PNG shows recognisable mitosis stages.
    3. Vision critic returns no HIGH-severity layout issues after refine
       passes (we still use the default max_refine_passes=2).

Conclusion (v1 — pre keep-best, pre lazy-injection):
    - LLM successfully reached for `bioicons_mitosis`. Rendered output is a
      dramatic quality improvement over the primitives baseline.
    - SVG size: 63 KB. Defs block: full 62 KB library (carried 33 unused
      symbols per response).
    - Vision critic REGRESSED across passes (pass 1: 1 low → pass 2: 3 high).
      Current refine loop shipped the regressed output. Filed follow-up to
      track per-pass severity and ship the best critiqued candidate.

Conclusion (v2 — after keep-best + lazy injection):
    - Pass 1: score 1 (1 low). Pass 2: score 1 (1 low, tied). Final regen
      not critiqued; keep-best correctly returns pass 1's SVG.
    - SVG total: 44,550 bytes (was 63,511; **30% smaller**).
    - Top-level <defs> contains only `bioicons_mitosis` — the 33 unused
      hand-written symbols (~20KB of wasted bytes per response in v1) are
      gone.
    - Visual quality preserved. The same chromosome / spindle anatomy
      renders. Stage label placement is still approximate (a Servier-
      composite limitation, not a regression).
    - Logger trail confirms keep-best: `path_a.refine_returning_best
      best_score=1` instead of silently shipping the un-critiqued final
      regen.

Usage:
    uv run python analyze/260512_bioicons_pilot_cellcycle.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from app.tools.svg_render import rasterize_svg
from app.tools.vector_schematic import generate_vector_schematic

PROMPT = (
    "Cell cycle figure showing the four mitosis stages "
    "(prophase, metaphase, anaphase, telophase) of a single cell. "
    "Below each stage place the stage name. Above the figure place a "
    "title 'Mitosis: phases of cell division'. Use the bioicons mitosis "
    "and chromosome symbols if helpful."
)

OUT_DIR = Path(__file__).resolve().parent


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    # v2 of the run (after keep-best + lazy injection).
    out_svg = OUT_DIR / "260512_bioicons_pilot_cellcycle_v2.svg"
    out_png = OUT_DIR / "260512_bioicons_pilot_cellcycle_v2.png"
    out_svg.write_text(svg)

    used_mitosis = svg.count('href="#bioicons_mitosis"')
    used_chrom = svg.count('href="#bioicons_chromosome"')
    use_count = svg.count("<use ")
    # Approx defs size — the lazy-injected block only carries used symbols.
    import re

    defs_match = re.search(r"<defs[^>]*>.*?</defs>", svg, re.DOTALL)
    defs_size = len(defs_match.group()) if defs_match else 0
    print(f"SVG written: {out_svg}  ({len(svg):,} bytes)")
    print(f"  <defs> block size: {defs_size:,} bytes")
    print(f"  <use> elements total: {use_count}")
    print(f"  bioicons_mitosis refs:    {used_mitosis}")
    print(f"  bioicons_chromosome refs: {used_chrom}")

    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG written: {out_png}  ({len(png):,} bytes)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
