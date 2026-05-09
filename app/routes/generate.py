"""POST /generate — main entry for figure generation.

Dispatches to Path A (SVG) or Path C (PNG) via the orchestrator.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request
from google.genai import errors as genai_errors

from app.agent.orchestrator import Orchestrator
from app.agent.schemas import GenerateRequest, GenerateResult
from app.clients.gemini import GeminiResponseError
from app.tools.svg_validate import SVGValidationError

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/generate", response_model=GenerateResult)
async def generate(req: GenerateRequest, request: Request) -> GenerateResult:
    sessions = request.app.state.session_store
    orchestrator = Orchestrator(sessions=sessions)
    try:
        result = await orchestrator.generate(req)
    except SVGValidationError as exc:
        logger.warning("generate.svg_invalid", error=str(exc))
        raise HTTPException(
            status_code=422,
            detail=f"Generated artifact failed SVG validation: {exc}",
        )
    except GeminiResponseError as exc:
        logger.warning("generate.gemini_response_error", error=str(exc))
        raise HTTPException(
            status_code=503,
            detail=f"Gemini returned a malformed response: {exc}",
        )
    except genai_errors.APIError as exc:
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", None) or str(exc)
        logger.warning("generate.upstream_error", code=code, message=message)
        raise HTTPException(
            status_code=503,
            detail=f"Upstream Gemini error ({code}): {message}",
        ) from exc
    logger.info(
        "generate.ok",
        session_id=result.session_id,
        kind=result.kind,
        figure_kind=req.figure_kind,
    )
    return result
