"""Tests for the Path D tool: vector backbone + generated raster icons."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

import app.tools.mixed_schematic as mod
from app.clients.gemini import GeminiClient
from app.tools.mixed_schematic import generate_mixed_figure

BACKBONE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
    '<g id="tcell" data-role="entity">'
    '<rect class="gen-icon" data-desc="a round CD8 T cell with a dark nucleus" '
    'x="100" y="100" width="120" height="120"/>'
    '<text x="160" y="240" text-anchor="middle">CD8+ T cell</text>'
    "</g></svg>"
)

BACKBONE_NO_ICONS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
    '<g id="frame" data-role="box"><rect x="0" y="0" width="10" height="10"/>'
    '<text x="5" y="5">label</text></g></svg>'
)


def _icon_jpeg(w: int = 300, h: int = 200) -> bytes:
    img = Image.new("RGB", (w, h), (255, 255, 255))
    for x in range(w // 4, 3 * w // 4):
        for y in range(h // 4, 3 * h // 4):
            img.putpixel((x, y), (50, 100, 170))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _client(*, backbone: str, icon: bytes | Exception) -> GeminiClient:
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=backbone)
    if isinstance(icon, Exception):
        client.generate_image = AsyncMock(side_effect=icon)
    else:
        client.generate_image = AsyncMock(return_value=icon)
    return client


@pytest.fixture(autouse=True)
def _clear_cache():
    mod._ICON_CACHE.clear()
    yield
    mod._ICON_CACHE.clear()


@pytest.mark.asyncio
async def test_placeholder_replaced_with_data_image() -> None:
    client = _client(backbone=BACKBONE, icon=_icon_jpeg())
    out = await generate_mixed_figure("draw a T cell", client=client)
    assert "<image" in out or "image" in out
    assert "data:image/png;base64," in out
    assert "gen-icon" not in out  # placeholder consumed
    assert "CD8+ T cell" in out  # vector label preserved
    client.generate_image.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_placeholders_returns_vector_backbone() -> None:
    client = _client(backbone=BACKBONE_NO_ICONS, icon=_icon_jpeg())
    out = await generate_mixed_figure("just a frame", client=client)
    assert "data:image" not in out
    client.generate_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_icon_failure_leaves_placeholder_untouched() -> None:
    client = _client(backbone=BACKBONE, icon=RuntimeError("image gen 500"))
    out = await generate_mixed_figure("draw a T cell", client=client)
    # icon failed → no data image embedded; figure still returns (label intact)
    assert "data:image" not in out
    assert "CD8+ T cell" in out


@pytest.mark.asyncio
async def test_icon_cache_dedupes_identical_desc() -> None:
    two_same = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="g" data-role="e">'
        '<rect class="gen-icon" data-desc="a macrophage" x="10" y="10" width="80" height="80"/>'
        '<rect class="gen-icon" data-desc="a macrophage" x="200" y="10" width="80" height="80"/>'
        '<text x="50" y="120">m</text></g></svg>'
    )
    client = _client(backbone=two_same, icon=_icon_jpeg())
    out = await generate_mixed_figure("two macrophages", client=client)
    assert out.count("data:image/png;base64,") == 2  # both placeholders filled
    client.generate_image.assert_awaited_once()  # but only ONE generation (cache)


@pytest.mark.asyncio
async def test_empty_prompt_raises() -> None:
    client = _client(backbone=BACKBONE, icon=_icon_jpeg())
    with pytest.raises(ValueError, match="empty"):
        await generate_mixed_figure("   ", client=client)
