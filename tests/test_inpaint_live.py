"""Live test: edit a real raster against the Gemini Image API.

Uses the probe artifact (`/tmp/path_c_probe_latest.png`, the BioRender tumor
microenvironment with a duplicate CD8+ T cell) and asks Gemini to remove the
duplicate. Verifies API works end-to-end. Visual quality is judged afterwards
by reading the saved output.

Skipped unless --run-live. Cost ~$0.04 per run.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.clients.gemini import GeminiClient
from app.tools.inpaint import inpaint_region
from app.tools.raster_illustration import detect_image_mime


pytestmark = pytest.mark.live


SOURCE_PATH = Path("/tmp/path_c_probe_latest.png")
INSTRUCTION = (
    "There are TWO CD8+ T cells in this image. Remove the upper-right CD8+ T cell "
    "(the one receiving the inhibition arrow from MDSC) AND its 'CD8+ T cell' label. "
    "Keep the central-right CD8+ T cell that receives activation arrows from the "
    "cancer cluster and the fibroblast. Re-route the MDSC inhibition arrow so it "
    "ends at the remaining CD8+ T cell. Also remove any duplicate 'M1 polarization' "
    "label that appears below the M2 macrophage. Preserve everything else exactly."
)


@pytest.mark.asyncio
async def test_live_inpaint_conversational_reprompt() -> None:
    if not SOURCE_PATH.exists():
        pytest.skip(
            f"{SOURCE_PATH} not present — run "
            f"analyze/260509_path_c_complex_figure_probe.py first"
        )

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    real_key = os.environ.get("GOOGLE_API_KEY", "")
    if not real_key or real_key == "test-key-not-real":
        pytest.skip("real GOOGLE_API_KEY not set")

    source_bytes = SOURCE_PATH.read_bytes()
    source_mime = detect_image_mime(source_bytes)
    assert source_mime in {"image/png", "image/jpeg"}, source_mime

    client = GeminiClient(api_key=real_key)
    edited = await inpaint_region(
        source_bytes,
        INSTRUCTION,
        image_mime=source_mime,
        client=client,
    )

    assert len(edited) > 1000
    edited_mime = detect_image_mime(edited)
    assert edited_mime in {"image/png", "image/jpeg", "image/webp"}, edited_mime

    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[edited_mime]
    out_path = Path(f"/tmp/path_c_live_inpaint.{ext}")
    out_path.write_bytes(edited)
    print(
        f"\n[live inpaint] source: {len(source_bytes)} bytes ({source_mime}) "
        f"→ edited: {len(edited)} bytes ({edited_mime}) → {out_path}"
    )
