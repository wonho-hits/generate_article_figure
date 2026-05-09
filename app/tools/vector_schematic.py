"""Path A tool: text → SVG vector schematic via Gemini text generation.

The output SVG always carries the bio symbol library in its <defs>, so any
`<use href="#..."/>` references emitted by Gemini resolve to library-styled
graphics. Unused symbols are inert (~10 KB overhead).
"""

from __future__ import annotations

import structlog

from app.agent.prompts.vector_schematic import SYSTEM_PROMPT, retry_prompt
from app.clients.gemini import GeminiClient
from app.domain.bio_symbols import build_defs_block
from app.tools.svg_validate import SVGValidationError, validate_and_canonicalize

logger = structlog.get_logger(__name__)

_DEFS_BLOCK = build_defs_block()


def inject_defs(svg_string: str) -> str:
    """Insert the symbol library <defs> block immediately after the opening <svg> tag.

    Does string-level injection rather than XML manipulation to preserve
    Gemini's exact formatting. The validator parses the merged result so any
    structural error surfaces normally.
    """
    open_idx = svg_string.find("<svg")
    if open_idx == -1:
        # Let the validator surface this as a structural error
        return svg_string
    end_idx = svg_string.find(">", open_idx)
    if end_idx == -1:
        return svg_string
    return svg_string[: end_idx + 1] + _DEFS_BLOCK + svg_string[end_idx + 1 :]


async def generate_vector_schematic(
    prompt: str,
    *,
    client: GeminiClient | None = None,
) -> str:
    """Generate a publication-quality SVG schematic from a natural-language prompt.

    Returns canonical SVG with the bio symbol library injected. On validation
    failure, retries once with the parser error fed back to Gemini. A second
    failure raises SVGValidationError.
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt is empty")

    client = client or GeminiClient()

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
