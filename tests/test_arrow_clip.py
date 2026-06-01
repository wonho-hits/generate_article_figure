"""Tests for deterministic connector clipping (Path D arrow attachment)."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from app.tools.arrow_clip import (
    DEFAULT_GAP,
    DEFAULT_INSIDE_MARGIN,
    _contains,
    clip_connectors_to_icons,
)

SVG_NS = "http://www.w3.org/2000/svg"


def _svg(*body: str) -> ET.Element:
    return ET.fromstring(
        f'<svg xmlns="{SVG_NS}" viewBox="0 0 1600 900">{"".join(body)}</svg>'
    )


def _line(el: ET.Element) -> tuple[float, float, float, float]:
    ln = next(e for e in el.iter() if e.tag.endswith("line"))
    return (
        float(ln.get("x1")),  # type: ignore[arg-type]
        float(ln.get("y1")),  # type: ignore[arg-type]
        float(ln.get("x2")),  # type: ignore[arg-type]
        float(ln.get("y2")),  # type: ignore[arg-type]
    )


def test_no_icons_no_change() -> None:
    root = _svg('<line x1="0" y1="0" x2="100" y2="100"/>')
    assert clip_connectors_to_icons(root) == 0
    assert _line(root) == (0.0, 0.0, 100.0, 100.0)


def test_endpoint_outside_box_untouched() -> None:
    root = _svg(
        '<image x="700" y="305" width="200" height="190" href="d"/>'
        '<line x1="100" y1="100" x2="300" y2="300"/>'  # nowhere near the box
    )
    assert clip_connectors_to_icons(root) == 0
    assert _line(root) == (100.0, 100.0, 300.0, 300.0)


def test_tail_buried_in_hub_pushed_to_edge() -> None:
    # Hub box [700..900]x[305..495]; tail at center (800,400) → up to node above.
    root = _svg(
        '<image x="700" y="305" width="200" height="190" href="hub"/>'
        '<line x1="800" y1="400" x2="800" y2="50"/>'
    )
    adjusted = clip_connectors_to_icons(root)
    x1, y1, x2, y2 = _line(root)
    # Start was inside hub → must now sit just ABOVE the hub top edge (y<305).
    assert adjusted == 1
    assert x1 == 800.0
    assert y1 < 305.0
    assert abs(y1 - (305.0 - DEFAULT_GAP)) < 0.2
    # End was already outside any box → untouched.
    assert (x2, y2) == (800.0, 50.0)


def test_both_endpoints_clipped_between_two_boxes() -> None:
    # Hub center (800,400); node box [750..850]x[50..150], center (800,100).
    root = _svg(
        '<image x="700" y="305" width="200" height="190" href="hub"/>'
        '<image x="750" y="50" width="100" height="100" href="node"/>'
        '<line x1="800" y1="400" x2="800" y2="100"/>'
    )
    adjusted = clip_connectors_to_icons(root)
    x1, y1, x2, y2 = _line(root)
    assert adjusted == 2
    # Tail just above hub top (305), head just below node bottom (150).
    assert y1 < 305.0 and abs(y1 - (305.0 - DEFAULT_GAP)) < 0.2
    assert y2 > 150.0 and abs(y2 - (150.0 + DEFAULT_GAP)) < 0.2
    # Tail (near hub, larger y ≈299) sits below head (near node, smaller y ≈156);
    # the connector still spans the gap between the two boxes.
    assert y1 > y2


def test_diagonal_endpoint_clips_along_line_direction() -> None:
    # Hub center (800,400) → diagonal to (1200,200).
    root = _svg(
        '<image x="700" y="305" width="200" height="190" href="hub"/>'
        '<line x1="800" y1="400" x2="1200" y2="200"/>'
    )
    clip_connectors_to_icons(root)
    x1, y1, x2, y2 = _line(root)
    # New tail must be outside the hub box on the line toward (1200,200):
    # x>900 (right edge) or y<305 (top edge).
    assert not _contains((700, 305, 200, 190), x1, y1, DEFAULT_INSIDE_MARGIN)
    assert x1 > 800 and y1 < 400  # moved up-right toward the target


def test_unfilled_gen_icon_rect_also_clips() -> None:
    # If icon generation failed, the gen-icon rect remains and still bounds arrows.
    root = _svg(
        '<rect class="gen-icon" data-desc="x" x="700" y="305" width="200" height="190"/>'
        '<line x1="800" y1="400" x2="800" y2="50"/>'
    )
    assert clip_connectors_to_icons(root) == 1
    _, y1, _, _ = _line(root)
    assert y1 < 305.0


def test_contains_respects_margin() -> None:
    box = (700.0, 305.0, 200.0, 190.0)
    assert _contains(box, 800.0, 400.0, DEFAULT_INSIDE_MARGIN)
    # On the edge → not "inside" by margin.
    assert not _contains(box, 700.0, 400.0, DEFAULT_INSIDE_MARGIN)
    assert not _contains(box, 901.0, 400.0, DEFAULT_INSIDE_MARGIN)
