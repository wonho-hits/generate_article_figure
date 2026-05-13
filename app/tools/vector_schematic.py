"""Path A tool: text → SVG vector schematic via Gemini text generation.

The output SVG carries ONLY the library symbols Gemini actually referenced
via `<use href="#...">`. The full library catalog is advertised in the
system prompt, but we don't bundle 60 KB of unused `<symbol>` definitions
into every response — `inject_defs` parses the raw output, looks up which
ids the LLM used, and splices in just those.

Pipeline:
  1. Generate raw SVG via Gemini (Path A system prompt + library catalog).
  2. Lazy-inject the `<defs>` block for referenced symbols, validate XML /
     sanitise.
  3. If max_refine_passes > 0, run a VISION-BASED layout critic: rasterise
     the SVG to PNG and send to Gemini Vision for visual audit. If the
     critic surfaces issues, regenerate with issue-specific feedback. Loop
     up to max_refine_passes times. The refine loop is keep-best: if a
     regeneration scores worse than its predecessor, ship the predecessor.
"""

from __future__ import annotations

import re

import structlog

from app.agent.prompts.layout_critic import (
    VISION_CRITIC_SYSTEM,
    LayoutCritique,
    build_refine_prompt,
    build_vision_critic_prompt,
)
from app.agent.prompts.vector_schematic import SYSTEM_PROMPT, retry_prompt
from app.clients.gemini import GeminiClient, GeminiResponseError
from app.domain.bio_symbols import CATALOG, SYMBOLS, build_defs_block_for
from app.tools.svg_render import SVGRenderError, rasterize_svg
from app.tools.svg_validate import SVGValidationError, validate_and_canonicalize

logger = structlog.get_logger(__name__)

# Matches `<use ... href="#id"`, `<use ... xlink:href="#id"`, attribute order
# agnostic. Captures the bare id (without the leading `#`).
_USE_HREF_RE = re.compile(
    r'<use\b[^>]*?(?:xlink:)?href\s*=\s*"#([A-Za-z_][\w-]*)"',
    re.IGNORECASE,
)


def _extract_use_refs(svg_string: str) -> set[str]:
    """Return the set of bare symbol ids referenced by `<use href="#id"/>`."""
    return set(_USE_HREF_RE.findall(svg_string))


# Matches a full <use ... /> element, capturing its inner attribute string.
# Greedy on the attribute body but stops at the first `/>` (single closing).
_USE_TAG_RE = re.compile(r"<use\b([^>]*?)\s*/>", re.IGNORECASE | re.DOTALL)

# Catalog-default sizes by symbol id. Populated lazily so tests with
# monkey-patched SYMBOLS see the fresh CATALOG.
def _catalog_defaults() -> dict[str, tuple[int, int]]:
    return {e.id: (e.default_w, e.default_h) for e in CATALOG}


def _patch_use_dimensions(svg_string: str) -> str:
    """Inject catalog `default_w` / `default_h` on `<use>` elements that
    omit width or height.

    Why this exists: SVG's `<use>` element treats absent width/height as
    "100% of the containing viewport". When the LLM emits
    `<use href="#p_badge" x="310" y="415" />` without dimensions, the
    24×24 P badge scales to ~1600×900 and dominates the figure. The
    catalog lists default sizes in the system prompt, but prompt
    compliance is imperfect — this function is the defensive fix.

    Only touches `<use>` elements whose `href` resolves to a CATALOG
    entry. Anything else (unknown ids, non-library uses inside
    bundled-icon bodies) is left alone.
    """
    defaults = _catalog_defaults()

    def patch(match: re.Match[str]) -> str:
        attrs = match.group(1)
        href_m = re.search(
            r'(?:xlink:)?href\s*=\s*"#([A-Za-z_][\w-]*)"', attrs
        )
        if not href_m:
            return match.group(0)
        sid = href_m.group(1)
        if sid not in defaults:
            return match.group(0)
        has_w = re.search(r"\bwidth\s*=", attrs) is not None
        has_h = re.search(r"\bheight\s*=", attrs) is not None
        if has_w and has_h:
            return match.group(0)
        w, h = defaults[sid]
        injection_parts: list[str] = []
        if not has_w:
            injection_parts.append(f'width="{w}"')
        if not has_h:
            injection_parts.append(f'height="{h}"')
        injection = " " + " ".join(injection_parts)
        return f"<use{attrs}{injection}/>"

    return _USE_TAG_RE.sub(patch, svg_string)


def _resolve_transitive_refs(
    initial_refs: set[str], symbol_bodies: dict[str, str]
) -> set[str]:
    """Expand a ref set to include refs nested inside the referenced symbols.

    Some bundled icons are thin wrappers that crop a larger composite via
    `<use href="#full_composite"/>` inside their own body. Lazy injection
    must follow those transitive references — otherwise the wrapper renders
    a blank box because the composite it depends on never lands in `<defs>`.

    BFS over the use-graph. Unknown ids are silently dropped (same policy
    as the rest of the lazy-injection pipeline).
    """
    resolved: set[str] = set()
    queue: list[str] = [r for r in initial_refs if r in symbol_bodies]
    while queue:
        sid = queue.pop()
        if sid in resolved:
            continue
        resolved.add(sid)
        # Recurse into this symbol's body for more <use> refs.
        for nested in _USE_HREF_RE.findall(symbol_bodies[sid]):
            if nested in symbol_bodies and nested not in resolved:
                queue.append(nested)
    return resolved

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
    """Lazy-inject a `<defs>` block for symbols the LLM actually referenced.

    Scans the SVG for `<use href="#id"/>` or `<use xlink:href="#id"/>`
    references, looks each id up in the library, and splices a `<defs>`
    block containing only the matched symbols immediately after the opening
    `<svg>` tag.

    No-ops when:
    - There is no `<svg>` open tag in the input (malformed; let the
      validator reject it).
    - The LLM emitted no `<use>` references at all.
    - The LLM's refs are all unknown to the library — no defs to inject.

    Unknown referenced ids are NOT flagged. They render as a no-op (SVG's
    fallback for unresolved `<use>` refs is to draw nothing) so the worst
    that happens is a missing symbol in the output. We accept that as
    cheaper than the alternative — running an additional reference-resolution
    validator pass on every generation.
    """
    open_idx = svg_string.find("<svg")
    if open_idx == -1:
        return svg_string
    end_idx = svg_string.find(">", open_idx)
    if end_idx == -1:
        return svg_string
    refs = _extract_use_refs(svg_string)
    if not refs:
        return svg_string
    # Follow refs that appear inside the referenced symbols themselves so
    # that wrappers (e.g. bioicons_mitosis_telophase, which `<use>`s
    # bioicons_mitosis under the hood) pull their dependencies in.
    resolved = _resolve_transitive_refs(refs, SYMBOLS)
    defs_block = build_defs_block_for(resolved)
    if not defs_block:
        return svg_string
    return svg_string[: end_idx + 1] + defs_block + svg_string[end_idx + 1 :]


# Severity weights for the keep-best refine loop. The numbers themselves are
# not load-bearing — what matters is the strict ordering high > medium > low
# and that a single HIGH issue outweighs multiple LOW issues.
_SEVERITY_WEIGHT: dict[str, int] = {"high": 4, "medium": 2, "low": 1}


def _critique_score(critique: LayoutCritique) -> int:
    """Sum severity-weighted issue count. Lower is better; 0 = clean."""
    return sum(_SEVERITY_WEIGHT.get(i.severity, 1) for i in critique.issues)


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

    When `max_refine_passes > 0`, runs a vision-based layout critic after each
    generation. If the critic returns no issues, ships immediately. Otherwise
    regenerates with concrete feedback and loops up to `max_refine_passes`
    times. If none of the candidates fully converge, ships the one with the
    LOWEST severity-weighted critique score (not the most recent regen — the
    refine loop can occasionally produce a worse output than its predecessor,
    and "keep-best" prevents shipping that regression).
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt is empty")

    client = client or GeminiClient()
    svg = await _generate_and_validate(prompt, client)
    best_svg = svg
    best_score: int | None = None  # None == not yet critiqued

    for pass_num in range(max_refine_passes):
        critique = await _layout_critic(prompt, svg, client)
        if not critique.has_issues:
            logger.info("path_a.critic_clean", pass_num=pass_num + 1)
            return svg

        score = _critique_score(critique)
        if best_score is None or score < best_score:
            best_svg, best_score = svg, score
        else:
            logger.info(
                "path_a.refine_regressed",
                pass_num=pass_num + 1,
                score=score,
                best_score=best_score,
            )

        logger.info(
            "path_a.refine",
            pass_num=pass_num + 1,
            issue_count=len(critique.issues),
            severities=[i.severity for i in critique.issues],
            score=score,
        )
        refine_prompt = build_refine_prompt(prompt, critique.issues)
        svg = await _generate_and_validate(refine_prompt, client)

    # All passes surfaced issues; ship the best critiqued candidate.
    # The final regen is intentionally discarded — we have no critique for it,
    # so we cannot prove it is better than the best we already verified.
    logger.info("path_a.refine_returning_best", best_score=best_score)
    return best_svg


async def _generate_and_validate(prompt: str, client: GeminiClient) -> str:
    """One generation attempt with the existing SVG-validation retry."""
    raw = await client.generate_text(prompt, system=SYSTEM_PROMPT)
    if not isinstance(raw, str):
        raise SVGValidationError("Gemini returned non-string content")

    try:
        return validate_and_canonicalize(inject_defs(_patch_use_dimensions(raw)))
    except SVGValidationError as exc:
        logger.warning("path_a.validation_failed", error=str(exc), attempt=1)
        retry = retry_prompt(prompt, str(exc))
        raw_retry = await client.generate_text(retry, system=SYSTEM_PROMPT)
        if not isinstance(raw_retry, str):
            raise SVGValidationError(
                "Gemini returned non-string content on retry"
            ) from exc
        try:
            return validate_and_canonicalize(inject_defs(_patch_use_dimensions(raw_retry)))
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
