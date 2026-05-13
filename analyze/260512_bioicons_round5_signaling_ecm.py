"""
Analysis: round 5 — signaling pathway + ECM expansion
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Library covers cell-division well after rounds 1-4. User asked for
    expansion in two directions:
      • Signaling pathway figures (specific named proteins like TFs,
        scaffolds, GTPases)
      • ECM (collagen, fibroblasts, junctions)

    Bioicons.com has rich ECM content (Servier Tissues category) but no
    named signaling proteins (only generic membrane shapes we already
    cover). So we added 5 ECM icons from bioicons + 3 hand-written
    signaling symbols (transcription_factor, scaffold_protein, small_gtpase).

    Does the LLM reach for the new icons when the prompt fits?

Judgment criteria (per prompt):
    1. Signaling prompt: at least one of the 3 new signaling symbols used.
    2. ECM prompt: at least one of the 5 ECM bioicons used.
    3. Each <use> co-located with relevant label.
    4. Vision critic: no HIGH-severity layout issues after refine passes.

Conclusion:
    [filled in after run]

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round5_signaling_ecm.py
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
    "signaling": (
        "MAPK signaling pathway figure. Start at an RTK receptor in the cell "
        "membrane bound by a growth factor ligand. Below the membrane show "
        "the Ras small GTPase (use the small_gtpase icon, labelled 'Ras'). "
        "Ras activates Raf (use kinase). Raf phosphorylates MEK (kinase). "
        "MEK phosphorylates ERK (kinase). Activated ERK translocates into "
        "the nucleus where it activates a transcription factor (use the "
        "transcription_factor icon, labelled 'ELK-1'). Show phosphorylation "
        "events with the p_badge symbol on each downstream kinase. Title: "
        "'MAPK signaling cascade: from ligand to gene expression'."
    ),
    "ecm": (
        "Extracellular matrix figure. Show a fibroblast cell on the left "
        "secreting collagen fibres into the matrix space on the right. Use "
        "the fibroblast icon for the cell and multiple horizontal collagen "
        "fibres filling the matrix area (use the bioicons_collagen symbol, "
        "stacked vertically with small gaps). Show a tight-junction between "
        "two epithelial cells at the top of the figure to indicate barrier "
        "tissue context. Label the major elements (Fibroblast, Collagen "
        "fibres, ECM, Tight junction). Title: 'Extracellular matrix: "
        "fibroblast secretes collagen into the matrix space'."
    ),
}


def _summary(svg: str) -> dict:
    refs = re.findall(r'href="#([A-Za-z_][\w-]*)"', svg)
    counts = Counter(refs)
    return {
        "svg_bytes": len(svg),
        "use_ref_total": sum(counts.values()),
        "ref_counts": dict(counts),
    }


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260512_bioicons_round5_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round5_{name}.png"
    out_svg.write_text(svg)
    s = _summary(svg)
    print(f"SVG written: {out_svg.name}  ({s['svg_bytes']:,} B)")
    print(f"  total <use> refs: {s['use_ref_total']}")
    # Filter to the ones that matter for this prompt
    interesting = sorted(
        (k, v) for k, v in s["ref_counts"].items()
        if k in (
            "transcription_factor", "scaffold_protein", "small_gtpase",
            "bioicons_collagen", "bioicons_collagen_3d", "bioicons_fibroblast",
            "bioicons_tight_junction", "bioicons_desmosome",
        )
        or k.startswith(("gpcr", "rtk", "kinase", "p_badge", "nucleus"))
    )
    print(f"  relevant refs:")
    for k, v in interesting:
        print(f"    {k}: {v}")
    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
        print(f"PNG written: {out_png.name}  ({len(png):,} B)")
    except Exception as exc:
        print(f"  [render fail] {exc}")


async def main() -> None:
    for name, prompt in PROMPTS.items():
        await run_one(name, prompt)


if __name__ == "__main__":
    asyncio.run(main())
