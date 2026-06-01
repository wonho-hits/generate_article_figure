"""Tests for the SVG validator/sanitizer."""

from __future__ import annotations

import pytest

from app.tools.svg_validate import SVGValidationError, validate_and_canonicalize


VALID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
    '<g id="kinase" data-role="protein">'
    '<rect x="10" y="10" width="100" height="50" fill="#f0f4f8"/>'
    '<text x="60" y="40" font-family="Helvetica, Arial, sans-serif">Kinase</text>'
    "</g>"
    "</svg>"
)


def test_valid_svg_round_trips() -> None:
    out = validate_and_canonicalize(VALID_SVG)
    assert "<svg" in out
    assert 'xmlns="http://www.w3.org/2000/svg"' in out
    assert 'id="kinase"' in out


def test_strips_markdown_code_fence() -> None:
    wrapped = f"```svg\n{VALID_SVG}\n```"
    out = validate_and_canonicalize(wrapped)
    assert "<svg" in out
    assert "```" not in out


def test_strips_xml_code_fence() -> None:
    wrapped = f"```xml\n{VALID_SVG}\n```"
    out = validate_and_canonicalize(wrapped)
    assert "<svg" in out


def test_strips_unlabeled_code_fence() -> None:
    wrapped = f"```\n{VALID_SVG}\n```"
    out = validate_and_canonicalize(wrapped)
    assert "<svg" in out


def test_empty_input_raises() -> None:
    with pytest.raises(SVGValidationError, match="empty"):
        validate_and_canonicalize("")


def test_whitespace_only_raises() -> None:
    with pytest.raises(SVGValidationError):
        validate_and_canonicalize("   \n  ")


def test_malformed_xml_raises() -> None:
    with pytest.raises(SVGValidationError, match="malformed XML"):
        validate_and_canonicalize("<svg><g id='x'></svg>")  # missing close


def test_non_svg_root_raises() -> None:
    with pytest.raises(SVGValidationError, match="root element"):
        validate_and_canonicalize('<html><body><g id="x"/></body></html>')


def test_missing_g_id_raises() -> None:
    no_groups = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
    with pytest.raises(SVGValidationError, match="no <g id"):
        validate_and_canonicalize(no_groups)


def test_g_without_id_does_not_count() -> None:
    only_anonymous = '<svg xmlns="http://www.w3.org/2000/svg"><g><rect/></g></svg>'
    with pytest.raises(SVGValidationError, match="no <g id"):
        validate_and_canonicalize(only_anonymous)


def test_script_element_rejected() -> None:
    bad = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g id="x"><script>alert(1)</script></g></svg>'
    )
    with pytest.raises(SVGValidationError, match="forbidden element <script>"):
        validate_and_canonicalize(bad)


def test_image_element_rejected() -> None:
    bad = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g id="x"><image href="evil.png"/></g></svg>'
    )
    with pytest.raises(SVGValidationError, match="forbidden element <image>"):
        validate_and_canonicalize(bad)


def test_foreignobject_rejected() -> None:
    bad = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g id="x"><foreignObject><div>x</div></foreignObject></g></svg>'
    )
    with pytest.raises(SVGValidationError):
        validate_and_canonicalize(bad)


def test_event_attribute_rejected() -> None:
    bad = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<g id="x" onclick="alert(1)"><rect/></g></svg>'
    )
    with pytest.raises(SVGValidationError, match="forbidden event"):
        validate_and_canonicalize(bad)


def test_style_at_import_rejected() -> None:
    bad = (
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<style>@import url(evil.css);</style>'
        '<g id="x"><rect/></g></svg>'
    )
    with pytest.raises(SVGValidationError, match="@import"):
        validate_and_canonicalize(bad)


def test_no_xmlns_input_gets_xmlns_added() -> None:
    no_ns = '<svg viewBox="0 0 100 100"><g id="x"><rect/></g></svg>'
    out = validate_and_canonicalize(no_ns)
    assert 'xmlns="http://www.w3.org/2000/svg"' in out


# ── Path D: data-URI <image> exception (allow_data_image) ──────────────────

# 1x1 transparent PNG.
_PNG_1PX = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _svg_with_image(href: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="icon" data-role="entity">'
        f'<image x="10" y="10" width="50" height="50" href="{href}"/>'
        "</g></svg>"
    )


def test_data_image_allowed_when_opted_in() -> None:
    svg = _svg_with_image(f"data:image/png;base64,{_PNG_1PX}")
    out = validate_and_canonicalize(svg, allow_data_image=True)
    assert "<image" in out


def test_data_image_still_forbidden_by_default() -> None:
    """Back-compat: Path A must keep rejecting <image> outright."""
    svg = _svg_with_image(f"data:image/png;base64,{_PNG_1PX}")
    with pytest.raises(SVGValidationError, match="forbidden element <image>"):
        validate_and_canonicalize(svg)


def test_http_image_href_rejected_even_when_opted_in() -> None:
    svg = _svg_with_image("https://evil.example/x.png")
    with pytest.raises(SVGValidationError, match="data:image"):
        validate_and_canonicalize(svg, allow_data_image=True)


def test_data_html_href_rejected_even_when_opted_in() -> None:
    svg = _svg_with_image("data:text/html;base64,PHNjcmlwdD4=")
    with pytest.raises(SVGValidationError, match="data:image"):
        validate_and_canonicalize(svg, allow_data_image=True)


def test_image_without_href_rejected_when_opted_in() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<g id="icon"><image x="10" y="10" width="50" height="50"/></g></svg>'
    )
    with pytest.raises(SVGValidationError, match="data:image"):
        validate_and_canonicalize(svg, allow_data_image=True)


def test_xlink_href_data_image_allowed() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 800 600">'
        '<g id="icon"><image x="10" y="10" width="50" height="50" '
        f'xlink:href="data:image/jpeg;base64,{_PNG_1PX}"/></g></svg>'
    )
    out = validate_and_canonicalize(svg, allow_data_image=True)
    assert "image" in out
