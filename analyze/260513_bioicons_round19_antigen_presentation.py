"""
Analysis: round 19 — immunology dogfood (T-cell activation via MHC-II)
Date: 2026-05-13
Related: docs/progress/260512_bioicons_pilot.md

Round 19 adds 5 immunology symbols: 4 bundled (antibody, t_lymphocyte,
b_lymphocyte, macrophage) + 1 hand-written (mhc_complex). Together
they cover the canonical immune-synapse figure: APC presenting peptide
via MHC to a TCR on a T-cell, plus antibody-response figures.

Open prompt asking for antigen presentation. No icon hints — pure
dogfood.

Usage:
    PYTHONPATH=. uv run python analyze/260513_bioicons_round19_antigen_presentation.py
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
    "Antigen presentation and T-cell activation figure. A macrophage on the "
    "left has phagocytosed and processed a bacterial protein. It now "
    "displays a short peptide fragment of the antigen in the groove of a "
    "MHC class II molecule on its surface. A CD4+ helper T lymphocyte on "
    "the right approaches and its T-cell receptor (TCR) recognises and "
    "binds the peptide-MHC-II complex (this is the immune synapse). After "
    "TCR engagement the T cell becomes activated and produces cytokines. "
    "Label the macrophage (APC), the MHC-II + bacterial peptide, the T "
    "cell (CD4+), the TCR, and the cytokine release. Title the figure "
    "'Antigen Presentation & T-cell Activation'."
)

EXPECTED = {
    "bioicons_macrophage", "bioicons_t_lymphocyte", "mhc_complex",
}


async def main() -> None:
    svg = await generate_vector_schematic(PROMPT, max_refine_passes=2)
    out_svg = OUT_DIR / "260513_bioicons_round19_antigen_presentation.svg"
    out_png = OUT_DIR / "260513_bioicons_round19_antigen_presentation.png"
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
