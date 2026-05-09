"""End-to-end tests for POST /edit/{session_id} (mocked Gemini)."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


SOURCE_PNG = b"\x89PNG\r\n\x1a\n" + b"FAKE-SOURCE-BODY"
EDITED_JPEG = b"\xff\xd8\xff\xe0" + b"FAKE-EDITED-BODY"
MASK_PNG = b"\x89PNG\r\n\x1a\n" + b"FAKE-MASK-BODY"


def _make_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _make_raster_session() -> str:
    """Create a session pre-populated with a raster artifact."""
    sessions = app.state.session_store
    entry = await sessions.create()
    await sessions.update(entry.session_id, SOURCE_PNG)
    return entry.session_id


async def _make_svg_session() -> str:
    sessions = app.state.session_store
    entry = await sessions.create()
    await sessions.update(entry.session_id, "<svg/>")
    return entry.session_id


# ── happy path ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_conversational_edit_returns_data_uri() -> None:
    session_id = await _make_raster_session()

    with patch("app.agent.orchestrator.inpaint_region") as mock_inpaint:
        mock_inpaint.return_value = EDITED_JPEG

        async with _make_client() as client:
            response = await client.post(
                f"/edit/{session_id}",
                json={"instruction": "remove the duplicate T cell"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["kind"] == "raster"
    # JPEG magic in EDITED_JPEG → MIME should be image/jpeg
    assert body["artifact"].startswith("data:image/jpeg;base64,")
    assert body["revision"] == 1


@pytest.mark.asyncio
async def test_mask_based_edit_decodes_base64_mask() -> None:
    session_id = await _make_raster_session()
    mask_b64 = base64.b64encode(MASK_PNG).decode("ascii")

    with patch("app.agent.orchestrator.inpaint_region") as mock_inpaint:
        mock_inpaint.return_value = EDITED_JPEG

        async with _make_client() as client:
            response = await client.post(
                f"/edit/{session_id}",
                json={"instruction": "replace masked area", "mask": mask_b64},
            )

    assert response.status_code == 200
    # Tool received raw mask bytes (decoded from base64)
    _, kwargs = mock_inpaint.call_args
    assert kwargs["mask"] == MASK_PNG


@pytest.mark.asyncio
async def test_revision_increments_across_edits() -> None:
    session_id = await _make_raster_session()

    with patch("app.agent.orchestrator.inpaint_region") as mock_inpaint:
        mock_inpaint.return_value = EDITED_JPEG

        async with _make_client() as client:
            r1 = await client.post(
                f"/edit/{session_id}", json={"instruction": "edit one"}
            )
            r2 = await client.post(
                f"/edit/{session_id}", json={"instruction": "edit two"}
            )

    assert r1.json()["revision"] == 1
    assert r2.json()["revision"] == 2


# ── error cases ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_session_returns_404() -> None:
    async with _make_client() as client:
        response = await client.post(
            "/edit/does-not-exist", json={"instruction": "x"}
        )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_svg_session_returns_422() -> None:
    session_id = await _make_svg_session()

    async with _make_client() as client:
        response = await client.post(
            f"/edit/{session_id}", json={"instruction": "x"}
        )

    assert response.status_code == 422
    assert "raster" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_empty_instruction_returns_422() -> None:
    session_id = await _make_raster_session()
    async with _make_client() as client:
        response = await client.post(
            f"/edit/{session_id}", json={"instruction": ""}
        )
    assert response.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_invalid_base64_mask_returns_422() -> None:
    session_id = await _make_raster_session()
    async with _make_client() as client:
        response = await client.post(
            f"/edit/{session_id}",
            json={"instruction": "x", "mask": "!!!not-valid-base64!!!"},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upstream_apierror_returns_503() -> None:
    from google.genai import errors as genai_errors

    err = genai_errors.APIError.__new__(genai_errors.APIError)
    err.code = 503
    err.message = "service unavailable"

    session_id = await _make_raster_session()
    with patch("app.agent.orchestrator.inpaint_region") as mock_inpaint:
        mock_inpaint.side_effect = err

        async with _make_client() as client:
            response = await client.post(
                f"/edit/{session_id}", json={"instruction": "x"}
            )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_gemini_response_error_returns_503() -> None:
    from app.clients.gemini import GeminiResponseError

    session_id = await _make_raster_session()
    with patch("app.agent.orchestrator.inpaint_region") as mock_inpaint:
        mock_inpaint.side_effect = GeminiResponseError("no image part")

        async with _make_client() as client:
            response = await client.post(
                f"/edit/{session_id}", json={"instruction": "x"}
            )

    assert response.status_code == 503
