"""Route-level tests for GET /export/{session_id}/{format}."""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image as PILImage

from app.main import app


SVG_TEXT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<g id="x"><rect/></g></svg>'
)


@pytest.fixture
def jpeg_bytes() -> bytes:
    img = PILImage.new("RGB", (300, 200), color="white")
    out = io.BytesIO()
    img.save(out, format="JPEG")
    return out.getvalue()


def _make_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _make_svg_session() -> str:
    sessions = app.state.session_store
    entry = await sessions.create()
    await sessions.update(entry.session_id, SVG_TEXT)
    return entry.session_id


async def _make_raster_session(image_bytes: bytes) -> str:
    sessions = app.state.session_store
    entry = await sessions.create()
    await sessions.update(entry.session_id, image_bytes)
    return entry.session_id


async def _make_empty_session() -> str:
    sessions = app.state.session_store
    entry = await sessions.create()
    return entry.session_id


# ── happy paths ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_svg_for_svg_session() -> None:
    sid = await _make_svg_session()
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/svg")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "filename=" in r.headers["content-disposition"]
    assert "<svg" in r.text


@pytest.mark.asyncio
async def test_get_pptx_for_raster_session(jpeg_bytes: bytes) -> None:
    sid = await _make_raster_session(jpeg_bytes)
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/pptx")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert r.content[:4] == b"PK\x03\x04"


@pytest.mark.asyncio
async def test_get_image_for_raster_session(jpeg_bytes: bytes) -> None:
    sid = await _make_raster_session(jpeg_bytes)
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/image")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content == jpeg_bytes
    assert ".jpg" in r.headers["content-disposition"]


# ── cross-format mismatch ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pptx_for_svg_session_returns_svg_embedded_pptx() -> None:
    """SVG session → PPTX with embedded SVG (L2 editability)."""
    import zipfile

    sid = await _make_svg_session()
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/pptx")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert r.content[:4] == b"PK\x03\x04"

    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert "ppt/media/image1.svg" in names
    # The embedded SVG should be the session SVG verbatim
    assert z.read("ppt/media/image1.svg") == SVG_TEXT.encode("utf-8")
    # Slide XML should reference the asvg extension
    slide_xml = z.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "svgBlip" in slide_xml
    assert "{96DAC541-7B7A-43D3-8B79-37D633B846F1}" in slide_xml
    # Content_Types should declare svg+xml
    ct_xml = z.read("[Content_Types].xml").decode("utf-8")
    assert "image/svg+xml" in ct_xml


@pytest.mark.asyncio
async def test_image_for_svg_session_returns_422() -> None:
    sid = await _make_svg_session()
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/image")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_svg_for_raster_session_returns_422(jpeg_bytes: bytes) -> None:
    sid = await _make_raster_session(jpeg_bytes)
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/svg")
    assert r.status_code == 422
    assert "raster" in r.json()["detail"].lower()


# ── error cases ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_session_returns_404() -> None:
    async with _make_client() as client:
        for ext in ("svg", "pptx", "image"):
            r = await client.get(f"/export/does-not-exist/{ext}")
            assert r.status_code == 404, ext


@pytest.mark.asyncio
async def test_session_with_no_artifact_returns_422() -> None:
    sid = await _make_empty_session()
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/svg")
    assert r.status_code == 422
    assert "no artifact" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_pptx_unrecognized_image_returns_422() -> None:
    """If the session somehow holds non-image bytes, /pptx surfaces 422."""
    sid = await _make_raster_session(b"not actually image bytes")
    async with _make_client() as client:
        r = await client.get(f"/export/{sid}/pptx")
    assert r.status_code == 422
