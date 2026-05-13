"""
Analysis: round 17 — verify round-16 catalog description fixes
Date: 2026-05-13
Related: docs/progress/260512_bioicons_pilot.md

Round 16 dogfood exposed TWO catalog-description gaps:
  1. `bioicons_endocytosis` `use_when` didn't mention phagocytosis,
     so the LLM drew phagocytosis from primitives instead of using
     the icon.
  2. `ligand` `use_when` focused on peptide growth factors / cytokines
     and didn't reach for steroid hormones, so the steroid-hormone
     dogfood missed the `ligand` icon.

Both descriptions were extended in commit 027681e (endocytosis) and
in this round (ligand). Round 17 verifies the fixes work — re-runs
the SAME two prompts that exposed the gaps.

Expected outcome:
  • Phagocytosis prompt now references `bioicons_endocytosis` ≥ 1×
    (round 16: 0 refs).
  • Steroid-hormone prompt now references `ligand` ≥ 1×
    (round 16: 0 refs).

Usage:
    PYTHONPATH=. uv run python analyze/260513_bioicons_round17_verify_descriptions.py
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
    "phagocytosis_v2": (
        "Macrophage phagocytosis of a bacterium. Show a macrophage cell "
        "engulfing a bacterial pathogen at its plasma membrane through "
        "pseudopod extension; the bacterium ends up inside a phagosome "
        "vesicle within the cytoplasm. The phagosome then fuses with a "
        "lysosome whose acidic enzymes digest the bacterium. Label the "
        "key stages (recognition, engulfment, phagosome formation, "
        "phagolysosome maturation, degradation) and add a figure title."
    ),
    "steroid_hormone_v2": (
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
}

# Target icons whose discovery we're verifying.
TARGETS = {
    "phagocytosis_v2": "bioicons_endocytosis",
    "steroid_hormone_v2": "ligand",
}


async def run_one(name: str, prompt: str) -> None:
    print(f"\n==== {name} ====")
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    out_svg = OUT_DIR / f"260513_bioicons_round17_{name}.svg"
    out_png = OUT_DIR / f"260513_bioicons_round17_{name}.png"
    out_svg.write_text(svg)

    refs = Counter(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    target = TARGETS[name]
    found = refs.get(target, 0)
    print(f"SVG: {out_svg.name}  ({len(svg):,} B)")
    print(f"  target `{target}` discovered: {found}× (round 16: 0×)")
    print(f"  ✓ FIXED" if found > 0 else "  ✗ Still not discovered")
    print(f"  all refs:")
    for k, v in sorted(refs.items()):
        marker = " ←TARGET" if k == target else ""
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
