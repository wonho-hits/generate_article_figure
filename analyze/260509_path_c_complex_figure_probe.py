"""
Analysis: Path C (Nano Banana 2) probe — can it one-shot a BioRender-style
          tumor microenvironment figure?
Date: 2026-05-09
Related progress log: docs/progress/260509_path_c_probe.md

Problem:
    Path A (LLM → SVG, validated in step 2) cannot produce stylized cell
    illustrations like the user-provided BioRender example: tumor cluster
    with mutation markers, M1/M2 macrophages with morphology, monocyte,
    dendritic cell with dendrites, MDSC, fibroblast, CD8+ T cell, plus
    cytokines (GM-CSF, IL-10) and inhibition/activation arrows.

    Question: can Path C (Gemini Image generation, model
    gemini-3.1-flash-image-preview a.k.a. Nano Banana 2) one-shot this
    class of figure with publication quality, or is curated symbol-library
    composition (Step 9) mandatory?

    Decision matters because:
    - ADOPT Path C → Step 5 (raster) + Step 6 (bg removal) jump to priority.
      Step 9 (symbol library) becomes optional refinement.
    - REJECT Path C → Step 9 mandatory. Path C reserved for atmospheric/
      textural figures only.
    - HYBRID → both paths needed; orchestrator routes by figure type.

Judgment Criteria (0/1/2 per axis, max 8):
    1. Cell identification — are M1/M2 macrophages, monocyte, dendritic cell,
       MDSC, fibroblast, T cell, cancer cluster all visually distinguishable
       and morphologically plausible?
    2. Schematic clarity — arrows present and directional? activation vs
       inhibition (⊣) visually distinct? cytokine bubbles drawn?
    3. Label legibility — KRAS G12D, BRAF V600E, p53 loss, GM-CSF, IL-10,
       polarization labels, cell type names — readable, not garbled?
    4. Layout / publication-readiness — white background, balanced
       composition, no watermarks, no extraneous borders or noise?

    Threshold:
    - ≥ 6  → ADOPT (Path C primary for these figures)
    - 3-5 → HYBRID (Path C draft + manual or symbol-library refinement)
    - ≤ 2 → REJECT (Step 9 mandatory)

Conclusion:
    SCORE 6/8 → ADOPT.

    Single-shot output quality is surprisingly close to the user-provided
    BioRender reference. All seven cell types rendered with correct
    morphology and visual differentiation. Text labels are crisp and
    grammatically correct (a historic weak spot of image models — Nano
    Banana 2 has cleared this bar). Pill-shaped mutation badges
    (KRAS G12D, BRAF V600E) emerged without explicit instruction.

    Defects are LOCAL and FIXABLE:
    - CD8+ T cell rendered TWICE (top-right + middle-right). One must be
      painted out. Inpainting is exactly the workflow to fix this.
    - Duplicate "M1 polarization" label appears below M2 macrophage.
      Same fix.
    - Cytokine "p53 loss" arrow direction is slightly ambiguous vs. the
      reference (cancer cluster as source vs. target).

    Implications for build order:
    - Step 5 (Path C raster) — bumped to primary path for complex
      multi-cell illustrative figures. Less custom work than expected
      because the model already produces near-final quality.
    - Step 7 (inpainting / region redraw) — promoted in priority. Path C
      outputs have small fixable defects (duplicate elements, mislabeled
      arrows) that need surgical correction. This is now load-bearing.
    - Step 9 (curated symbol library) — DEMOTED to optional. Path C alone
      is sufficient for v1; symbol-library composition is a future
      consistency/reuse refinement, not a prerequisite.

    Risks:
    - One sample. Stochastic. Variance on other prompts unknown.
    - Defect rate unknown — duplicate-element error frequency needs
      measurement over a larger prompt set. Recommend a follow-up probe
      with 5+ varied prompts before fully committing build order.
    - Editability constraint: raster can be inpainted but not vector-edited.
      For figures where users need to drag boxes / change colors, Path A
      remains preferred. The orchestrator's router (Step 5+) must classify
      "schematic" vs. "illustrative" requests reliably.

Usage:
    uv run python analyze/260509_path_c_complex_figure_probe.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=True)

from app.clients.gemini import GeminiClient  # noqa: E402


PROMPT = """Create a publication-quality scientific figure of the tumor microenvironment in BioRender illustration style. Clean white background, soft pastel cell colors with subtle shading, black labels, clean black arrows with rounded heads, no decorative borders.

Composition (left to right, top to bottom):

1. LEFT — Monocyte (yellow, with a kidney-shaped nucleus). Two dashed curved arrows leave the monocyte:
   - Upper dashed arrow → an M1 macrophage (red/orange, mildly amoeboid with small protrusions). Label this transition: "M1 polarization (inflammatory)".
   - Lower dashed arrow → an M2 macrophage (blue/teal, mildly amoeboid). Label this transition: "M2 polarization (anti-inflammatory)".

2. CENTER — A dense cluster of irregular overlapping cancer cells in pink and purple tones (organic, slightly translucent, with subtle shading suggesting depth). Above the cluster: label "Cancer cells". Two mutation tags on or near the cluster: "KRAS G12D" (upper part) and "BRAF V600E" (lower part). A solid horizontal arrow enters the cluster from the M2 macrophage region, labeled "p53 loss".

3. TOP RIGHT — A curved solid arrow from the cancer cluster going up-and-right, labeled "GM-CSF" (drawn as a few small circular molecule dots near the label), pointing to an MDSC (tan, multi-lobed irregular cell). The MDSC then has an INHIBITION line (line ending in a perpendicular bar ⊣) pointing right to a CD8+ T cell.

4. RIGHT — A green CD8+ T cell (round, smooth, with a darker green nucleus). Label: "CD8+ T cell". This T cell receives THREE incoming connections:
   - Inhibition from MDSC (perpendicular-bar end, from above-left).
   - Solid activation arrow from the cancer cluster (direct, from left).
   - Solid activation arrow from the fibroblast (from below-left).

5. BOTTOM RIGHT — A curved solid arrow from the cancer cluster going down-and-right, labeled "IL-10" (small molecule dots near the label), pointing to a tan dendritic cell drawn with multiple spiky dendrites. Below or beside the dendritic cell, an elongated brown fibroblast (spindle-shaped). A solid arrow from the cancer cluster also reaches the fibroblast.

Quality requirements:
- All labels in clean sans-serif, black, readable.
- Arrows are crisp, no fuzzy edges.
- Cells morphologically distinct from each other.
- Layout balanced, no element clipped.
- Pure white background, no shadows under elements.
"""


async def main() -> None:
    print("=" * 70)
    print("[probe] Path C complex-figure probe")
    print(f"[probe] model: gemini-3.1-flash-image-preview (Nano Banana 2)")
    print(f"[probe] prompt length: {len(PROMPT)} chars / ~{len(PROMPT.split())} words")
    print("=" * 70)

    client = GeminiClient()
    t0 = time.time()
    try:
        image_bytes = await client.generate_image(PROMPT)
    except Exception as exc:
        print(f"[probe] FAILED: {type(exc).__name__}: {exc}")
        raise
    elapsed = time.time() - t0

    out_dir = Path("/tmp")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    png_path = out_dir / f"path_c_probe_{timestamp}.png"
    stable_path = out_dir / "path_c_probe_latest.png"
    meta_path = out_dir / f"path_c_probe_{timestamp}.json"

    png_path.write_bytes(image_bytes)
    stable_path.write_bytes(image_bytes)
    meta_path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "model": "gemini-3.1-flash-image-preview",
                "elapsed_seconds": round(elapsed, 2),
                "image_bytes": len(image_bytes),
                "prompt_length_chars": len(PROMPT),
                "png_path": str(png_path),
            },
            indent=2,
        )
    )

    print(f"[probe] elapsed:   {elapsed:.1f}s")
    print(f"[probe] image:     {len(image_bytes):,} bytes")
    print(f"[probe] saved:     {png_path}")
    print(f"[probe] alias:     {stable_path}")
    print(f"[probe] metadata:  {meta_path}")
    print()
    print("Inspect the PNG and score against the 4 judgment axes (see docstring).")


if __name__ == "__main__":
    asyncio.run(main())
