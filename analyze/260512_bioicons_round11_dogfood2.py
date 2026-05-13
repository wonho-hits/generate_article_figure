"""
Analysis: round 11 — second dogfood batch (3 new open prompts)
Date: 2026-05-12
Related: docs/progress/260512_bioicons_pilot.md

Problem:
    Round 10 dogfood verified catalog discovery + surfaced one
    architectural bug (use-dimensions). Round 11 expands the dogfood
    coverage with 3 prompts that exercise:
      • Cell biology (mitosis): does the LLM organically choose the
        5 per-stage wrappers over the composite?
      • Innate immunity (TLR signaling): cross-domain composition
        (receptor + signaling + nuclear TF).
      • Hormone signaling (insulin): metabolic pathway, different
        topology than MAPK.

    Same dogfood rules as round 10: no icon-name hints in prompts.

Judgment criteria:
    1. Catalog discovery: how many expected icons were picked, any
       ad-hoc primitive shapes filling library-coverable roles?
    2. Sizing compliance: does the use-dim patch from round 10b
       continue to produce correctly-sized symbols?
    3. Mitosis specific: does the LLM reach for `bioicons_mitosis_<stage>`
       wrappers (round 3 work) or fall back to the composite or to
       primitives?
    4. Vision critic pass-1 vs pass-2 outcomes.

Conclusion:
    [filled in after run]

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round11_dogfood2.py
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
    "mitosis_stages": (
        "Draw a figure showing the major stages of mitosis (interphase, "
        "prophase, prometaphase, metaphase, anaphase, telophase) in a "
        "single eukaryotic cell. Show each stage as a separate labelled "
        "panel arranged left-to-right. Title the figure 'Mitosis: stages "
        "of nuclear division'."
    ),
    "tlr_innate_immunity": (
        "Toll-like receptor 4 (TLR4) signaling in innate immunity. Bacterial "
        "lipopolysaccharide (LPS) binds TLR4 on the macrophage cell surface. "
        "TLR4 activates the kinase IKK in the cytoplasm. IKK phosphorylates "
        "and inactivates the inhibitor IκB, freeing NF-κB to translocate "
        "into the nucleus where it activates pro-inflammatory genes "
        "(IL-6, TNF-α). Show phosphorylation events. Label each component."
    ),
    "insulin_signaling": (
        "Insulin signaling pathway: insulin binds the insulin receptor "
        "(an RTK) on the cell membrane. The receptor recruits IRS-1, "
        "which activates PI3K. PI3K phosphorylates the membrane lipid "
        "PIP2 to PIP3. PIP3 recruits and activates AKT (kinase). "
        "Activated AKT phosphorylates downstream targets that mediate "
        "glucose uptake. Show the lipid second messenger conversion and "
        "the kinase cascade with phosphorylation badges. Label every "
        "component."
    ),
}

EXPECTED_HITS = {
    "mitosis_stages": {
        # Should ideally pick the per-stage wrappers, not the composite
        "bioicons_mitosis_interphase",
        "bioicons_mitosis_prophase",
        "bioicons_mitosis_prometaphase",
        "bioicons_mitosis_metaphase",
        "bioicons_mitosis_telophase",
    },
    "tlr_innate_immunity": {
        "ligand", "rtk", "kinase", "p_badge", "transcription_factor",
        "nucleus", "generic_protein",
    },
    "insulin_signaling": {
        "ligand", "rtk", "kinase", "p_badge",
        # PI3K and AKT are kinases; PIP2/PIP3 likely as dag-like or none
    },
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260512_bioicons_round11_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round11_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    expected = EXPECTED_HITS.get(name, set())
    found_expected = expected & refs.keys()
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  total <use> refs: {sum(refs.values())} ({len(refs)} unique)")
    print(f"  expected ∩ found: {sorted(found_expected)}")
    print(f"  expected MISSING: {sorted(expected - refs.keys())}")
    other = refs.keys() - expected
    if other:
        print(f"  other refs:       {sorted(other)}")
    print(f"  full ref count:")
    for k, v in sorted(refs.items()):
        marker = "  ←expected" if k in expected else ""
        print(f"    {k:35s} ×{v}{marker}")
    # Sizing check
    use_tags = re.findall(r"<use\b[^/]+/>", svg)
    missing_dims = [
        t for t in use_tags
        if not (re.search(r"\bwidth\s*=", t) and re.search(r"\bheight\s*=", t))
    ]
    if missing_dims:
        print(f"  ⚠ {len(missing_dims)} <use> tags MISSING dims (patch failure?):")
        for t in missing_dims[:3]:
            print(f"    {t}")
    else:
        print(f"  ✓ all {len(use_tags)} <use> tags have width+height")

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
