"""Live test: Path C raster generation against the real Gemini Image API.

Skipped unless --run-live is passed. Cost ~$0.04 per run.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from app.clients.gemini import GeminiClient
from app.tools.raster_illustration import (
    detect_image_mime,
    generate_raster_illustration,
)


pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_live_path_c_returns_image_bytes() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)

    real_key = os.environ.get("GOOGLE_API_KEY", "")
    if not real_key or real_key == "test-key-not-real":
        pytest.skip("real GOOGLE_API_KEY not set")

    client = GeminiClient(api_key=real_key)
    prompt = (
        "T cell receptor binding to MHC class I on a tumor cell, with "
        "downstream signaling represented as small phosphorylation events "
        "near the cytoplasmic tail."
    )
    image = await generate_raster_illustration(prompt, client=client)

    assert len(image) > 1000, f"image too small: {len(image)} bytes"

    mime = detect_image_mime(image)
    assert mime in {"image/png", "image/jpeg", "image/webp"}, (
        f"unexpected mime: {mime}"
    )

    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[mime]
    out_path = Path(f"/tmp/path_c_live_smoke.{ext}")
    out_path.write_bytes(image)
    print(
        f"\n[live smoke] Path C wrote {len(image)} bytes "
        f"({mime}) to {out_path}"
    )
