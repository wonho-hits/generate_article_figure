"""Live test: Router classifies an 8-prompt eval set against the real Gemini API.

Skipped unless --run-live is passed. Cost ~8 short text calls (negligible).

Acceptance: 8/8 correct. The eval set covers schematic prompts (Path A) and
illustrative prompts (Path C), including three user-supplied edge cases.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.agent.router import Router
from app.clients.gemini import GeminiClient


pytestmark = pytest.mark.live


# (prompt, expected_path)
ROUTER_EVAL: list[tuple[str, str]] = [
    # ── schematic / abstract structure ───────────────────────────────────────
    (
        "MAPK signaling cascade with EGF binding, EGFR activation, Ras "
        "activation, and downstream Raf, MEK, ERK phosphorylation",
        "A",
    ),
    (
        "Phosphorylation cycle of a kinase substrate showing kinase, "
        "phosphatase, and ATP/ADP turnover",
        "A",
    ),
    (
        "Western blot quantification analysis flowchart with sample prep, "
        "gel run, transfer, blocking, primary/secondary antibody, and ECL",
        "A",
    ),
    # ── illustrative / morphology / multi-cell ──────────────────────────────
    (
        "Tumor microenvironment with a cluster of cancer cells, M1 and M2 "
        "macrophages, dendritic cells, T cells, and fibroblasts",
        "C",
    ),
    (
        "Structural overview of a eukaryotic cell with labeled organelles "
        "drawn as biological illustrations",
        "C",
    ),
    # ── user-supplied edge cases ────────────────────────────────────────────
    (
        "Scientific mechanism diagram of a single-atom Fe catalyst on "
        "graphene. Top: top view of graphene lattice (gray) with a central "
        "blue Fe-N4 active center and O2 molecules. Bottom: 4-step reaction "
        "sequence: 1. Adsorption, 2. Activation, 3. Reaction, 4. Desorption. "
        "Ball-and-stick model, professional chemical color scheme.",
        "C",
    ),
    (
        "Biological pathway of DNA damage response in Naked Mole-rat. "
        "Left: cGAS and HR repair pathway leading to reduced cellular "
        "senescence. Center: chromatin ubiquitination releasing key amino "
        "acids. Right: RAD50-FANCI complex interacting with P97. 2D vector "
        "style, scientific icons of DNA, proteins, and lab animals.",
        "C",
    ),
    (
        "A high-definition cinematic landscape of a lush African savanna "
        "merging into a tropical rainforest. A winding river flows through "
        "the center, golden hour sun, snow-capped mountains in the "
        "background, baobab trees and ferns. Photorealistic, 8k.",
        "C",
    ),
    # ── chemistry (Path B) ───────────────────────────────────────────────────
    (
        "Show the structure of aspirin (acetylsalicylic acid).",
        "B",
    ),
    (
        "Draw the molecular structure of caffeine.",
        "B",
    ),
    (
        "Show the structure of citrate (the deprotonated form).",
        "B",
    ),
]


@pytest.mark.asyncio
async def test_router_classifies_eval_set() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)

    real_key = os.environ.get("GOOGLE_API_KEY", "")
    if not real_key or real_key == "test-key-not-real":
        pytest.skip("real GOOGLE_API_KEY not set")

    router = Router(client=GeminiClient(api_key=real_key))

    rows = []
    correct = 0
    for prompt, expected in ROUTER_EVAL:
        decision = await router.decide(prompt)
        ok = decision.path == expected
        rows.append((prompt[:60], expected, decision.path, ok, decision.reason[:80]))
        if ok:
            correct += 1

    print(f"\n[router eval] {correct}/{len(ROUTER_EVAL)} correct\n")
    for prompt_preview, expected, actual, ok, reason in rows:
        marker = "✓" if ok else "✗"
        print(
            f"  {marker} expected={expected} got={actual}  "
            f"{prompt_preview!r:64s}  {reason}"
        )

    assert correct == len(ROUTER_EVAL), (
        f"router eval: {correct}/{len(ROUTER_EVAL)} correct — see printed table"
    )
