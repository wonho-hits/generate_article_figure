"""
Analysis: round 7 — deeper signaling + richer ECM
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Round 5-6 covered ECM with collagen + fibroblast + integrin, and
    signaling with TF/scaffold/small_gtpase. Two remaining gaps:
      • Generic ligand (LLM was drawing ad-hoc circles for "Growth
        factor", "EGF", etc.)
      • G-protein heterotrimer (αβγ) — distinct from generic complex
      • Other major matrix proteins beyond collagen: fibronectin,
        laminin, proteoglycan

    Added: ligand, g_protein_trimer (signaling); fibronectin, laminin,
    proteoglycan (ECM matrix proteins). All hand-written (bioicons has
    no named-form for any of these).

Judgment criteria:
    Test A — GPCR cascade: output references `ligand` AND `gpcr` AND
        `g_protein_trimer`. Each <use> labelled.
    Test B — Rich ECM panel: output references AT LEAST 3 of {collagen,
        fibronectin, laminin, proteoglycan} + integrin.
    Vision critic: no HIGH-severity issues after refine passes.

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round7_signaling_ecm.py
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
    "gpcr_cascade": (
        "GPCR signaling pathway figure. Show an extracellular ligand "
        "(use the ligand icon, labelled 'adrenaline') above a 7-helix "
        "GPCR (use gpcr) embedded in the cell membrane. Below the "
        "membrane in the cytoplasm, place the G-protein heterotrimer "
        "(use the g_protein_trimer icon) showing all three αβγ subunits. "
        "Then show adenylyl cyclase (kinase shape, labelled 'AC') "
        "producing cAMP (use camp). cAMP activates PKA (kinase, labelled "
        "'PKA') which phosphorylates a downstream target. Title: 'GPCR "
        "→ G-protein → adenylyl cyclase → cAMP → PKA cascade'."
    ),
    "rich_ecm": (
        "Rich extracellular matrix composition figure showing the full "
        "diversity of matrix proteins. Above the cell membrane (drawn as "
        "two horizontal lines) show: multiple collagen fibres (use "
        "bioicons_collagen, stacked), at least one fibronectin V-dimer "
        "(use fibronectin), one laminin cross (use laminin), and one "
        "proteoglycan (use proteoglycan). Show an integrin (use integrin) "
        "straddling the membrane and binding to the fibronectin. Below "
        "the membrane (cytoplasm) show actin (use bioicons_actin_filament) "
        "connected to the integrin's cytoplasmic tail via 'talin/"
        "vinculin'. Title: 'Extracellular matrix composition and "
        "cell-matrix adhesion'."
    ),
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260512_bioicons_round7_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round7_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())}")
    NEW = {"ligand", "g_protein_trimer", "fibronectin", "laminin", "proteoglycan"}
    print(f"  refs (NEW marked):")
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
