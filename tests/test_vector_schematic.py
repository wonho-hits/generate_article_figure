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
async def test_defs_injected_for_referenced_symbols() -> None:
    """Lazy injection: <use href="#X"/> in the LLM output causes only the
    matched library symbols to land in the output <defs> block. Symbols the
    LLM did NOT reference must NOT appear (they would be dead bytes)."""
    svg_with_refs = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="content">'
        '<use href="#gpcr" x="20" y="20" width="60" height="80"/>'
        '<use href="#kinase" x="100" y="100" width="80" height="50"/>'
        '<text x="60" y="160">EGFR</text>'
        "</g></svg>"
    )
    client = _mock_client([svg_with_refs])
    result = await generate_vector_schematic(
        "draw EGFR", client=client, max_refine_passes=0
    )
    assert "<defs>" in result
    # Referenced symbols present
    assert '<symbol id="gpcr"' in result
    assert '<symbol id="kinase"' in result
    # Unreferenced symbols absent (this is the whole point of lazy injection)
    assert '<symbol id="ip3"' not in result
    assert '<symbol id="p_badge"' not in result
    assert '<symbol id="nucleus"' not in result


@pytest.mark.asyncio
async def test_defs_block_omitted_when_no_use_refs() -> None:
    """If the LLM emits no <use> references, no <defs> wrapper is spliced
    in — empty defs would just be visual noise in the output."""
    client = _mock_client([GOOD_SVG])  # GOOD_SVG has <g id="receptor">, no <use>
    result = await generate_vector_schematic(
        "anything", client=client, max_refine_passes=0
    )
    assert "<defs>" not in result
    assert 'id="receptor"' in result  # body unchanged


@pytest.mark.asyncio
async def test_use_without_width_height_gets_catalog_defaults() -> None:
    """The LLM sometimes emits `<use href="#X" x=.. y=.. />` without width/
    height. SVG treats missing dimensions as 100% of viewport, so a 24×24
    badge would scale to ~1600×900. _patch_use_dimensions injects the
    catalog's default_w / default_h to prevent this."""
    # p_badge has default 24×24 per CATALOG. kinase is 80×50.
    svg_no_dims = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="content">'
        '<use href="#p_badge" x="100" y="100"/>'
        '<use href="#kinase" x="200" y="200"/>'
        "</g></svg>"
    )
    client = _mock_client([svg_no_dims])
    result = await generate_vector_schematic(
        "x", client=client, max_refine_passes=0
    )
    # p_badge should now have width="24" height="24"
    assert 'href="#p_badge"' in result
    assert 'width="24"' in result and 'height="24"' in result
    # kinase should have width="80" height="50"
    assert 'href="#kinase"' in result
    assert 'width="80"' in result and 'height="50"' in result


@pytest.mark.asyncio
async def test_use_with_explicit_dims_is_left_alone() -> None:
    """If the LLM emits width and height already, they MUST NOT be
    overwritten — the LLM may want a different size."""
    svg_with_dims = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="content">'
        '<use href="#p_badge" x="100" y="100" width="50" height="50"/>'
        "</g></svg>"
    )
    client = _mock_client([svg_with_dims])
    result = await generate_vector_schematic(
        "x", client=client, max_refine_passes=0
    )
    # Should keep the LLM's chosen 50×50, NOT replace with default 24×24
    assert 'width="50"' in result
    assert 'height="50"' in result
    assert 'width="24"' not in result


@pytest.mark.asyncio
async def test_use_with_only_width_gets_height_default() -> None:
    """Partial: LLM gave width but no height. We fill the missing one."""
    svg_partial = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="content">'
        '<use href="#p_badge" x="100" y="100" width="48"/>'
        "</g></svg>"
    )
    client = _mock_client([svg_partial])
    result = await generate_vector_schematic(
        "x", client=client, max_refine_passes=0
    )
    assert 'width="48"' in result  # LLM's width preserved
    assert 'height="24"' in result  # catalog default for height injected


@pytest.mark.asyncio
async def test_xlink_href_also_triggers_injection() -> None:
    """Some Gemini outputs use the older xlink:href attribute. Lazy injection
    must recognise both forms."""
    svg_xlink = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 800 600">'
        '<g id="content">'
        '<use xlink:href="#kinase" x="100" y="100" width="80" height="50"/>'
        "</g></svg>"
    )
    client = _mock_client([svg_xlink])
    result = await generate_vector_schematic(
        "x", client=client, max_refine_passes=0
    )
    assert '<symbol id="kinase"' in result


@pytest.mark.asyncio
async def test_transitive_use_ref_pulls_in_inner_symbol(monkeypatch) -> None:
    """Wrappers that `<use>` another symbol internally must trigger
    injection of BOTH the wrapper and the inner symbol. Otherwise the
    wrapper renders blank because its dependency is missing from <defs>."""
    import app.domain.bio_symbols as bs
    import app.tools.vector_schematic as mod

    # Synthesise a wrapper + inner pair in the library for this test only.
    extra = {
        "test_inner_shape": (
            '<symbol id="test_inner_shape" viewBox="0 0 100 100" '
            'overflow="visible"><rect x="10" y="10" width="80" height="80" '
            'fill="#abc"/></symbol>'
        ),
        "test_cropped_wrapper": (
            '<symbol id="test_cropped_wrapper" viewBox="20 20 60 60">'
            '<use href="#test_inner_shape" x="0" y="0" width="100" height="100"/>'
            "</symbol>"
        ),
    }
    augmented = {**bs.SYMBOLS, **extra}
    monkeypatch.setattr(bs, "SYMBOLS", augmented)
    monkeypatch.setattr(mod, "SYMBOLS", augmented)

    # LLM references ONLY the wrapper. Transitive resolution must also
    # inject the inner shape that the wrapper depends on.
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="content">'
        '<use href="#test_cropped_wrapper" x="0" y="0"/>'
        "</g></svg>"
    )
    client = _mock_client([svg])
    result = await generate_vector_schematic(
        "anything", client=client, max_refine_passes=0
    )
    assert '<symbol id="test_cropped_wrapper"' in result
    assert '<symbol id="test_inner_shape"' in result, (
        "Transitive resolution failed: wrapper landed but inner shape didn't."
    )


@pytest.mark.asyncio
async def test_unknown_use_ref_is_silently_skipped_in_defs() -> None:
    """Refs to symbols not in the library are not injected. The SVG validator
    is responsible for flagging unresolved references."""
    svg_unknown = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="content">'
        '<use href="#kinase"/>'
        '<use href="#totally_made_up_symbol"/>'
        "</g></svg>"
    )
    client = _mock_client([svg_unknown])
    result = await generate_vector_schematic(
        "x", client=client, max_refine_passes=0
    )
    assert '<symbol id="kinase"' in result
    assert "totally_made_up_symbol" not in result.split("</defs>")[0], (
        "Unknown ref leaked into <defs>"
    )


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
    # max=1 → 1 gen + 1 critic + 1 regen = 2 gen calls + 1 critic call.
    # The final regen is intentionally NOT critiqued; keep-best ships the
    # best critiqued candidate so far (here: the initial SVG).
    client = _mock_client([GOOD_SVG, GOOD_SVG], critic_responses=[dirty])
    result = await generate_vector_schematic(
        "draw pipeline", client=client, max_refine_passes=1
    )
    assert "<svg" in result
    assert client.generate_text.await_count == 2
    assert client.generate_text_with_image.await_count == 1


@pytest.mark.asyncio
async def test_critic_keep_best_when_regen_regresses() -> None:
    """If a refine pass produces a worse critique than its predecessor, the
    earlier (better) SVG should be returned — not the regression."""
    # Two distinguishable SVGs so we can assert which one was returned.
    INITIAL_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="initial" data-role="protein"><rect/></g></svg>'
    )
    REGRESSED_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="regressed" data-role="protein"><rect/></g></svg>'
    )
    # Pass 1 critiques INITIAL_SVG: 1 low-severity (score = 1).
    # Pass 2 critiques REGRESSED_SVG: 3 high-severity (score = 12). Worse!
    # max_refine_passes=2 means: critique INITIAL → regen → critique REGRESSED
    # → regen DOUBLY_REGRESSED. The doubly-regenerated SVG is never critiqued,
    # so it's discarded. Best critiqued candidate = INITIAL_SVG.
    pass1_critique = LayoutCritique(
        has_issues=True,
        issues=[LayoutIssue(severity="low", location="x", problem="minor")],
    )
    pass2_critique = LayoutCritique(
        has_issues=True,
        issues=[
            LayoutIssue(severity="high", location="a", problem="bad 1"),
            LayoutIssue(severity="high", location="b", problem="bad 2"),
            LayoutIssue(severity="high", location="c", problem="bad 3"),
        ],
    )
    DOUBLY_REGRESSED_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="doubly_regressed" data-role="protein"><rect/></g></svg>'
    )
    client = _mock_client(
        [INITIAL_SVG, REGRESSED_SVG, DOUBLY_REGRESSED_SVG],
        critic_responses=[pass1_critique, pass2_critique],
    )
    result = await generate_vector_schematic(
        "draw pipeline", client=client, max_refine_passes=2
    )
    assert 'id="initial"' in result, (
        "Expected keep-best to return INITIAL_SVG (score 1), not the "
        "regression. Got:\n" + result[:400]
    )
    assert 'id="regressed"' not in result
    assert 'id="doubly_regressed"' not in result
    assert client.generate_text.await_count == 3  # 1 initial + 2 regens
    assert client.generate_text_with_image.await_count == 2


@pytest.mark.asyncio
async def test_critic_keep_best_picks_later_when_it_improves() -> None:
    """When a refine pass produces a strictly better critique, the new SVG
    becomes the new best. Sanity check that keep-best isn't biased toward
    the initial candidate."""
    INITIAL_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="initial"/></svg>'
    )
    IMPROVED_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="improved"/></svg>'
    )
    THIRD_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="third"/></svg>'
    )
    pass1_critique = LayoutCritique(  # critiques INITIAL: score 4
        has_issues=True,
        issues=[LayoutIssue(severity="high", location="x", problem="bad")],
    )
    pass2_critique = LayoutCritique(  # critiques IMPROVED: score 1 (better)
        has_issues=True,
        issues=[LayoutIssue(severity="low", location="x", problem="minor")],
    )
    client = _mock_client(
        [INITIAL_SVG, IMPROVED_SVG, THIRD_SVG],
        critic_responses=[pass1_critique, pass2_critique],
    )
    result = await generate_vector_schematic(
        "x", client=client, max_refine_passes=2
    )
    assert 'id="improved"' in result, (
        "Expected keep-best to return IMPROVED_SVG (score 1 < INITIAL's 4). "
        f"Got: {result[:400]}"
    )


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
