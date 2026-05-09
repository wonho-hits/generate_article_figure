"""Live test: render aspirin via Path B against the real Gemini API + RDKit.

Skipped unless --run-live. Cost: 1 short Gemini text call (~$0.0001).
RDKit + PubChemPy are local, no API cost.
"""

from __future__ import annotations

import os
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from dotenv import load_dotenv

from app.clients.gemini import GeminiClient
from app.tools.molecule import render_molecule


pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_live_render_aspirin() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    real_key = os.environ.get("GOOGLE_API_KEY", "")
    if not real_key or real_key == "test-key-not-real":
        pytest.skip("real GOOGLE_API_KEY not set")

    client = GeminiClient(api_key=real_key)
    svg = await render_molecule("show the structure of aspirin", client=client)

    # Parses cleanly
    root = ET.fromstring(svg)
    local = root.tag.rsplit("}", 1)[-1]
    assert local == "svg"

    # Has the expected wrapping group
    groups = [
        e for e in root.iter()
        if e.tag.rsplit("}", 1)[-1] == "g" and e.attrib.get("id") == "molecule"
    ]
    assert len(groups) >= 1

    # Has at least a few path/text elements (the rendered structure)
    paths = [e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "path"]
    assert len(paths) > 5, f"expected several <path> elements; got {len(paths)}"

    out_path = Path("/tmp/path_b_live_aspirin.svg")
    out_path.write_text(svg)
    print(f"\n[live path b] wrote {len(svg)} chars to {out_path}")
