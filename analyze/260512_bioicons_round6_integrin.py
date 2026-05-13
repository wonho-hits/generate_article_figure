"""
Analysis: round 6 — integrin + cytoskeleton (ECM↔cell signaling)
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Round 5 added bioicons ECM (collagen, fibroblast, junctions) and
    hand-written signaling extensions. The remaining gap: how does a
    cell SENSE its matrix? That's the integrin family. Bioicons.com has
    no integrin/focal-adhesion icons, so round 6 hand-writes integrin
    and bundles cytoskeleton (microtubule, actin_filament) to complete
    the ECM↔cell bridge.

    Does the LLM compose a clean ECM↔cell signaling figure using all
    these new pieces?

Judgment criteria:
    1. Output references `integrin` AND `bioicons_actin_filament` AND
       `bioicons_collagen` — the full ECM↔cell bridge.
    2. Integrin straddles the membrane (placement test).
    3. Each <use> has a relevant label.
    4. Vision critic: no HIGH-severity issues after refine passes.

Conclusion:
    [filled in after run]

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round6_integrin.py
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
    "Cell-ECM signaling figure showing how an integrin connects "
    "extracellular collagen to the intracellular actin cytoskeleton. "
    "Show: collagen fibres in the extracellular space (above the "
    "membrane); an integrin (αβ heterodimer) straddling the cell "
    "membrane with its head bound to collagen; actin filaments inside "
    "the cytoplasm connected to the integrin's cytoplasmic tail "
    "(label the connector as 'talin/vinculin'). Add the labels "
    "'Extracellular', 'Cytoplasm', and 'ECM' in the appropriate "
    "regions. Title the figure 'Integrin: bridging the extracellular "
    "matrix to the cytoskeleton'."
)


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260512_bioicons_round6_integrin.svg"
    out_png = OUT_DIR / "260512_bioicons_round6_integrin.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())}")
    print(f"  unique symbols:")
    for k, v in sorted(refs.items()):
        marker = "←NEW" if k in ("integrin", "bioicons_actin_filament",
                                   "bioicons_microtubule") else ""
        print(f"    {k:30s} ×{v}  {marker}")
    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG: {out_png.name}  ({len(png):,} B)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


if __name__ == "__main__":
    asyncio.run(main())
