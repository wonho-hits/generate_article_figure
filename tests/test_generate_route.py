"""End-to-end tests for POST /generate (mocked Gemini, both paths)."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agent.schemas import RoutingDecision
from app.main import app


GOOD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
    '<g id="ras" data-role="protein"><rect/></g></svg>'
)
# Real PNG magic bytes so detect_image_mime() returns image/png.
FAKE_PNG = b"\x89PNG\r\n\x1a\n" + b"FAKE-PIXEL-BODY"
FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"FAKE-JPEG-BODY"


def _make_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# --- Path A via auto-routing ---


@pytest.mark.asyncio
async def test_auto_routes_to_path_a_returns_svg() -> None:
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_vector_schematic") as mock_a,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="A", reason="abstract pathway")
        )
        mock_a.return_value = GOOD_SVG

        async with _make_client() as client:
            response = await client.post(
                "/generate", json={"prompt": "MAPK pathway"}
            )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "svg"
    assert "<svg" in body["artifact"]
    assert body["routing_reason"] == "abstract pathway"


@pytest.mark.asyncio
async def test_auto_routes_to_path_c_returns_data_uri() -> None:
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_raster_illustration") as mock_c,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="C", reason="multi-cell illustration")
        )
        mock_c.return_value = FAKE_PNG

        async with _make_client() as client:
            response = await client.post(
                "/generate",
                json={"prompt": "tumor microenvironment with macrophages"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "raster"
    expected_uri = "data:image/png;base64," + base64.b64encode(FAKE_PNG).decode("ascii")
    assert body["artifact"] == expected_uri
    assert body["routing_reason"] == "multi-cell illustration"


@pytest.mark.asyncio
async def test_auto_routes_to_path_b_returns_svg() -> None:
    """Chemistry prompt → router picks B → render_molecule produces SVG."""
    CHEM_SVG = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">'
        '<g id="molecule" data-role="chemistry"><path d="M0 0"/></g></svg>'
    )
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.render_molecule") as mock_b,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="B", reason="single molecule")
        )
        mock_b.return_value = CHEM_SVG

        async with _make_client() as client:
            response = await client.post(
                "/generate", json={"prompt": "draw aspirin"}
            )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "svg"
    assert 'id="molecule"' in body["artifact"]
    assert body["routing_reason"] == "single molecule"


@pytest.mark.asyncio
async def test_vector_override_falls_back_when_router_picks_c() -> None:
    """figure_kind=vector + router says C → degrade to A."""
    GOOD_SVG_FB = '<svg xmlns="http://www.w3.org/2000/svg"><g id="x"/></svg>'
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_vector_schematic") as mock_a,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="C", reason="illustrative")
        )
        mock_a.return_value = GOOD_SVG_FB

        async with _make_client() as client:
            response = await client.post(
                "/generate",
                json={"prompt": "stylized cells", "figure_kind": "vector"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "svg"
    assert "vector forced" in body["routing_reason"]


@pytest.mark.asyncio
async def test_vector_override_fallback_reason_fits_200_char_limit() -> None:
    """Regression: router can return a 200-char reason; the vector→A fallback
    interpolates it into a wrapper, which previously overflowed the
    RoutingDecision.reason max_length=200 and raised ValidationError."""
    GOOD_SVG_FB = '<svg xmlns="http://www.w3.org/2000/svg"><g id="x"/></svg>'
    long_router_reason = "x" * 200  # the maximum router can produce
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_vector_schematic") as mock_a,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="C", reason=long_router_reason)
        )
        mock_a.return_value = GOOD_SVG_FB

        async with _make_client() as client:
            response = await client.post(
                "/generate",
                json={"prompt": "x", "figure_kind": "vector"},
            )

    assert response.status_code == 200
    body = response.json()
    assert len(body["routing_reason"]) <= 200
    assert "vector forced" in body["routing_reason"]


@pytest.mark.asyncio
async def test_path_c_jpeg_response_uses_image_jpeg_mime() -> None:
    """Gemini Image returns JPEG in practice — data URI must reflect that."""
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_raster_illustration") as mock_c,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="C", reason="x")
        )
        mock_c.return_value = FAKE_JPEG

        async with _make_client() as client:
            response = await client.post("/generate", json={"prompt": "x"})

    assert response.status_code == 200
    body = response.json()
    assert body["artifact"].startswith("data:image/jpeg;base64,")


# --- Explicit overrides ---


@pytest.mark.asyncio
async def test_figure_kind_vector_runs_router_picks_path_a() -> None:
    """vector mode runs the router (so chemistry can route to B); only C is
    forbidden under vector and falls back to A."""
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_vector_schematic") as mock_a,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="A", reason="abstract pathway")
        )
        mock_a.return_value = GOOD_SVG

        async with _make_client() as client:
            response = await client.post(
                "/generate",
                json={"prompt": "MAPK pathway", "figure_kind": "vector"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "svg"
    MockRouter.return_value.decide.assert_awaited_once()


@pytest.mark.asyncio
async def test_figure_kind_raster_forces_path_c() -> None:
    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_raster_illustration") as mock_c,
    ):
        MockRouter.return_value.decide = AsyncMock(
            side_effect=AssertionError("router must not run on override")
        )
        mock_c.return_value = FAKE_PNG

        async with _make_client() as client:
            response = await client.post(
                "/generate",
                json={"prompt": "anything", "figure_kind": "raster"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "raster"
    assert body["artifact"].startswith("data:image/")


# --- Validation / errors ---


@pytest.mark.asyncio
async def test_empty_prompt_returns_422() -> None:
    async with _make_client() as client:
        response = await client.post("/generate", json={"prompt": ""})
    assert response.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_invalid_figure_kind_returns_422() -> None:
    async with _make_client() as client:
        response = await client.post(
            "/generate", json={"prompt": "x", "figure_kind": "magic"}
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_persistent_svg_validation_failure_returns_422() -> None:
    from app.tools.svg_validate import SVGValidationError

    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_vector_schematic") as mock_a,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="A", reason="x")
        )
        mock_a.side_effect = SVGValidationError("malformed XML")

        async with _make_client() as client:
            response = await client.post("/generate", json={"prompt": "x"})

    assert response.status_code == 422
    assert "validation" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upstream_apierror_returns_503() -> None:
    from google.genai import errors as genai_errors

    err = genai_errors.APIError.__new__(genai_errors.APIError)
    err.code = 503
    err.message = "service unavailable"

    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_vector_schematic") as mock_a,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="A", reason="x")
        )
        mock_a.side_effect = err

        async with _make_client() as client:
            response = await client.post("/generate", json={"prompt": "x"})

    assert response.status_code == 503
    assert "Upstream Gemini error" in response.json()["detail"]


@pytest.mark.asyncio
async def test_gemini_response_error_returns_503() -> None:
    from app.clients.gemini import GeminiResponseError

    with (
        patch("app.agent.orchestrator.Router") as MockRouter,
        patch("app.agent.orchestrator.generate_raster_illustration") as mock_c,
    ):
        MockRouter.return_value.decide = AsyncMock(
            return_value=RoutingDecision(path="C", reason="x")
        )
        mock_c.side_effect = GeminiResponseError("no image part")

        async with _make_client() as client:
            response = await client.post("/generate", json={"prompt": "x"})

    assert response.status_code == 503
    assert "malformed response" in response.json()["detail"]
