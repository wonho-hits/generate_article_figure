"""Deterministic connector clipping for icon-based figures (Path D).

The LLM backbone draws connector `<line>`s center-to-center between entities.
Once the gen-icon placeholders are filled with `<image>` icons, those endpoints
sit *inside* the icon boxes — so arrow tails and arrowheads are buried under the
artwork (see [[docs/progress/260601_path_d_arrow_clipping.md]]).

This pass clips every `<line>` endpoint that falls inside an icon box back to the
box boundary plus a small gap, along the line's own direction. The result: tails
start just outside the source icon, heads (with their marker) land just outside
the target icon — visible, not buried. Pure geometry, no LLM, no variance.

Scope: straight `<line>` connectors against `<image>` and unfilled
`<rect class="gen-icon">` boxes. Bezier `<path>` routing is out of scope for v1.
"""

from __future__ import annotations

import math
from xml.etree import ElementTree as ET

import structlog

logger = structlog.get_logger(__name__)

# How far outside the icon boundary an endpoint is pushed, in user units. Large
# enough that an arrowhead marker (≈6px) clears the artwork; small enough that
# the connector still reads as touching the icon.
DEFAULT_GAP = 6.0

# An endpoint must be inside a box by more than this margin to be clipped. Keeps
# the pass from nudging connectors that already terminate cleanly at an edge.
DEFAULT_INSIDE_MARGIN = 2.0

_GEN_ICON_CLASS = "gen-icon"

Box = tuple[float, float, float, float]  # (x, y, w, h)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr_float(el: ET.Element, name: str) -> float | None:
    raw = el.get(name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _icon_boxes(root: ET.Element) -> list[Box]:
    """All icon bounding boxes: filled `<image>` plus unfilled gen-icon rects."""
    boxes: list[Box] = []
    for el in root.iter():
        local = _local(el.tag)
        is_image = local == "image"
        is_gen_rect = local == "rect" and el.get("class") == _GEN_ICON_CLASS
        if not (is_image or is_gen_rect):
            continue
        x = _attr_float(el, "x")
        y = _attr_float(el, "y")
        w = _attr_float(el, "width")
        h = _attr_float(el, "height")
        if None in (x, y, w, h) or w <= 0 or h <= 0:  # type: ignore[operator]
            continue
        boxes.append((x, y, w, h))  # type: ignore[arg-type]
    return boxes


def _contains(box: Box, px: float, py: float, margin: float) -> bool:
    bx, by, bw, bh = box
    return (bx + margin <= px <= bx + bw - margin) and (
        by + margin <= py <= by + bh - margin
    )


def _exit_point(
    px: float, py: float, qx: float, qy: float, box: Box, gap: float
) -> tuple[float, float]:
    """From p (inside box) moving toward q, return the box-boundary crossing
    pushed `gap` further along the p→q direction (i.e. just outside the box)."""
    bx, by, bw, bh = box
    dx, dy = qx - px, qy - py
    if dx == 0 and dy == 0:
        return px, py

    eps = 1e-6
    ts: list[float] = []
    for edge_x in (bx, bx + bw):
        if dx != 0:
            t = (edge_x - px) / dx
            if t > 0:
                yy = py + t * dy
                if by - eps <= yy <= by + bh + eps:
                    ts.append(t)
    for edge_y in (by, by + bh):
        if dy != 0:
            t = (edge_y - py) / dy
            if t > 0:
                xx = px + t * dx
                if bx - eps <= xx <= bx + bw + eps:
                    ts.append(t)
    if not ts:
        return px, py

    t = min(ts)
    ix, iy = px + t * dx, py + t * dy
    length = math.hypot(dx, dy)
    if length == 0:
        return ix, iy
    ux, uy = dx / length, dy / length
    return ix + ux * gap, iy + uy * gap


def _push_out(
    px: float,
    py: float,
    ox: float,
    oy: float,
    boxes: list[Box],
    *,
    gap: float,
    margin: float,
    max_iter: int = 4,
) -> tuple[float, float]:
    """Push point (px,py) out of any box that contains it, moving toward the
    other endpoint (ox,oy). Iterates to handle overlapping boxes."""
    cur = (px, py)
    for _ in range(max_iter):
        containing = [b for b in boxes if _contains(b, cur[0], cur[1], margin)]
        if not containing:
            break
        # Pick the box that requires the largest push so we exit the deepest
        # overlap first; remaining boxes are handled on the next iteration.
        best: tuple[float, tuple[float, float]] | None = None
        for b in containing:
            np = _exit_point(cur[0], cur[1], ox, oy, b, gap)
            moved = math.hypot(np[0] - cur[0], np[1] - cur[1])
            if best is None or moved > best[0]:
                best = (moved, np)
        assert best is not None
        cur = best[1]
    return cur


def clip_connectors_to_icons(
    root: ET.Element,
    *,
    gap: float = DEFAULT_GAP,
    inside_margin: float = DEFAULT_INSIDE_MARGIN,
) -> int:
    """Clip `<line>` endpoints buried inside icon boxes back to the boundary.

    Mutates `root` in place. Returns the number of endpoints adjusted.
    """
    boxes = _icon_boxes(root)
    if not boxes:
        return 0

    adjusted = 0
    for el in root.iter():
        if _local(el.tag) != "line":
            continue
        x1 = _attr_float(el, "x1")
        y1 = _attr_float(el, "y1")
        x2 = _attr_float(el, "x2")
        y2 = _attr_float(el, "y2")
        if None in (x1, y1, x2, y2):
            continue

        # Start endpoint: push toward the end endpoint.
        nx1, ny1 = _push_out(
            x1, y1, x2, y2, boxes, gap=gap, margin=inside_margin  # type: ignore[arg-type]
        )
        # End endpoint: push toward the start endpoint.
        nx2, ny2 = _push_out(
            x2, y2, x1, y1, boxes, gap=gap, margin=inside_margin  # type: ignore[arg-type]
        )

        if (nx1, ny1) != (x1, y1):
            el.set("x1", f"{nx1:.1f}")
            el.set("y1", f"{ny1:.1f}")
            adjusted += 1
        if (nx2, ny2) != (x2, y2):
            el.set("x2", f"{nx2:.1f}")
            el.set("y2", f"{ny2:.1f}")
            adjusted += 1

    if adjusted:
        logger.info("arrow_clip.adjusted", endpoints=adjusted, boxes=len(boxes))
    return adjusted
