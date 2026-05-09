"""Live test: hits the real Gemini API. Skipped unless --run-live is passed.

This is the integration check that the system prompt actually produces SVG
that satisfies our validator. Cost per run is ~$0.0001.
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from dotenv import load_dotenv

from app.clients.gemini import GeminiClient
from app.tools.vector_schematic import generate_vector_schematic


pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_live_generates_valid_svg_with_groups() -> None:
    # Conftest pins GOOGLE_API_KEY to a fake value so non-live tests cannot
    # accidentally call the real API. Override here from .env when actually
    # running --run-live.
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)

    real_key = os.environ.get("GOOGLE_API_KEY", "")
    if not real_key or real_key == "test-key-not-real":
        pytest.skip("real GOOGLE_API_KEY not set in .env or environment")

    client = GeminiClient(api_key=real_key)
    prompt = (
        "MAPK signaling cascade with EGF binding, EGFR activation, "
        "Ras activation, and downstream Raf, MEK, ERK phosphorylation. "
        "Show the membrane and cytoplasm."
    )
    svg = await generate_vector_schematic(prompt, client=client)

    root = ET.fromstring(svg)
    local = root.tag.rsplit("}", 1)[-1]
    assert local == "svg", f"root must be <svg>, got <{local}>"

    groups_with_id = [
        e for e in root.iter()
        if e.tag.rsplit("}", 1)[-1] == "g" and "id" in e.attrib
    ]
    assert len(groups_with_id) >= 3, (
        f"expected ≥3 named groups, got {len(groups_with_id)}: "
        f"{[g.attrib.get('id') for g in groups_with_id]}"
    )

    # Make the artifact eyeball-able after the run.
    out_path = "/tmp/path_a_live_smoke.svg"
    with open(out_path, "w") as f:
        f.write(svg)
    print(f"\n[live smoke] wrote {len(svg)} bytes to {out_path}")
