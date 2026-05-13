"""
Analysis: round 8 — cell-cell adhesion (cadherin/gap-junction) + MMP-driven remodelling
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Rounds 5-7 covered cell-MATRIX adhesion (integrin + ECM proteins)
    but not cell-CELL adhesion (cadherin) and not matrix remodelling
    (MMPs). Round 8 closes both gaps:
      • cadherin (hand-written) — single transmembrane chain with 5 EC
        domains. Complements integrin (cell-matrix vs cell-cell).
      • mmp (hand-written) — Pac-Man enzyme with Zn²⁺ active site for
        matrix proteolysis.
      • bioicons_gap_junction (bundled) — completes the cell-cell
        junction trio (with tight_junction + desmosome from earlier).

    Two live prompts test each direction independently.

Judgment criteria:
    Test A — Epithelial cell-cell adhesion: output references `cadherin`
        ×2 (mirror-image pair) AND `bioicons_gap_junction`. Two cells
        shown facing each other.
    Test B — Tumor invasion / matrix remodelling: output references
        `mmp` AND `bioicons_collagen` with a visible cleavage. Optional:
        cancer cell shape.
    Vision critic: no HIGH-severity issues after refine passes.

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round8_adhesion_remodelling.py
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
    "cell_cell_adhesion": (
        "Epithelial cell-cell adhesion figure. Show two adjacent epithelial "
        "cells with their membranes facing each other (intercellular space "
        "between). Place a pair of cadherins (use the cadherin icon) on the "
        "facing membranes oriented so their EC1 heads meet in the middle of "
        "the intercellular space — this represents homophilic cadherin "
        "binding at an adherens junction. Also show a gap junction (use "
        "bioicons_gap_junction) on a different region of the same membrane "
        "pair to depict cell-cell communication. Label 'Adherens junction "
        "(cadherins)' and 'Gap junction (connexons)'. Title: 'Epithelial "
        "cell-cell adhesion: adherens junction + gap junction'."
    ),
    "tumor_matrix_remodelling": (
        "Tumor invasion / matrix remodelling figure. Show an extracellular "
        "matrix region with multiple horizontal collagen fibres (use "
        "bioicons_collagen, 3-4 fibres stacked). Place two MMP icons (use "
        "the mmp symbol) cleaving collagen fibres — draw a visible gap in "
        "the collagen at the MMP mouth position to depict the proteolytic "
        "cut. Label each MMP with 'MMP-9' and 'MMP-2' respectively. Add a "
        "small cell or cancer cell shape (use the kinase or generic_protein "
        "shape, labelled 'Tumor cell') invading through one of the cleaved "
        "regions. Title: 'Matrix remodelling: MMPs cleave collagen to "
        "enable cell invasion'."
    ),
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260512_bioicons_round8_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round8_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    NEW = {"cadherin", "mmp", "bioicons_gap_junction"}
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())}")
    for k, v in sorted(refs.items()):
        marker = " ←NEW" if k in NEW else ""
        print(f"    {k:30s} ×{v}{marker}")
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
