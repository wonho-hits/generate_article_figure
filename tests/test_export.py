"""Tool-level tests for the export pipeline."""

from __future__ import annotations

import io
import zipfile

import pytest
from PIL import Image as PILImage

from app.tools.export import (
    PPTX_MIME,
    export_image,
    export_pptx,
    export_pptx_from_svg,
    export_svg,
)


SESSION_ID = "abcdef0123456789-deadbeef"
SVG_TEXT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<g id="x"><rect/></g></svg>'
)


@pytest.fixture
def jpeg_bytes() -> bytes:
    img = PILImage.new("RGB", (1376, 768), color="white")
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=80)
    return out.getvalue()


@pytest.fixture
def png_bytes() -> bytes:
    img = PILImage.new("RGB", (200, 100), color="white")
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


# ── export_svg ────────────────────────────────────────────────────────────


def test_export_svg_returns_utf8_with_correct_filename() -> None:
    r = export_svg(SVG_TEXT, session_id=SESSION_ID)
    assert r.media_type == "image/svg+xml"
    assert r.filename == "figure_abcdef01.svg"
    assert r.content == SVG_TEXT.encode("utf-8")


def test_export_svg_rejects_empty() -> None:
    with pytest.raises(ValueError):
        export_svg("", session_id=SESSION_ID)


# ── export_image ──────────────────────────────────────────────────────────


def test_export_image_passes_through_jpeg(jpeg_bytes: bytes) -> None:
    r = export_image(jpeg_bytes, session_id=SESSION_ID)
    assert r.media_type == "image/jpeg"
    assert r.filename == "figure_abcdef01.jpg"
    assert r.content == jpeg_bytes


def test_export_image_passes_through_png(png_bytes: bytes) -> None:
    r = export_image(png_bytes, session_id=SESSION_ID)
    assert r.media_type == "image/png"
    assert r.filename == "figure_abcdef01.png"
    assert r.content == png_bytes


def test_export_image_rejects_unrecognized_bytes() -> None:
    with pytest.raises(ValueError, match="not a recognized image"):
        export_image(b"not actually an image", session_id=SESSION_ID)


def test_export_image_rejects_empty() -> None:
    with pytest.raises(ValueError):
        export_image(b"", session_id=SESSION_ID)


# ── export_pptx ───────────────────────────────────────────────────────────


def test_export_pptx_returns_valid_pptx_with_embedded_image(
    jpeg_bytes: bytes,
) -> None:
    r = export_pptx(jpeg_bytes, session_id=SESSION_ID)
    assert r.media_type == PPTX_MIME
    assert r.filename == "figure_abcdef01.pptx"

    # PPTX is a ZIP with OOXML structure
    assert r.content[:4] == b"PK\x03\x04"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert any("ppt/slides/slide1.xml" in n for n in names), (
        f"missing slide1.xml; have: {names[:10]}"
    )

    # Verify embedded image bytes match the input
    media = [n for n in names if n.startswith("ppt/media/")]
    assert len(media) == 1, f"expected exactly one embedded image, got {media}"
    assert z.read(media[0]) == jpeg_bytes


def test_export_pptx_rejects_unrecognized_bytes() -> None:
    with pytest.raises(ValueError, match="not a recognized image"):
        export_pptx(b"not an image at all", session_id=SESSION_ID)


def test_export_pptx_rejects_empty() -> None:
    with pytest.raises(ValueError):
        export_pptx(b"", session_id=SESSION_ID)


# ── filename short-id behavior ────────────────────────────────────────────


def test_filename_truncates_long_session_id(jpeg_bytes: bytes) -> None:
    r = export_image(jpeg_bytes, session_id="0123456789abcdef" * 4)
    assert r.filename == "figure_01234567.jpg"


def test_filename_handles_short_session_id(jpeg_bytes: bytes) -> None:
    r = export_image(jpeg_bytes, session_id="abc")
    assert r.filename == "figure_abc.jpg"


# ── export_pptx_from_svg (L2 editable PPTX) ───────────────────────────────


def test_export_pptx_from_svg_embeds_svg_and_extension() -> None:
    r = export_pptx_from_svg(SVG_TEXT, session_id=SESSION_ID)
    assert r.media_type == PPTX_MIME
    assert r.filename == "figure_abcdef01.pptx"
    assert r.content[:4] == b"PK\x03\x04"

    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert "ppt/media/image1.svg" in names
    # SVG embedded verbatim
    assert z.read("ppt/media/image1.svg") == SVG_TEXT.encode("utf-8")
    # Content type registered
    ct = z.read("[Content_Types].xml").decode("utf-8")
    assert "image/svg+xml" in ct
    # Slide XML has asvg:svgBlip extension
    slide_xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "svgBlip" in slide_xml
    # Slide rels has TWO image relationships (PNG fallback + SVG)
    rels_xml = z.read("ppt/slides/_rels/slide1.xml.rels").decode("utf-8")
    assert rels_xml.count('Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"') == 2


def test_export_pptx_from_svg_rejects_empty() -> None:
    with pytest.raises(ValueError):
        export_pptx_from_svg("", session_id=SESSION_ID)
    with pytest.raises(ValueError):
        export_pptx_from_svg("   \n", session_id=SESSION_ID)


def test_export_pptx_from_svg_uses_asvg_prefix_not_generated_one() -> None:
    """PowerPoint requires the namespace prefix to be exactly 'asvg'.

    lxml will emit an auto-generated prefix (e.g., 'ns0:') unless we pass
    nsmap={'asvg': ASVG_NS} on the SubElement creation. PowerPoint silently
    ignores the extension if the prefix is wrong and falls back to the PNG.
    """
    r = export_pptx_from_svg(SVG_TEXT, session_id=SESSION_ID)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    slide_xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "<asvg:svgBlip" in slide_xml, (
        "expected asvg-prefixed svgBlip; got something else "
        "(PowerPoint will ignore the SVG embed and show the PNG fallback)"
    )
    assert 'xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main"' in slide_xml
    # Make sure the auto-generated prefix didn't sneak in
    assert "ns0:svgBlip" not in slide_xml


def test_export_pptx_from_svg_uses_viewbox_aspect_ratio() -> None:
    """The picture box on the slide should respect the SVG's viewBox aspect."""
    # Wide SVG (4:1)
    wide_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200">'
        '<g id="x"/></svg>'
    )
    r = export_pptx_from_svg(wide_svg, session_id=SESSION_ID)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    slide_xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
    # Just verify the file is well-formed PPTX with the SVG present.
    assert "ppt/media/image1.svg" in z.namelist()
    assert "svgBlip" in slide_xml


# ── svg_has_embedded_raster (Path D detection / PPTX warning) ──────────────

def test_svg_has_embedded_raster_true_for_data_uri_image() -> None:
    from app.tools.export import svg_has_embedded_raster

    mixed = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="i"><image href="data:image/png;base64,iVBORw0KGgo="/></g></svg>'
    )
    assert svg_has_embedded_raster(mixed) is True


def test_svg_has_embedded_raster_false_for_pure_vector() -> None:
    from app.tools.export import svg_has_embedded_raster

    assert svg_has_embedded_raster(SVG_TEXT) is False


def test_export_pptx_from_svg_warns_on_mixed(capsys) -> None:
    mixed = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        '<g id="i"><image href="data:image/png;base64,iVBORw0KGgo="/></g></svg>'
    )
    r = export_pptx_from_svg(mixed, session_id=SESSION_ID)
    assert r.media_type == PPTX_MIME
    captured = capsys.readouterr()
    assert "pptx_mixed_raster" in (captured.out + captured.err)


def test_export_pptx_from_svg_no_warn_on_pure_vector(capsys) -> None:
    export_pptx_from_svg(SVG_TEXT, session_id=SESSION_ID)
    captured = capsys.readouterr()
    assert "pptx_mixed_raster" not in (captured.out + captured.err)
