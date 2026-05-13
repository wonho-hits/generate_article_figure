"""
Analysis: round 9 — vesicle trafficking + apoptosis + BM anchoring
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Round 9 adds 5 more icons spanning signaling/ECM gaps:
- `bioicons_endocytosis` (bundled): vesicle budding from membrane
- `bioicons_ribosome` (bundled): translation machinery
- `caspase` (hand-written): apoptosis protease (purple, distinct from MMP)
- `hemidesmosome` (hand-written): cell ↔ BM junction
- `basement_membrane` (hand-written): two-layer sheet

Two live prompts:
  A. Receptor-mediated endocytosis → translation cascade.
  B. Apoptosis cascade triggered by extrinsic ligand (Fas).
  (Live BM-anchoring test deferred — already covered in smoke render.)

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round9_endo_apop.py
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
    "endocytosis_translation": (
        "Receptor-mediated endocytosis figure followed by gene expression. "
        "Show an extracellular ligand (use ligand, labelled 'EGF') binding "
        "to an RTK receptor on the cell membrane. Below show the "
        "internalisation step using the bioicons_endocytosis icon. From the "
        "internalised signal draw an arrow into the nucleus where a "
        "transcription_factor (labelled 'Egr-1') activates a gene; the gene "
        "produces mRNA shown by the bioicons_ribosome icon translating it "
        "into protein in the cytoplasm. Label the protein 'EGR1 target'. "
        "Title: 'Receptor endocytosis → transcription → translation'."
    ),
    "apoptosis_cascade": (
        "Apoptotic signaling cascade triggered by extrinsic death-receptor "
        "ligand. Show a ligand (use ligand, labelled 'FasL') binding to a "
        "death receptor (use rtk shape, labelled 'Fas'). Below the membrane "
        "in the cytoplasm show initiator caspase (use caspase, labelled "
        "'Caspase-8'). Caspase-8 activates executioner caspase (use caspase "
        "again, labelled 'Caspase-3'). Caspase-3 cleaves a substrate "
        "(use generic_protein, labelled 'PARP') leading to apoptotic DNA "
        "fragmentation. Title: 'Extrinsic apoptosis: Fas → caspase cascade "
        "→ substrate cleavage'."
    ),
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260512_bioicons_round9_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round9_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    NEW = {"caspase", "hemidesmosome", "basement_membrane",
           "bioicons_endocytosis", "bioicons_ribosome"}
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
