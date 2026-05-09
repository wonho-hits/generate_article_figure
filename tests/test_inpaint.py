"""Mocked tests for the Path C inpaint tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.gemini import GeminiClient
from app.tools.inpaint import inpaint_region


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"FAKE-IMAGE-BODY"
RESULT_BYTES = b"\xff\xd8\xff\xe0" + b"FAKE-EDITED-BODY"
MASK_BYTES = b"\x89PNG\r\n\x1a\n" + b"FAKE-MASK-BODY"


@pytest.mark.asyncio
async def test_conversational_reprompt_no_mask() -> None:
    client = MagicMock(spec=GeminiClient)
    client.edit_image = AsyncMock(return_value=RESULT_BYTES)

    out = await inpaint_region(
        PNG_BYTES,
        "remove the duplicate T cell",
        image_mime="image/png",
        client=client,
    )

    assert out == RESULT_BYTES
    client.edit_image.assert_awaited_once()
    _, kwargs = client.edit_image.call_args
    assert kwargs["mask"] is None
    assert "remove the duplicate T cell" in kwargs["instruction"]
    # Style-preserving prefix should be prepended
    assert "PRESERVE" in kwargs["instruction"]


@pytest.mark.asyncio
async def test_mask_based_edit_passes_mask_through() -> None:
    client = MagicMock(spec=GeminiClient)
    client.edit_image = AsyncMock(return_value=RESULT_BYTES)

    out = await inpaint_region(
        PNG_BYTES,
        "replace this region with a green T cell",
        image_mime="image/png",
        mask=MASK_BYTES,
        client=client,
    )

    assert out == RESULT_BYTES
    _, kwargs = client.edit_image.call_args
    assert kwargs["mask"] == MASK_BYTES
    assert kwargs["image_mime"] == "image/png"


@pytest.mark.asyncio
async def test_empty_instruction_raises() -> None:
    client = MagicMock(spec=GeminiClient)
    with pytest.raises(ValueError, match="instruction"):
        await inpaint_region(
            PNG_BYTES, "", image_mime="image/png", client=client
        )
    with pytest.raises(ValueError, match="instruction"):
        await inpaint_region(
            PNG_BYTES, "   ", image_mime="image/png", client=client
        )


@pytest.mark.asyncio
async def test_empty_image_raises() -> None:
    client = MagicMock(spec=GeminiClient)
    with pytest.raises(ValueError, match="image"):
        await inpaint_region(
            b"", "do something", image_mime="image/png", client=client
        )
