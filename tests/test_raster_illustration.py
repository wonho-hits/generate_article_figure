"""Mocked tests for the Path C tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.gemini import GeminiClient
from app.tools.raster_illustration import (
    detect_image_mime,
    generate_raster_illustration,
)


@pytest.mark.asyncio
async def test_returns_raw_png_bytes() -> None:
    client = MagicMock(spec=GeminiClient)
    client.generate_image = AsyncMock(return_value=b"\x89PNG-FAKE")

    result = await generate_raster_illustration(
        "draw a tumor microenvironment", client=client
    )

    assert result == b"\x89PNG-FAKE"
    client.generate_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_prepends_style_prefix_to_prompt() -> None:
    client = MagicMock(spec=GeminiClient)
    client.generate_image = AsyncMock(return_value=b"PNG")

    await generate_raster_illustration("just a kinase substrate", client=client)

    args, _ = client.generate_image.call_args
    composed = args[0]
    assert "BioRender" in composed  # style prefix landed
    assert "just a kinase substrate" in composed  # user prompt preserved


@pytest.mark.asyncio
async def test_empty_prompt_raises() -> None:
    client = MagicMock(spec=GeminiClient)
    with pytest.raises(ValueError, match="empty"):
        await generate_raster_illustration("", client=client)
    with pytest.raises(ValueError, match="empty"):
        await generate_raster_illustration("   \n", client=client)


# ── detect_image_mime ──────────────────────────────────────────────────────


def test_detect_png() -> None:
    assert detect_image_mime(b"\x89PNG\r\n\x1a\n" + b"body") == "image/png"


def test_detect_jpeg() -> None:
    assert detect_image_mime(b"\xff\xd8\xff\xe0" + b"body") == "image/jpeg"
    assert detect_image_mime(b"\xff\xd8\xff\xdb" + b"body") == "image/jpeg"


def test_detect_webp() -> None:
    data = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"more"
    assert detect_image_mime(data) == "image/webp"


def test_detect_gif() -> None:
    assert detect_image_mime(b"GIF87a" + b"x") == "image/gif"
    assert detect_image_mime(b"GIF89a" + b"x") == "image/gif"


def test_detect_unknown_falls_back_to_octet_stream() -> None:
    assert detect_image_mime(b"random garbage") == "application/octet-stream"
    assert detect_image_mime(b"") == "application/octet-stream"
