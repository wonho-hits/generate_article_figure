"""Path A tool: text → SVG vector schematic via Gemini text generation.

The output SVG always carries the bio symbol library in its <defs>, so any
`<use href="#..."/>` references emitted by Gemini resolve to library-styled
graphics. Unused symbols are inert (~10 KB overhead).

Pipeline:
  1. Generate raw SVG via Gemini (Path A system prompt + library catalog).
  2. Inject the defs block, validate XML / sanitize.
  3. If max_refine_passes > 0, run a VISION-BASED layout critic: rasterize
     the SVG to PNG and send to Gemini Vision for visual audit. If the
     critic surfaces issues, regenerate with issue-specific feedback and
     loop up to max_refine_passes times.
"""

from __future__ import annotations

import structlog

from app.agent.prompts.layout_critic import (
    VISION_CRITIC_SYSTEM,
    LayoutCritique,
    build_refine_prompt,
    build_vision_critic_prompt,
)
from app.agent.prompts.vector_schematic import SYSTEM_PROMPT, retry_prompt
from app.clients.gemini import GeminiClient, GeminiResponseError
from app.domain.bio_symbols import build_defs_block
from app.tools.svg_render import SVGRenderError, rasterize_svg
from app.tools.svg_validate import SVGValidationError, validate_and_canonicalize

logger = structlog.get_logger(__name__)

_DEFS_BLOCK = build_defs_block()

DEFAULT_MAX_REFINE_PASSES = 2
"""How many vision-critic + regen cycles to run after the initial generation.

0  = no critic, fastest, baseline quality
1  = single critic pass, ~+$0.0002 + ~30-60s, catches gross collisions
2  = two critic passes, ~+$0.0004 + ~60-150s, much higher polish (default)

Empirically on the drug-pipeline prompt, max=2 converges to ≤2 low-severity
issues after pass 2 with no label collisions; max=1 still showed medium-
severity issues and Gemini sometimes adds stages instead of fixing layout.
"""


def inject_defs(svg_string: str) -> str:
    """Insert the symbol library <defs> block immediately after the opening <svg> tag."""
    open_idx = svg_string.find("<svg")
    if open_idx == -1:
        return svg_string
    end_idx = svg_string.find(">", open_idx)
    if end_idx == -1:
        return svg_string
    return svg_string[: end_idx + 1] + _DEFS_BLOCK + svg_string[end_idx + 1 :]


async def generate_vector_schematic(
    prompt: str,
    *,
    client: GeminiClient | None = None,
    max_refine_passes: int = DEFAULT_MAX_REFINE_PASSES,
) -> str:
    """Generate a publication-quality SVG schematic from a natural-language prompt.

    Returns canonical SVG with the bio symbol library injected. On SVG-validation
    failure (malformed XML / forbidden element), retries once with the parser
    error fed back to Gemini.

    When `max_refine_passes > 0`, additionally runs a layout critic pass after
    the initial generation; if the critic surfaces layout issues, regenerates
    with concrete feedback and loops up to `max_refine_passes` times.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt is empty")

    client = client or GeminiClient()
    svg = await _generate_and_validate(prompt, client)

    for pass_num in range(max_refine_passes):
        critique = await _layout_critic(prompt, svg, client)
        if not critique.has_issues:
            logger.info("path_a.critic_clean", pass_num=pass_num + 1)
            return svg
        logger.info(
            "path_a.refine",
            pass_num=pass_num + 1,
            issue_count=len(critique.issues),
            severities=[i.severity for i in critique.issues],
        )
        refine_prompt = build_refine_prompt(prompt, critique.issues)
        svg = await _generate_and_validate(refine_prompt, client)

    return svg


async def _generate_and_validate(prompt: str, client: GeminiClient) -> str:
    """One generation attempt with the existing SVG-validation retry."""
    raw = await client.generate_text(prompt, system=SYSTEM_PROMPT)
    if not isinstance(raw, str):
        raise SVGValidationError("Gemini returned non-string content")

    try:
        return validate_and_canonicalize(inject_defs(raw))
    except SVGValidationError as exc:
        logger.warning("path_a.validation_failed", error=str(exc), attempt=1)
        retry = retry_prompt(prompt, str(exc))
        raw_retry = await client.generate_text(retry, system=SYSTEM_PROMPT)
        if not isinstance(raw_retry, str):
            raise SVGValidationError(
                "Gemini returned non-string content on retry"
            ) from exc
        try:
            return validate_and_canonicalize(inject_defs(raw_retry))
        except SVGValidationError as exc2:
            logger.error("path_a.validation_failed", error=str(exc2), attempt=2)
            raise


async def _layout_critic(
    prompt: str, svg: str, client: GeminiClient
) -> LayoutCritique:
    """Vision-based layout critic.

    Rasterizes the SVG locally and sends the PNG to Gemini Vision. Catches
    spatial collisions / clipping that a text-only critic cannot see.

    If rasterization fails or the LLM call errors, returns a no-issues
    critique so the calling code ships the unrefined SVG instead of failing.
    """
    try:
        png = rasterize_svg(svg, width=1600)
    except SVGRenderError as exc:
        logger.warning("path_a.critic_render_failed", error=str(exc))
        return LayoutCritique(has_issues=False, issues=[])

    critic_prompt = build_vision_critic_prompt(prompt)
    try:
        result = await client.generate_text_with_image(
            critic_prompt,
            png,
            image_mime="image/png",
            system=VISION_CRITIC_SYSTEM,
            response_schema=LayoutCritique,
        )
    except GeminiResponseError as exc:
        logger.warning("path_a.critic_failed", error=str(exc))
        return LayoutCritique(has_issues=False, issues=[])

    if not isinstance(result, LayoutCritique):
        logger.warning(
            "path_a.critic_wrong_type", got_type=type(result).__name__
        )
        return LayoutCritique(has_issues=False, issues=[])
    return result
