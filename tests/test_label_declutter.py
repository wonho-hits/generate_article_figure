"""Tests for deterministic label declutter (Path D arrow↔text overlap)."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from app.tools.label_declutter import (
    _seg_intersects_box,
    _text_bbox,
    declutter_labels,
)

SVG_NS = "http://www.w3.org/2000/svg"


def _svg(*body: str, vb: str = "0 0 1600 900") -> ET.Element:
    return ET.fromstring(f'<svg xmlns="{SVG_NS}" viewBox="{vb}">{"".join(body)}</svg>')


def _text(root: ET.Element) -> ET.Element:
    return next(e for e in root.iter() if e.tag.endswith("text"))


def test_seg_intersects_box_basic() -> None:
    box = (100.0, 100.0, 50.0, 20.0)
    assert _seg_intersects_box((90, 110, 200, 110), box, 0)  # horizontal through
    assert _seg_intersects_box((125, 0, 125, 500), box, 0)  # vertical through
    assert not _seg_intersects_box((0, 0, 10, 10), box, 0)  # far away
    assert not _seg_intersects_box((0, 300, 500, 300), box, 0)  # below


def test_text_bbox_middle_anchor() -> None:
    root = _svg(
        '<text x="800" y="570" font-size="18" text-anchor="middle">Tumor Cell</text>'
    )
    bbox = _text_bbox(_text(root))
    assert bbox is not None
    x0, y0, w, h = bbox
    # centered on x=800
    assert abs((x0 + w / 2) - 800) < 0.01
    assert w > 0 and h > 0


def test_no_obstacles_no_move() -> None:
    root = _svg('<text x="100" y="100" font-size="16">free label</text>')
    assert declutter_labels(root) == 0


def test_label_on_vertical_arrow_gets_moved() -> None:
    # "Tumor Cell" centered at (800,570); a vertical spoke runs down x=800.
    root = _svg(
        '<image x="700" y="362" width="200" height="176" href="hub"/>'
        '<text x="800" y="570" font-size="18" text-anchor="middle">Tumor Cell</text>'
        '<line x1="800" y1="550" x2="800" y2="700"/>'
    )
    before_x = float(_text(root).get("x"))  # type: ignore[arg-type]
    before_y = float(_text(root).get("y"))  # type: ignore[arg-type]
    moved = declutter_labels(root)
    assert moved == 1
    el = _text(root)
    after = (float(el.get("x")), float(el.get("y")))  # type: ignore[arg-type]
    assert after != (before_x, before_y)
    # After moving, the label bbox must no longer intersect the line.
    bbox = _text_bbox(el)
    assert bbox is not None
    assert not _seg_intersects_box((800, 550, 800, 700), bbox, 3.0)


def test_label_overlapping_icon_moved_off() -> None:
    root = _svg(
        '<image x="500" y="500" width="120" height="120" href="i"/>'
        '<text x="560" y="560" font-size="16" text-anchor="middle">Inside</text>'
    )
    assert declutter_labels(root) == 1


def test_unmovable_label_left_unchanged() -> None:
    # Label boxed in by a viewbox so tight no nudge stays inside → keep original.
    root = _svg(
        '<line x1="0" y1="10" x2="100" y2="10"/>'
        '<text x="10" y="12" font-size="40" text-anchor="start">BIG</text>',
        vb="0 0 100 20",
    )
    x0 = _text(root).get("x")
    y0 = _text(root).get("y")
    declutter_labels(root)  # should not crash; likely can't place
    # original preserved (no partial move that worsens)
    el = _text(root)
    assert el.get("x") == x0 and el.get("y") == y0


def test_no_lines_no_icons_returns_zero() -> None:
    root = _svg('<text x="10" y="10">a</text>')
    assert declutter_labels(root) == 0
