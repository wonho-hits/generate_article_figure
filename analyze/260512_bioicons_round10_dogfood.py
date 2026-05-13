"""
Analysis: round 10 — DOGFOOD (open prompts, no icon-name hints)
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Rounds 1-9 expanded the library to 75 symbols and verified each
    expansion with live tests. But every live prompt so far had
    explicit icon-name hints ("use the ligand icon, labelled X"). That
    tests whether the icon RENDERS, not whether the LLM DISCOVERS it
    from the catalog.

    Round 10 dogfoods: three open prompts that describe biology
    naturally — no `<use href=...>` hints, no "use the X icon" phrases.
    Whatever icons the LLM picks comes purely from reading the
    advertised catalog in the system prompt.

Judgment criteria (per prompt):
    1. Icon-coverage: count <use> refs and check which were library
       icons vs ad-hoc primitive drawings.
    2. Domain-fit: did the LLM pick the right SHAPE for each biological
       role? (e.g. rtk for EGFR, not gpcr)
    3. Vision-critic outcome: report pass-1 and pass-2 severity.
    4. Visual quality on render: any glaring gaps where the LLM had to
       hand-draw a shape that we already have an icon for? That's a
       prompt-tuning gap (catalog isn't being discovered) rather than a
       library gap.

Conclusion:
    [filled in after run]

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round10_dogfood.py
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

# IMPORTANT: prompts must NOT mention specific icon IDs. Describe the
# biology naturally and let the LLM pick from the catalog.
PROMPTS = {
    "mapk_from_egf": (
        "Draw a clear pathway figure of MAPK signaling: EGF binds EGFR on "
        "the cell surface, activating the Ras-Raf-MEK-ERK kinase cascade. "
        "Activated ERK enters the nucleus and turns on a transcription "
        "factor that drives gene expression. Show phosphorylation events "
        "at each kinase step. Label each component."
    ),
    "cancer_invasion": (
        "Cancer-cell invasion through the extracellular matrix. A tumor "
        "cell sits in an ECM rich in collagen fibres. The tumor cell "
        "secretes proteases that cleave the collagen, opening a path for "
        "the cell to migrate through. Show the proteolytic cleavage "
        "explicitly (broken collagen fibres at the cleavage points) and "
        "label the proteases. Add a small movement arrow showing where "
        "the cell will migrate. Title the figure."
    ),
    "intrinsic_apoptosis": (
        "Intrinsic (mitochondrial) apoptosis pathway. Cellular stress "
        "(DNA damage, ROS) activates p53. p53 induces pro-apoptotic Bcl-2 "
        "family proteins that permeabilize the mitochondrial outer "
        "membrane. Cytochrome c is released from the mitochondrion into "
        "the cytoplasm. Released cytochrome c activates a caspase cascade "
        "(initiator caspase-9 → executioner caspase-3) which cleaves "
        "substrates and triggers cell death. Show the mitochondrion and "
        "label every step."
    ),
}

# Library icons we expect to be relevant for each prompt — used only to
# score the run, NOT shown to the LLM.
EXPECTED_HITS = {
    "mapk_from_egf": {
        "ligand", "rtk", "small_gtpase", "kinase", "p_badge", "nucleus",
        "transcription_factor",
    },
    "cancer_invasion": {
        "bioicons_collagen", "mmp", "fibronectin", "laminin",
        "proteoglycan",
    },
    "intrinsic_apoptosis": {
        "mitochondrion", "caspase", "generic_protein", "transcription_factor",
    },
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260512_bioicons_round10_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round10_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    expected = EXPECTED_HITS[name]
    found_expected = expected & refs.keys()
    unexpected_uses = refs.keys() - expected
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs:  {sum(refs.values())} ({len(refs)} unique)")
    print(f"  expected ∩ found:  {sorted(found_expected)}")
    print(f"  expected MISSING:  {sorted(expected - refs.keys())}")
    print(f"  unexpected hits:   {sorted(unexpected_uses)}")
    print(f"  full ref count:")
    for k, v in sorted(refs.items()):
        print(f"    {k:30s} ×{v}")
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
