"""Shared vision-based layout critic for the SVG-producing paths (A and D).

Both Path A (vector schematic) and Path D (mixed vector + raster icons) refine
their output the same way: rasterize the SVG, send the PNG to Gemini Vision,
and get back a structured `LayoutCritique`. This module is the single home for
that step plus the severity score used by the keep-best refine loop.

Kept tool-agnostic on purpose — it takes an SVG string and a client, and never
assumes which path produced the SVG.
"""

from __future__ import annotations

import structlog

from app.agent.prompts.layout_critic import (
    VISION_CRITIC_SYSTEM,
    LayoutCritique,
    build_vision_critic_prompt,
)
from app.clients.gemini import GeminiClient, GeminiResponseError
from app.tools.svg_render import SVGRenderError, rasterize_svg

logger = structlog.get_logger(__name__)

# Severity weights for the keep-best refine loop. The numbers are not
# load-bearing — what matters is the strict ordering high > medium > low and
# that a single HIGH issue outweighs multiple LOW issues.
SEVERITY_WEIGHT: dict[str, int] = {"high": 4, "medium": 2, "low": 1}


def critique_score(critique: LayoutCritique) -> int:
    """Sum severity-weighted issue count. Lower is better; 0 = clean."""
    return sum(SEVERITY_WEIGHT.get(i.severity, 1) for i in critique.issues)


async def vision_layout_critic(
    prompt: str,
    svg: str,
    client: GeminiClient,
    *,
    render_width: int = 1600,
) -> LayoutCritique:
    """Rasterize the SVG and have Gemini Vision audit its layout.

    Catches spatial collisions / clipping a text-only critic cannot see. If
    rasterization or the LLM call fails, returns a no-issues critique so the
    caller ships the unrefined SVG instead of erroring (graceful degradation —
    e.g. on a host without a working SVG rasterizer).
    """
    try:
        png = rasterize_svg(svg, width=render_width)
    except SVGRenderError as exc:
        logger.warning("layout_critic.render_failed", error=str(exc))
        return LayoutCritique(has_issues=False, issues=[])

    try:
        result = await client.generate_text_with_image(
            build_vision_critic_prompt(prompt),
            png,
            image_mime="image/png",
            system=VISION_CRITIC_SYSTEM,
            response_schema=LayoutCritique,
        )
    except GeminiResponseError as exc:
        logger.warning("layout_critic.failed", error=str(exc))
        return LayoutCritique(has_issues=False, issues=[])

    if not isinstance(result, LayoutCritique):
        logger.warning("layout_critic.wrong_type", got_type=type(result).__name__)
        return LayoutCritique(has_issues=False, issues=[])
    return result
