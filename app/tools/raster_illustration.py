"""Path C tool: text → raster image via Gemini Image (Nano Banana 2).

Note on format: Gemini-3.1-flash-image-preview returns JPEG, not PNG, in
practice. We don't try to coerce — `detect_image_mime` returns the actual
type, and serialization layers use it to build correct data URIs / file
extensions.
"""

from __future__ import annotations

import structlog

from app.agent.prompts.raster_illustration import STYLE_PREFIX
from app.clients.gemini import GeminiClient

logger = structlog.get_logger(__name__)


def detect_image_mime(data: bytes) -> str:
    """Detect image MIME by inspecting magic bytes.

    Returns 'application/octet-stream' for unrecognized data — caller can
    treat that as an error if desired.
    """
    if not data:
        return "application/octet-stream"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if (
        data.startswith(b"RIFF")
        and len(data) >= 12
        and data[8:12] == b"WEBP"
    ):
        return "image/webp"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    return "application/octet-stream"


async def generate_raster_illustration(
    prompt: str,
    *,
    client: GeminiClient | None = None,
) -> bytes:
    """Generate a publication-style raster illustration. Returns raw PNG bytes.

    No retry: image generation is non-deterministic and a failed call usually
    means a bad prompt, not a transient error. The Gemini SDK's own 5xx/429
    retry (in GeminiClient._call_with_retry) is preserved.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt is empty")
    client = client or GeminiClient()
    composed = f"{STYLE_PREFIX}{prompt}"
    return await client.generate_image(composed)
