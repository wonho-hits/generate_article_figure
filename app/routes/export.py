"""GET /export/{session_id}/{format} — package session artifacts as files.

Format compatibility:
- /svg     → SVG sessions only (Path A)
- /pptx    → raster sessions only (Path C)
- /image   → raster sessions only (Path C); MIME pass-through
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Path, Request
from fastapi.responses import Response

from app.tools import export

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/export/{session_id}/svg")
async def export_svg_route(
    request: Request,
    session_id: str = Path(..., min_length=1),
) -> Response:
    entry = await _load_artifact(request, session_id)
    if not isinstance(entry.artifact, str):
        raise HTTPException(
            status_code=422,
            detail=(
                "session is raster; SVG export is not available. "
                f"Use /export/{session_id}/pptx or /export/{session_id}/image."
            ),
        )
    result = export.export_svg(entry.artifact, session_id=session_id)
    return _file_response(result)


@router.get("/export/{session_id}/pptx")
async def export_pptx_route(
    request: Request,
    session_id: str = Path(..., min_length=1),
) -> Response:
    """PPTX export is available for both kinds.

    - SVG session → PPTX with the SVG embedded as a vector image.
      Modern PowerPoint renders it as vector; right-click → "Convert to
      Shape" breaks it into editable native shapes.
    - Raster session → PPTX with the raster embedded as a single picture
      on a blank slide.
    """
    entry = await _load_artifact(request, session_id)
    try:
        if isinstance(entry.artifact, str):
            result = export.export_pptx_from_svg(
                entry.artifact, session_id=session_id
            )
        elif isinstance(entry.artifact, bytes):
            result = export.export_pptx(entry.artifact, session_id=session_id)
        else:
            raise HTTPException(
                status_code=422,
                detail="session artifact has an unsupported type",
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _file_response(result)


@router.get("/export/{session_id}/image")
async def export_image_route(
    request: Request,
    session_id: str = Path(..., min_length=1),
) -> Response:
    entry = await _load_artifact(request, session_id)
    if not isinstance(entry.artifact, bytes):
        raise HTTPException(
            status_code=422,
            detail=(
                "session is svg; image export is not available. "
                f"Use /export/{session_id}/svg."
            ),
        )
    try:
        result = export.export_image(entry.artifact, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _file_response(result)


async def _load_artifact(request: Request, session_id: str):
    sessions = request.app.state.session_store
    entry = await sessions.get(session_id)
    if entry is None:
        raise HTTPException(
            status_code=404, detail=f"session {session_id} not found"
        )
    if entry.artifact is None:
        raise HTTPException(
            status_code=422,
            detail=f"session {session_id} has no artifact yet — call /generate first",
        )
    return entry


def _file_response(result: export.ExportResult) -> Response:
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
        },
    )
