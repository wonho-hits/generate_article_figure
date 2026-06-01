"""Path D tool: text → mixed vector-backbone + generated-raster-icon SVG.

The LLM emits a vector backbone (arrows, labels, compartments) where every
biological entity is a `<rect class="gen-icon" data-desc="...">` placeholder.
This module fills each placeholder: generate the icon with Gemini Image, strip
its background to a tight transparent PNG, and swap the `<rect>` for an
`<image>` carrying a base64 data URI — fitted inside the reserved box,
aspect-preserved. The result is a single SVG mixing crisp vector (backbone) and
raster (icons).

See [[docs/progress/260601_path_d_mixed_vector_raster.md]] and the probes
[[analyze/260601_path_d_icon_consistency_probe.py]] /
[[analyze/260601_path_d_icon_postprocess_size.py]].
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import math
from typing import Callable
from xml.etree import ElementTree as ET

import structlog

from app.agent.prompts.gen_icon import ICON_STYLE_PREFIX
from app.agent.prompts.mixed_schematic import (
    SYSTEM_PROMPT,
    build_refine_prompt,
    retry_prompt,
)
from app.clients.gemini import GeminiClient
from app.tools.arrow_clip import clip_connectors_to_icons
from app.tools.icon_postprocess import postprocess_icon
from app.tools.label_declutter import declutter_labels
from app.tools.layout_review import critique_score, vision_layout_critic
from app.tools.svg_validate import (
    SVG_NS,
    SVGValidationError,
    validate_and_canonicalize,
)

logger = structlog.get_logger(__name__)

ProgressCallback = Callable[[str, float], None]

DEFAULT_MAX_REFINE_PASSES = 3
"""Vision-critic + backbone-regen cycles after the initial assembly.

0 = no critic (fastest). Each pass re-lays-out the VECTOR BACKBONE only — the
refine prompt freezes data-desc strings, so the icon cache hits and icons are
NOT regenerated (no extra image-gen cost, no style drift). Cost per pass ≈ one
backbone text-gen + one vision-critic call. Default 3 gives the strict
professor-level critic room to converge; keep-best backstops if it doesn't.
"""

_GEN_ICON_CLASS = "gen-icon"
_IMAGE_TAG = f"{{{SVG_NS}}}image"

# Process-level icon cache: sha256(data-desc) → post-processed PNG bytes.
# Same entity description (within or across figures) reuses the generated icon
# instead of paying another image-generation call. Bounded only by process
# lifetime; figures are small so unbounded growth is not a concern in v1.
_ICON_CACHE: dict[str, bytes] = {}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _desc_key(desc: str) -> str:
    return hashlib.sha256(desc.strip().encode("utf-8")).hexdigest()


def _find_gen_icons(root: ET.Element) -> list[ET.Element]:
    """All <rect class="gen-icon"> elements, in document order."""
    return [
        el
        for el in root.iter()
        if _local(el.tag) == "rect" and el.get("class") == _GEN_ICON_CLASS
    ]


ICON_AREA_FILL = 0.78
"""Fraction of a placeholder box's area a fitted icon should occupy.

Sizing by AREA (not longest-side) is what makes a set of icons look balanced:
equal-size boxes → equal icon area regardless of each icon's aspect ratio, so a
wide/flat icon no longer reads as 'tiny' next to a square one.
"""

ICON_MAX_OVERFLOW = 1.18
"""How far an icon may exceed its reserved box (per dimension) to hit the target
area. Lets wide/flat icons stay visually present instead of being shrunk into
slivers; the box has built-in inter-group clearance (≥30px) to absorb it."""


def _fit_box(
    bx: float,
    by: float,
    bw: float,
    bh: float,
    aspect: float,
    *,
    area_fill: float = ICON_AREA_FILL,
    max_overflow: float = ICON_MAX_OVERFLOW,
) -> tuple[float, float, float, float]:
    """Size an icon of the given aspect to a consistent VISUAL AREA inside box
    (bx,by,bw,bh), centered. Aspect preserved (no stretch).

    Equal-size boxes yield equal icon area, so icons of differing aspect read as
    balanced. Width/height may modestly exceed the box (up to `max_overflow`) so
    flat icons aren't reduced to slivers; extreme aspects clamp to the overflow
    cap rather than blowing up. Returns (x, y, w, h).
    """
    target_area = bw * bh * area_fill
    h = math.sqrt(target_area / aspect) if aspect > 0 else bh
    w = h * aspect

    max_w = bw * max_overflow
    max_h = bh * max_overflow
    if w > max_w:
        w = max_w
        h = w / aspect
    if h > max_h:
        h = max_h
        w = h * aspect

    x = bx + (bw - w) / 2
    y = by + (bh - h) / 2
    return x, y, w, h


async def _make_icon(
    desc: str, client: GeminiClient
) -> "tuple[bytes, float]":
    """Generate + post-process one icon. Returns (png_bytes, aspect). Cached."""
    key = _desc_key(desc)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(cached)) as im:
            return cached, (im.width / im.height if im.height else 1.0)

    raw = await client.generate_image(f"{ICON_STYLE_PREFIX}{desc}")
    processed = postprocess_icon(raw)
    _ICON_CACHE[key] = processed.png_bytes
    return processed.png_bytes, processed.aspect


def _attr_float(el: ET.Element, name: str) -> float | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


async def generate_mixed_figure(
    prompt: str,
    *,
    client: GeminiClient | None = None,
    max_refine_passes: int = DEFAULT_MAX_REFINE_PASSES,
    progress: ProgressCallback | None = None,
) -> str:
    """Generate a Path D figure: vector backbone + generated raster icons.

    Assembles the figure (backbone + filled icons), then runs a vision-based
    layout critic up to `max_refine_passes` times. If the critic is clean,
    ships immediately. Otherwise re-lays-out the backbone with concrete
    feedback — the refine prompt freezes data-desc strings so the icon cache
    hits and icons are NOT regenerated. Keep-best: ships the lowest
    severity-weighted candidate if none fully converge (a regen can score
    worse than its predecessor).

    `progress` is an optional `(message, fraction)` callback (no-op if None).
    """
    if not prompt or not prompt.strip():
        raise ValueError("prompt is empty")

    def _emit(msg: str, frac: float) -> None:
        if progress is not None:
            progress(msg, frac)

    client = client or GeminiClient()
    total_steps = 1 + max_refine_passes * 2  # initial + (critic + regen) × passes
    step = 0

    def _frac() -> float:
        return min(0.99, step / total_steps) if total_steps > 0 else 0.99

    _emit("Assembling figure…", _frac())
    svg = await _assemble_mixed(prompt, client)
    step += 1

    best_svg = svg
    best_score: int | None = None

    for pass_num in range(max_refine_passes):
        _emit(f"Layout critic — pass {pass_num + 1}…", _frac())
        critique = await vision_layout_critic(prompt, svg, client)
        step += 1
        if not critique.has_issues:
            logger.info("path_d.critic_clean", pass_num=pass_num + 1)
            _emit(f"Pass {pass_num + 1}: clean ✓ — shipping", 1.0)
            return svg

        score = critique_score(critique)
        if best_score is None or score < best_score:
            best_svg, best_score = svg, score
        else:
            logger.info(
                "path_d.refine_regressed",
                pass_num=pass_num + 1,
                score=score,
                best_score=best_score,
            )
        logger.info(
            "path_d.refine",
            pass_num=pass_num + 1,
            issue_count=len(critique.issues),
            severities=[i.severity for i in critique.issues],
            score=score,
        )
        _emit(
            f"Pass {pass_num + 1}: {len(critique.issues)} issues (score {score}) — refining layout",
            _frac(),
        )
        refine = build_refine_prompt(prompt, critique.issues)
        svg = await _assemble_mixed(refine, client)
        step += 1

    logger.info("path_d.refine_returning_best", best_score=best_score)
    _emit(f"Done — shipping best candidate (score {best_score})", 1.0)
    return best_svg


async def _assemble_mixed(prompt: str, client: GeminiClient) -> str:
    """One full Path D assembly: backbone → fill icons → validate.

    1. Gemini emits the backbone SVG with gen-icon placeholders.
    2. Validate the backbone (no <image> yet).
    3. Generate + bg-strip an icon per placeholder (parallel; desc-cached).
    4. Replace each placeholder <rect> with a fitted <image> data URI.
    5. Final validate with the data-URI <image> exception.

    A single icon failure leaves its placeholder untouched (harmless rect) and
    the rest proceed. No placeholders → the validated backbone is returned as
    plain vector.
    """
    backbone = await _generate_and_validate_backbone(prompt, client)

    root = ET.fromstring(backbone)
    placeholders = _find_gen_icons(root)
    if not placeholders:
        logger.warning("path_d.no_placeholders")
        return backbone

    logger.info("path_d.placeholders", count=len(placeholders))
    descs = [el.get("data-desc") or "" for el in placeholders]
    results = await asyncio.gather(
        *(_make_icon(d, client) for d in descs),
        return_exceptions=True,
    )

    filled = 0
    for el, desc, result in zip(placeholders, descs, results):
        if isinstance(result, BaseException):
            logger.warning("path_d.icon_failed", desc=desc[:60], error=str(result))
            continue
        png_bytes, aspect = result
        bx = _attr_float(el, "x")
        by = _attr_float(el, "y")
        bw = _attr_float(el, "width")
        bh = _attr_float(el, "height")
        if None in (bx, by, bw, bh) or bw <= 0 or bh <= 0:
            logger.warning("path_d.bad_placeholder_box", desc=desc[:60])
            continue
        x, y, w, h = _fit_box(bx, by, bw, bh, aspect)
        data_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")

        # Mutate the rect in place into an <image> (position preserved).
        el.tag = _IMAGE_TAG
        el.attrib.clear()
        el.set("x", f"{x:.1f}")
        el.set("y", f"{y:.1f}")
        el.set("width", f"{w:.1f}")
        el.set("height", f"{h:.1f}")
        el.set("preserveAspectRatio", "xMidYMid meet")
        el.set("href", data_uri)
        filled += 1

    logger.info("path_d.icons_filled", filled=filled, total=len(placeholders))

    # Deterministic passes (no LLM, no variance):
    #  1. clip connectors to icon boundaries (tails/heads not buried in icons).
    #  2. nudge labels off any connector / icon they overlap.
    # Order matters: declutter reads the already-clipped connector geometry.
    clip_connectors_to_icons(root)
    declutter_labels(root)

    merged = ET.tostring(root, encoding="unicode")
    return validate_and_canonicalize(merged, allow_data_image=True)


async def _generate_and_validate_backbone(prompt: str, client: GeminiClient) -> str:
    """One backbone generation with a single validation retry.

    The backbone has no <image> yet (only gen-icon <rect> placeholders), so it
    validates with the default allow_data_image=False.
    """
    raw = await client.generate_text(prompt, system=SYSTEM_PROMPT)
    if not isinstance(raw, str):
        raise SVGValidationError("Gemini returned non-string content")
    try:
        return validate_and_canonicalize(raw)
    except SVGValidationError as exc:
        logger.warning("path_d.backbone_validation_failed", error=str(exc), attempt=1)
        retry = retry_prompt(prompt, str(exc))
        raw_retry = await client.generate_text(retry, system=SYSTEM_PROMPT)
        if not isinstance(raw_retry, str):
            raise SVGValidationError(
                "Gemini returned non-string content on retry"
            ) from exc
        return validate_and_canonicalize(raw_retry)
