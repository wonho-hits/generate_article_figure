"""
Analysis: round 20 — final cross-domain dogfood
Date: 2026-05-13
Related: docs/progress/260512_bioicons_pilot.md

After 19 rounds of expansion + verification, the library covers 13
biological domains. Round 20 tests whether icons from MULTIPLE
domains compose coherently in one figure — the real test of library
maturity.

Three prompts that each span 2-4 domains:

1. CAR-T therapy — cancer + immune
   Icons: bioicons_t_lymphocyte, bioicons_cancer_cell, generic_membrane_protein
   (CAR), ligand, caspase

2. Tumor immune microenvironment — cancer + ECM + immune
   Icons: bioicons_tumor / bioicons_cancer_cell, bioicons_macrophage,
   bioicons_t_lymphocyte, bioicons_fibroblast, bioicons_collagen, mmp

3. Wound healing / fibrosis — ECM + immune + cell biology
   Icons: bioicons_macrophage, bioicons_fibroblast, bioicons_collagen,
   ligand (growth factors), mmp, bioicons_actin_filament

All prompts describe biology WITHOUT mentioning specific icon names.

Usage:
    PYTHONPATH=. uv run python analyze/260513_bioicons_round20_cross_domain_dogfood.py
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
    "car_t_therapy": (
        "CAR-T cell therapy figure. Show a genetically-engineered CD8+ "
        "cytotoxic T cell expressing a chimeric antigen receptor (CAR) on "
        "its surface. The CAR recognises a tumor-specific antigen on a "
        "cancer cell. When the CAR binds the tumor antigen, the T cell "
        "releases cytotoxic granules (perforin / granzyme) that induce "
        "apoptosis in the cancer cell via the caspase cascade. Label the "
        "T cell, the CAR, the cancer cell, the tumor antigen, the "
        "cytotoxic granules, and the caspase-induced cell death. Title "
        "the figure."
    ),
    "tumor_microenvironment": (
        "Tumor microenvironment figure. Show a tumor mass at the centre, "
        "surrounded by: (1) fibroblasts secreting collagen fibres into the "
        "extracellular matrix (these are 'cancer-associated fibroblasts' "
        "or CAFs), (2) tumor-associated macrophages infiltrating the "
        "stroma, (3) T lymphocytes attempting immune surveillance, (4) "
        "matrix metalloproteinases (MMPs) cleaving the collagen to enable "
        "tumor invasion. Label each cell type and matrix component. Title "
        "'The tumor microenvironment: stromal, immune, and matrix "
        "interactions'."
    ),
    "wound_healing": (
        "Wound healing figure showing the proliferative phase. Show: (1) "
        "macrophages cleaning the wound site by phagocytosing debris and "
        "secreting growth factors, (2) fibroblasts attracted by these "
        "growth factors migrating into the wound, (3) fibroblasts then "
        "depositing new collagen fibres to rebuild the extracellular "
        "matrix, (4) the new collagen aligned to restore tissue integrity. "
        "Add arrows to indicate migration / secretion direction. Label "
        "each cell type, growth factors, and matrix components. Title "
        "'Wound healing: proliferative phase'."
    ),
}

EXPECTED = {
    "car_t_therapy": {
        "bioicons_t_lymphocyte", "bioicons_cancer_cell", "caspase",
    },
    "tumor_microenvironment": {
        "bioicons_tumor", "bioicons_fibroblast", "bioicons_collagen",
        "bioicons_macrophage", "bioicons_t_lymphocyte", "mmp",
    },
    "wound_healing": {
        "bioicons_macrophage", "bioicons_fibroblast", "bioicons_collagen",
        "ligand",
    },
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260513_bioicons_round20_{name}.svg"
    out_png = OUT_DIR / f"260513_bioicons_round20_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    expected = EXPECTED[name]
    found = expected & refs.keys()
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  expected ∩ found: {len(found)}/{len(expected)}")
    print(f"    found:   {sorted(found)}")
    print(f"    missing: {sorted(expected - refs.keys())}")
    other = refs.keys() - expected
    if other:
        print(f"    other:   {sorted(other)}")
    print(f"  full refs:")
    for k, v in sorted(refs.items()):
        marker = " ←expected" if k in expected else ""
        print(f"    {k:32s} ×{v}{marker}")
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
