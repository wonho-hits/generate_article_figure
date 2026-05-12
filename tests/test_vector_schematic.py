"""Tests for the Path A tool: text → SVG via Gemini."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.prompts.layout_critic import LayoutCritique, LayoutIssue
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


def _mock_client(responses: list, *, critic_responses: list | None = None) -> GeminiClient:
    """Mock for tests.

    `responses` are returned by `generate_text` in order (the generation calls).
    `critic_responses` are returned by `generate_text_with_image` in order
    (the vision-based critic calls). Default None = vision critic is never
    expected (suitable for max_refine_passes=0 tests).
    """
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(side_effect=responses)
    if critic_responses is not None:
        client.generate_text_with_image = AsyncMock(side_effect=critic_responses)
    else:
        client.generate_text_with_image = AsyncMock(
            side_effect=AssertionError(
                "vision critic invoked but no critic_responses provided"
            )
        )
    return client


# Existing tests pin `max_refine_passes=0` so they exercise only the
# generate-and-validate path (no critic LLM calls expected).


@pytest.mark.asyncio
async def test_returns_canonical_svg_on_clean_response() -> None:
    client = _mock_client([GOOD_SVG])
    result = await generate_vector_schematic(
        "draw EGFR", client=client, max_refine_passes=0
    )
    assert "<svg" in result
    assert 'id="receptor"' in result
    client.generate_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_strips_code_fence_in_response() -> None:
    client = _mock_client([GOOD_SVG_WRAPPED])
    result = await generate_vector_schematic(
        "draw EGFR", client=client, max_refine_passes=0
    )
    assert "```" not in result
    assert "<svg" in result


@pytest.mark.asyncio
async def test_empty_prompt_raises_value_error() -> None:
    client = _mock_client([])
    with pytest.raises(ValueError, match="empty"):
        await generate_vector_schematic("", client=client, max_refine_passes=0)
    with pytest.raises(ValueError, match="empty"):
        await generate_vector_schematic("   ", client=client, max_refine_passes=0)


@pytest.mark.asyncio
async def test_retries_once_on_validation_failure_then_succeeds() -> None:
    client = _mock_client([BAD_SVG, GOOD_SVG])
    result = await generate_vector_schematic(
        "draw kinase", client=client, max_refine_passes=0
    )
    assert 'id="receptor"' in result
    assert client.generate_text.await_count == 2


@pytest.mark.asyncio
async def test_two_failures_raises_validation_error() -> None:
    client = _mock_client([BAD_SVG, "<not-svg/>"])
    with pytest.raises(SVGValidationError):
        await generate_vector_schematic(
            "draw kinase", client=client, max_refine_passes=0
        )
    assert client.generate_text.await_count == 2


@pytest.mark.asyncio
async def test_non_string_response_raises() -> None:
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value=12345)  # not a string
    with pytest.raises(SVGValidationError, match="non-string"):
        await generate_vector_schematic(
            "anything", client=client, max_refine_passes=0
        )


@pytest.mark.asyncio
async def test_defs_injected_into_output() -> None:
    """Symbol library defs must appear in every output so <use> resolves."""
    client = _mock_client([GOOD_SVG])
    result = await generate_vector_schematic(
        "draw EGFR", client=client, max_refine_passes=0
    )
    assert "<defs>" in result
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
    result = await generate_vector_schematic(
        "ERK kinase", client=client, max_refine_passes=0
    )
    assert "<use" in result
    assert 'href="#kinase"' in result
    assert 'id="kinase"' in result


# ── critic + refine loop (vision-based) ───────────────────────────────────


@pytest.mark.asyncio
async def test_critic_clean_no_refine() -> None:
    """When vision critic returns has_issues=False, no regeneration."""
    clean_critique = LayoutCritique(has_issues=False, issues=[])
    client = _mock_client([GOOD_SVG], critic_responses=[clean_critique])
    result = await generate_vector_schematic(
        "draw kinase", client=client, max_refine_passes=1
    )
    assert 'id="receptor"' in result
    assert client.generate_text.await_count == 1  # only the initial gen
    assert client.generate_text_with_image.await_count == 1  # one critic call


@pytest.mark.asyncio
async def test_critic_finds_issues_triggers_refine() -> None:
    """When vision critic returns issues, generator regenerates with feedback."""
    dirty_critique = LayoutCritique(
        has_issues=True,
        issues=[
            LayoutIssue(
                severity="high",
                location="right edge of image",
                problem="Phase III box clipped at the right edge of the canvas.",
            )
        ],
    )
    clean_critique = LayoutCritique(has_issues=False, issues=[])
    client = _mock_client(
        [GOOD_SVG, GOOD_SVG],  # gen + regen
        critic_responses=[dirty_critique, clean_critique],  # 2 critic calls
    )
    result = await generate_vector_schematic(
        "draw pipeline", client=client, max_refine_passes=2
    )
    assert "<svg" in result
    assert client.generate_text.await_count == 2  # 1 gen + 1 regen
    assert client.generate_text_with_image.await_count == 2  # 2 critics

    # Verify the refine prompt mentions the surfaced issue
    refine_call_args = client.generate_text.call_args_list[1]
    refine_prompt_arg = refine_call_args[0][0]
    assert "Phase III" in refine_prompt_arg
    assert "clipped" in refine_prompt_arg


@pytest.mark.asyncio
async def test_critic_stops_at_max_refine_passes() -> None:
    """If critic keeps surfacing issues, we still stop after max_refine_passes."""
    dirty = LayoutCritique(
        has_issues=True,
        issues=[
            LayoutIssue(severity="medium", location="x", problem="still bad")
        ],
    )
    # max=1 → 1 gen + 1 critic + 1 regen = 2 gen calls + 1 critic call
    # (after the final regen we don't re-critic; we just ship)
    client = _mock_client([GOOD_SVG, GOOD_SVG], critic_responses=[dirty])
    result = await generate_vector_schematic(
        "draw pipeline", client=client, max_refine_passes=1
    )
    assert "<svg" in result
    assert client.generate_text.await_count == 2
    assert client.generate_text_with_image.await_count == 1


@pytest.mark.asyncio
async def test_critic_failure_does_not_block_output() -> None:
    """If the critic call itself errors, ship the unrefined SVG instead of failing."""
    from app.clients.gemini import GeminiResponseError

    client = _mock_client(
        [GOOD_SVG],
        critic_responses=[GeminiResponseError("vision critic LLM failed")],
    )
    result = await generate_vector_schematic(
        "draw kinase", client=client, max_refine_passes=1
    )
    assert "<svg" in result  # the unrefined SVG is returned


@pytest.mark.asyncio
async def test_critic_render_failure_does_not_block_output(monkeypatch) -> None:
    """If SVG rasterization fails, skip critic and ship the unrefined SVG."""
    from app.tools.svg_render import SVGRenderError
    import app.tools.vector_schematic as mod

    def boom(*args, **kwargs):
        raise SVGRenderError("simulated rasterization failure")

    monkeypatch.setattr(mod, "rasterize_svg", boom)
    client = _mock_client([GOOD_SVG], critic_responses=[])
    result = await generate_vector_schematic(
        "draw kinase", client=client, max_refine_passes=1
    )
    assert "<svg" in result
    assert client.generate_text.await_count == 1
    client.generate_text_with_image.assert_not_called()
