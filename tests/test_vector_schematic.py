"""Tests for the Path A tool: text → SVG via Gemini."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.gemini import GeminiClient
from app.tools.svg_validate import SVGValidationError
from app.tools.vector_schematic import generate_vector_schematic


GOOD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
    '<g id="receptor" data-role="protein">'
    '<rect x="10" y="10" width="100" height="50"/>'
    '<text x="60" y="40">EGFR</text>'
    "</g></svg>"
)

GOOD_SVG_WRAPPED = f"```svg\n{GOOD_SVG}\n```"

BAD_SVG = "<svg><script>x</script></svg>"


def _mock_client(responses: list[str]) -> GeminiClient:
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(side_effect=responses)
    return client


@pytest.mark.asyncio
async def test_returns_canonical_svg_on_clean_response() -> None:
    client = _mock_client([GOOD_SVG])
    result = await generate_vector_schematic("draw EGFR", client=client)
    assert "<svg" in result
    assert 'id="receptor"' in result
    client.generate_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_strips_code_fence_in_response() -> None:
    client = _mock_client([GOOD_SVG_WRAPPED])
    result = await generate_vector_schematic("draw EGFR", client=client)
    assert "```" not in result
    assert "<svg" in result


@pytest.mark.asyncio
async def test_empty_prompt_raises_value_error() -> None:
    client = _mock_client([])
    with pytest.raises(ValueError, match="empty"):
        await generate_vector_schematic("", client=client)
    with pytest.raises(ValueError, match="empty"):
        await generate_vector_schematic("   ", client=client)


@pytest.mark.asyncio
async def test_retries_once_on_validation_failure_then_succeeds() -> None:
    client = _mock_client([BAD_SVG, GOOD_SVG])
    result = await generate_vector_schematic("draw kinase", client=client)
    assert 'id="receptor"' in result
    assert client.generate_text.await_count == 2


@pytest.mark.asyncio
async def test_two_failures_raises_validation_error() -> None:
    client = _mock_client([BAD_SVG, "<not-svg/>"])
    with pytest.raises(SVGValidationError):
        await generate_vector_schematic("draw kinase", client=client)
    assert client.generate_text.await_count == 2


@pytest.mark.asyncio
async def test_non_string_response_raises() -> None:
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=12345)  # not a string
    with pytest.raises(SVGValidationError, match="non-string"):
        await generate_vector_schematic("anything", client=client)


@pytest.mark.asyncio
async def test_defs_injected_into_output() -> None:
    """Symbol library defs must appear in every output so <use> resolves."""
    client = _mock_client([GOOD_SVG])
    result = await generate_vector_schematic("draw EGFR", client=client)
    assert "<defs>" in result
    # Sample of expected symbol ids
    for sid in ("gpcr", "kinase", "ip3", "p_badge", "nucleus"):
        assert f'id="{sid}"' in result


@pytest.mark.asyncio
async def test_use_reference_passes_validation() -> None:
    """A Gemini output that uses <use href="#kinase"/> should validate after defs injection."""
    svg_with_use = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="erk"><use href="#kinase" x="100" y="100" width="80" height="50"/>'
        '<text x="140" y="130">ERK</text></g>'
        "</svg>"
    )
    client = _mock_client([svg_with_use])
    result = await generate_vector_schematic("ERK kinase", client=client)
    assert '<use' in result
    assert 'href="#kinase"' in result
    assert 'id="kinase"' in result  # defs symbol resolves the reference
