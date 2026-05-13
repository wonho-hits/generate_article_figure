"""
Analysis: round 16 — release-readiness comprehensive dogfood
Date: 2026-05-13
Related: docs/progress/260512_bioicons_pilot.md

After 15 rounds of expansion + verification, this is the final wide-
sweep dogfood. Four prompts spanning domains the prior rounds did NOT
exercise densely:
  • Wnt/β-catenin — TF-translocation cascade different from MAPK
  • Phagocytosis — vesicle trafficking + cell biology mix
  • Steroid hormone (nuclear receptor) — no membrane receptor pathway
  • EMT (epithelial → mesenchymal) — multi-system: adhesion + matrix +
    signaling

All prompts describe biology without naming icons. Pure dogfood.

Goal: stress-test whether the 81-symbol library covers enough biology
for arbitrary publication figures, and whether the 4 architectural
fixes + 3 prompt patterns continue to produce clean output at scale.

Usage:
    PYTHONPATH=. uv run python analyze/260513_bioicons_round16_release_dogfood.py
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
    "wnt_signaling": (
        "Wnt/β-catenin signaling pathway. Wnt ligand binds the Frizzled "
        "receptor on the cell membrane. This inhibits the destruction "
        "complex (containing APC, Axin, GSK-3β kinase), so β-catenin "
        "accumulates in the cytoplasm. β-catenin then translocates into "
        "the nucleus and forms a complex with TCF/LEF transcription "
        "factors to activate target genes (Myc, cyclin D1). Show the "
        "membrane, cytoplasm, nucleus compartments and label each "
        "component. Title the figure."
    ),
    "phagocytosis": (
        "Macrophage phagocytosis of a bacterium. Show a macrophage cell "
        "engulfing a bacterial pathogen at its plasma membrane through "
        "pseudopod extension; the bacterium ends up inside a phagosome "
        "vesicle within the cytoplasm. The phagosome then fuses with a "
        "lysosome whose acidic enzymes digest the bacterium. Label the "
        "key stages (recognition, engulfment, phagosome formation, "
        "phagolysosome maturation, degradation) and add a figure title."
    ),
    "steroid_hormone": (
        "Steroid hormone signaling pathway. A lipophilic steroid hormone "
        "(e.g. cortisol) crosses the cell membrane directly by diffusion "
        "(it does NOT need a surface receptor). Inside the cytoplasm it "
        "binds a nuclear receptor (e.g. glucocorticoid receptor). The "
        "hormone-receptor complex translocates into the nucleus, binds "
        "specific DNA response elements (HRE), and activates gene "
        "transcription. Show the lipid bilayer membrane (no surface "
        "receptor), cytoplasm with hormone-receptor binding, nucleus "
        "with DNA-binding event, and downstream gene expression. Title "
        "the figure."
    ),
    "emt_transition": (
        "Epithelial-to-mesenchymal transition (EMT) figure. Show two "
        "states side-by-side. LEFT panel: an epithelial cell that "
        "expresses E-cadherin at its lateral membrane (forming adherens "
        "junctions with a neighbouring epithelial cell) and sits on a "
        "basement membrane via hemidesmosomes; the cell has organised "
        "actin cytoskeleton. RIGHT panel: the SAME cell after EMT — it "
        "has LOST E-cadherin (junctions gone, cells separated), secretes "
        "MMPs that cleave the basement membrane, and now has motile "
        "morphology with extended actin filaments suggesting migration "
        "into the underlying stroma (collagen fibres). Label the key "
        "differences between the two states. Title: 'Epithelial-"
        "mesenchymal transition (EMT)'."
    ),
}

EXPECTED = {
    "wnt_signaling": {
        "ligand", "kinase", "transcription_factor", "nucleus",
    },
    "phagocytosis": {
        "bioicons_endocytosis",  # closest icon for phagocytic engulfment
    },
    "steroid_hormone": {
        "ligand", "transcription_factor", "nucleus", "lipid_bilayer",
    },
    "emt_transition": {
        "cadherin", "integrin", "hemidesmosome", "basement_membrane",
        "mmp", "bioicons_collagen", "bioicons_actin_filament",
    },
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260513_bioicons_round16_{name}.svg"
    out_png = OUT_DIR / f"260513_bioicons_round16_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    expected = EXPECTED.get(name, set())
    found = expected & refs.keys()
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())} ({len(refs)} unique)")
    print(f"  expected ∩ found: {len(found)}/{len(expected)}")
    print(f"    found:   {sorted(found)}")
    print(f"    missing: {sorted(expected - refs.keys())}")
    print(f"  all refs:")
    for k, v in sorted(refs.items()):
        marker = " ←expected" if k in expected else ""
        print(f"    {k:32s} ×{v}{marker}")
    # Sizing check
    use_tags = re.findall(r"<use\b[^/]+/>", svg)
    missing_dims = [
        t for t in use_tags
        if not (re.search(r"\bwidth\s*=", t) and re.search(r"\bheight\s*=", t))
    ]
    if missing_dims:
        print(f"  ⚠ {len(missing_dims)} <use> tags MISSING dims!")
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
