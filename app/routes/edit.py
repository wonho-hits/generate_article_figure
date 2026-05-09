"""POST /edit/{session_id} — edit an existing raster artifact.

Supports two modalities:
- Conversational reprompt: instruction only.
- Mask-based: instruction + base64-encoded PNG mask (white = edit, black = preserve).
"""

from __future__ import annotations

import binascii

import structlog
from fastapi import APIRouter, HTTPException, Path, Request
from google.genai import errors as genai_errors

from app.agent.orchestrator import (
    Orchestrator,
    SessionNotFoundError,
    UnsupportedSessionKindError,
)
from app.agent.schemas import EditRequest, EditResult
from app.clients.gemini import GeminiResponseError

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/edit/{session_id}", response_model=EditResult)
async def edit(
    req: EditRequest,
    request: Request,
    session_id: str = Path(..., min_length=1),
) -> EditResult:
    sessions = request.app.state.session_store
    orchestrator = Orchestrator(sessions=sessions)
    try:
        result = await orchestrator.edit(session_id, req)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    except UnsupportedSessionKindError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (binascii.Error, ValueError) as exc:
        # Bad base64 in mask, or empty instruction sneaking past validation
        raise HTTPException(status_code=422, detail=f"bad request body: {exc}")
    except GeminiResponseError as exc:
        logger.warning("edit.gemini_response_error", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail=f"Gemini returned a malformed response: {exc}",
        )
    except genai_errors.APIError as exc:
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None) or str(exc)
        logger.warning("edit.upstream_error", code=code, message=message)
        raise HTTPException(
            status_code=503,
            detail=f"Upstream Gemini error ({code}): {message}",
        ) from exc
    logger.info(
        "edit.ok",
        session_id=result.session_id,
        revision=result.revision,
    )
    return result
