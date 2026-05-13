"""
Analysis: bioicons round 2 — meiosis prompt + fertilization-to-cleavage
Date: 2026-05-12
Related progress log: docs/progress/260512_bioicons_pilot.md

Problem:
    After round 1 added bioicons_mitosis (single composite) we added 3 more
    icons: bioicons_meiosis, bioicons_zygote, bioicons_embryo_2cell.
    Lazy injection means scaling the bundled set is now cheap.

    Two prompts test whether Gemini reaches for the right new icon:
    (A) "Show the stages of meiosis (8 stages, both divisions)" — should
        pick `bioicons_meiosis`, not `bioicons_mitosis`.
    (B) "Fertilization figure showing sperm meeting egg, then zygote with
        two pronuclei, then 2-cell embryo after first cleavage" — should
        pick `bioicons_zygote` and `bioicons_embryo_2cell` from the
        Xi-Chen set.

Judgment criteria:
    1. Each output references its target bioicons_* symbol(s).
    2. Each rasterised PNG shows recognisable subject matter.
    3. Lazy injection works: the <defs> block in each output carries
       ONLY the symbols actually referenced (verified by parsing).
    4. Total cost stays bounded — each prompt under ~$0.01 in API spend.

Conclusion:
    [filled in after run]

Usage:
    PYTHONPATH=. uv run python analyze/260512_bioicons_round2_live.py
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from app.tools.svg_render import rasterize_svg
from app.tools.vector_schematic import generate_vector_schematic

OUT_DIR = Path(__file__).resolve().parent

PROMPTS = {
    "meiosis": (
        "Show the stages of meiosis in a single eukaryotic cell, including "
        "both meiosis I (homolog separation) and meiosis II (sister chromatid "
        "separation). Label each major stage with its name (prophase I, "
        "metaphase I, anaphase I, telophase I, prophase II, metaphase II, "
        "anaphase II, telophase II). Title the figure 'Meiosis: phases of "
        "reductional and equational division'."
    ),
    "fertilization": (
        "Fertilization-to-cleavage figure. Show three panels left to right: "
        "(1) sperm meeting egg, (2) zygote (1-cell embryo) with two visible "
        "pronuclei inside the zona pellucida, (3) 2-cell embryo after the "
        "first cleavage division. Label each panel and add a title "
        "'Early mammalian development: fertilization to first cleavage'."
    ),
}


def _summarise(name: str, svg: str) -> dict:
    use_refs = set(re.findall(r'href="#([A-Za-z_][\w-]*)"', svg))
    bioicons_refs = sorted(r for r in use_refs if r.startswith("bioicons_"))
    # Top-level <defs> contents — count which symbols were lazily injected.
    defs_match = re.search(
        r"<svg[^>]*>\s*(<defs[^>]*>.*?</defs>)", svg, re.DOTALL
    )
    injected = sorted(
        re.findall(r'<symbol id="(bioicons_[\w_]+)"', defs_match.group(1))
        if defs_match
        else []
    )
    return {
        "svg_bytes": len(svg),
        "use_refs_total": len(use_refs),
        "bioicons_refs": bioicons_refs,
        "bioicons_injected": injected,
        "defs_size": len(defs_match.group(1)) if defs_match else 0,
    }


async def run_one(name: str, prompt: str) -> None:
    svg = await generate_vector_schematic(prompt, max_refine_passes=2)
    summary = _summarise(name, svg)

    out_svg = OUT_DIR / f"260512_bioicons_round2_{name}.svg"
    out_png = OUT_DIR / f"260512_bioicons_round2_{name}.png"
    out_svg.write_text(svg)
    try:
        png = rasterize_svg(svg, width=1600)
        out_png.write_bytes(png)
    except Exception as exc:
        print(f"  [{name} render fail] {exc}")
    print(f"[{name}] {out_svg.name}")
    print(f"  SVG: {summary['svg_bytes']:,} B  |  defs: {summary['defs_size']:,} B")
    print(f"  <use> refs total: {summary['use_refs_total']}")
    print(f"  bioicons referenced: {summary['bioicons_refs']}")
    print(f"  bioicons in <defs>:  {summary['bioicons_injected']}")
    print()


async def main() -> None:
    # Sequential rather than parallel: we want the rate-limit headroom and
    # the log streams readable.
    for name, prompt in PROMPTS.items():
        print(f"==== {name} ====")
        await run_one(name, prompt)


if __name__ == "__main__":
    asyncio.run(main())
