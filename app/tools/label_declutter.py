"""Deterministic label declutter for icon-based figures (Path D).

The LLM backbone often places a `<text>` label in the path of a connector that
was drawn later (e.g. a central entity's label sitting directly under the hub,
right where the downward spoke runs). The strict critic and prompt push against
this, but it still slips through. This pass is the deterministic backstop:
estimate each label's bounding box, and if it collides with a connector `<line>`
or an icon box, nudge the label off the obstacle along the shortest clear
direction (bounded; stays inside the viewBox). Text only moves — no rerouting.

Scope: straight `<line>` connectors and `<image>` / `<rect class="gen-icon">`
boxes as obstacles. Bezier `<path>` connectors are out of scope.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

import structlog

logger = structlog.get_logger(__name__)

# Helvetica/Arial average advance width as a fraction of font-size. Rough but
# good enough to bound a label's footprint for collision testing.
_AVG_CHAR_W = 0.55
_ASCENT = 0.80   # cap height above baseline, × font-size
_DESCENT = 0.22  # descender below baseline, × font-size
_DEFAULT_FONT_SIZE = 16.0

# Nudge search: try these displacements (px) in each axis direction, smallest
# first, and accept the first fully-clear placement.
_NUDGE_STEPS = (8, 16, 24, 32, 44, 56, 70, 88)
_OBSTACLE_PAD = 3.0  # treat collisions within this margin as touching

_GEN_ICON_CLASS = "gen-icon"

Box = tuple[float, float, float, float]
Seg = tuple[float, float, float, float]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _fattr(el: ET.Element, name: str, default: float | None = None) -> float | None:
    raw = el.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _font_size(el: ET.Element) -> float:
    fs = _fattr(el, "font-size")
    if fs and fs > 0:
        return fs
    # crude style="font-size:18px" fallback
    style = el.get("style") or ""
    for part in style.split(";"):
        if "font-size" in part:
            try:
                return float(part.split(":", 1)[1].strip().rstrip("px"))
            except (ValueError, IndexError):
                pass
    return _DEFAULT_FONT_SIZE


def _text_bbox(el: ET.Element) -> Box | None:
    """Estimate the rendered bounding box of a <text> from its attrs + content."""
    x = _fattr(el, "x")
    y = _fattr(el, "y")
    if x is None or y is None:
        return None
    text = "".join(el.itertext())
    n = len(text.strip())
    if n == 0:
        return None
    fs = _font_size(el)
    w = n * fs * _AVG_CHAR_W
    anchor = el.get("text-anchor", "start")
    if anchor == "middle":
        x0 = x - w / 2
    elif anchor == "end":
        x0 = x - w
    else:
        x0 = x
    y0 = y - _ASCENT * fs
    h = (_ASCENT + _DESCENT) * fs
    return (x0, y0, w, h)


def _boxes_overlap(a: Box, b: Box, pad: float) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax < bx + bw + pad
        and ax + aw > bx - pad
        and ay < by + bh + pad
        and ay + ah > by - pad
    )


def _seg_intersects_box(seg: Seg, box: Box, pad: float) -> bool:
    """Liang–Barsky: does segment (x1,y1)-(x2,y2) touch the padded rect?"""
    x1, y1, x2, y2 = seg
    bx, by, bw, bh = box
    xmin, ymin = bx - pad, by - pad
    xmax, ymax = bx + bw + pad, by + bh + pad

    # Trivial: an endpoint inside the rect.
    if (xmin <= x1 <= xmax and ymin <= y1 <= ymax) or (
        xmin <= x2 <= xmax and ymin <= y2 <= ymax
    ):
        return True

    dx, dy = x2 - x1, y2 - y1
    p = (-dx, dx, -dy, dy)
    q = (x1 - xmin, xmax - x1, y1 - ymin, ymax - y1)
    t0, t1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return False  # parallel and outside this slab
        else:
            t = qi / pi
            if pi < 0:
                if t > t1:
                    return False
                if t > t0:
                    t0 = t
            else:
                if t < t0:
                    return False
                if t < t1:
                    t1 = t
    return t0 <= t1


def _icon_boxes(root: ET.Element) -> list[Box]:
    boxes: list[Box] = []
    for el in root.iter():
        local = _local(el.tag)
        if local == "image" or (
            local == "rect" and el.get("class") == _GEN_ICON_CLASS
        ):
            x, y = _fattr(el, "x"), _fattr(el, "y")
            w, h = _fattr(el, "width"), _fattr(el, "height")
            if None not in (x, y, w, h) and w > 0 and h > 0:  # type: ignore[operator]
                boxes.append((x, y, w, h))  # type: ignore[arg-type]
    return boxes


def _segments(root: ET.Element) -> list[Seg]:
    segs: list[Seg] = []
    for el in root.iter():
        if _local(el.tag) != "line":
            continue
        x1, y1 = _fattr(el, "x1"), _fattr(el, "y1")
        x2, y2 = _fattr(el, "x2"), _fattr(el, "y2")
        if None not in (x1, y1, x2, y2):
            segs.append((x1, y1, x2, y2))  # type: ignore[arg-type]
    return segs


def _viewbox(root: ET.Element) -> Box | None:
    vb = root.get("viewBox")
    if not vb:
        return None
    try:
        x, y, w, h = (float(v) for v in vb.replace(",", " ").split())
        return (x, y, w, h)
    except ValueError:
        return None


def _collides(
    bbox: Box, segs: list[Seg], icons: list[Box], others: list[Box], pad: float
) -> bool:
    for seg in segs:
        if _seg_intersects_box(seg, bbox, pad):
            return True
    for ic in icons:
        if _boxes_overlap(bbox, ic, pad):
            return True
    for ob in others:
        if _boxes_overlap(bbox, ob, pad):
            return True
    return False


def _inside_viewbox(bbox: Box, vb: Box | None) -> bool:
    if vb is None:
        return True
    bx, by, bw, bh = bbox
    vx, vy, vw, vh = vb
    return bx >= vx and by >= vy and bx + bw <= vx + vw and by + bh <= vy + vh


def declutter_labels(root: ET.Element, *, pad: float = _OBSTACLE_PAD) -> int:
    """Nudge `<text>` labels off connectors / icon boxes. Mutates `root`.

    Returns the number of labels moved. A label that cannot be cleared within
    the bounded search (or off-canvas) is left where it was — never worsened.
    """
    segs = _segments(root)
    icons = _icon_boxes(root)
    if not segs and not icons:
        return 0
    vb = _viewbox(root)

    texts = [el for el in root.iter() if _local(el.tag) == "text"]
    placed: list[Box] = []  # bboxes of already-resolved labels (collision peers)
    moved = 0

    for el in texts:
        bbox = _text_bbox(el)
        if bbox is None:
            continue
        if not _collides(bbox, segs, icons, placed, pad):
            placed.append(bbox)
            continue

        bx, by, bw, bh = bbox
        best: tuple[float, float, Box] | None = None  # (dx, dy, new_bbox)
        for step in _NUDGE_STEPS:
            for dx, dy in ((0, step), (0, -step), (step, 0), (-step, 0)):
                cand = (bx + dx, by + dy, bw, bh)
                if not _inside_viewbox(cand, vb):
                    continue
                if not _collides(cand, segs, icons, placed, pad):
                    best = (dx, dy, cand)
                    break
            if best is not None:
                break

        if best is None:
            placed.append(bbox)  # give up gracefully; keep original
            continue

        dx, dy, new_bbox = best
        x = _fattr(el, "x") or 0.0
        y = _fattr(el, "y") or 0.0
        el.set("x", f"{x + dx:.1f}")
        el.set("y", f"{y + dy:.1f}")
        placed.append(new_bbox)
        moved += 1

    if moved:
        logger.info("label_declutter.moved", labels=moved)
    return moved
