"""Path C edit tool: inpaint or conversationally reprompt an existing raster.

Wraps GeminiClient.edit_image with the style-preserving instruction prefix.
"""

from __future__ import annotations

import structlog

from app.agent.prompts.inpaint import INSTRUCTION_PREFIX
from app.clients.gemini import GeminiClient

logger = structlog.get_logger(__name__)


async def inpaint_region(
    image: bytes,
    instruction: str,
    *,
    image_mime: str,
    mask: bytes | None = None,
    client: GeminiClient | None = None,
) -> bytes:
    """Edit an existing raster figure.

    `mask` semantics: PNG with WHITE pixels marking the region to edit and
    BLACK pixels marking the region to preserve (industry convention).
    """
    if not instruction or not instruction.strip():
        raise ValueError("instruction is empty")
    if not image:
        raise ValueError("image bytes are empty")

    client = client or GeminiClient()
    composed = INSTRUCTION_PREFIX + instruction
    has_mask = mask is not None
    logger.info("inpaint.call", has_mask=has_mask, instruction_length=len(instruction))
    return await client.edit_image(
        image=image,
        instruction=composed,
        image_mime=image_mime,
        mask=mask,
    )
