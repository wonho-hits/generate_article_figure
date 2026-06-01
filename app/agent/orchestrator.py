"""Orchestrator: dispatch between Path A (vector SVG) and Path C (raster PNG).

Routing decision comes from either explicit override (figure_kind=vector|raster)
or the LLM router (figure_kind=auto, the default).
"""

from __future__ import annotations

import base64

import structlog

from app.agent.router import Router
from app.agent.schemas import (
    EditRequest,
    EditResult,
    FigureKind,
    GenerateRequest,
    GenerateResult,
    RoutingDecision,
)
from app.clients.gemini import GeminiClient
from app.state.session import SessionStore
from app.tools.inpaint import inpaint_region
from app.tools.molecule import render_molecule
from app.tools.raster_illustration import (
    detect_image_mime,
    generate_raster_illustration,
)
from app.tools.mixed_schematic import generate_mixed_figure
from app.tools.vector_schematic import ProgressCallback, generate_vector_schematic

logger = structlog.get_logger(__name__)


class SessionNotFoundError(LookupError):
    """Raised when an operation references a session_id that doesn't exist."""


class UnsupportedSessionKindError(ValueError):
    """Raised when an operation cannot run against the current session's artifact kind."""


class Orchestrator:
    def __init__(
        self,
        *,
        sessions: SessionStore,
        router: Router | None = None,
        client: GeminiClient | None = None,
    ) -> None:
        self._sessions = sessions
        self._router = router or Router(client=client)
        self._client = client

    async def generate(
        self,
        request: GenerateRequest,
        *,
        progress: ProgressCallback | None = None,
    ) -> GenerateResult:
        decision = await self._resolve_path(request.prompt, request.figure_kind)
        logger.info(
            "orchestrator.dispatch",
            path=decision.path,
            figure_kind=request.figure_kind,
        )

        if decision.path == "A":
            return await self._dispatch_vector(request, decision, progress=progress)
        if decision.path == "B":
            return await self._dispatch_chemistry(request, decision)
        if decision.path == "D":
            return await self._dispatch_mixed(request, decision, progress=progress)
        return await self._dispatch_raster(request, decision)

    async def _dispatch_vector(
        self,
        request: GenerateRequest,
        decision: RoutingDecision,
        *,
        progress: ProgressCallback | None = None,
    ) -> GenerateResult:
        svg = await generate_vector_schematic(
            request.prompt, client=self._client, progress=progress
        )
        entry = await self._sessions.create()
        await self._sessions.update(entry.session_id, svg)
        return GenerateResult(
            session_id=entry.session_id,
            artifact=svg,
            kind="svg",
            routing_reason=decision.reason,
        )

    async def _dispatch_mixed(
        self,
        request: GenerateRequest,
        decision: RoutingDecision,
        *,
        progress: ProgressCallback | None = None,
    ) -> GenerateResult:
        """Path D: vector backbone + generated raster icons. Output is an SVG
        string (with embedded data-URI <image> regions), so kind='svg'."""
        svg = await generate_mixed_figure(
            request.prompt, client=self._client, progress=progress
        )
        entry = await self._sessions.create()
        await self._sessions.update(entry.session_id, svg)
        return GenerateResult(
            session_id=entry.session_id,
            artifact=svg,
            kind="svg",
            routing_reason=decision.reason,
        )

    async def _dispatch_chemistry(
        self, request: GenerateRequest, decision: RoutingDecision
    ) -> GenerateResult:
        svg = await render_molecule(request.prompt, client=self._client)
        entry = await self._sessions.create()
        await self._sessions.update(entry.session_id, svg)
        return GenerateResult(
            session_id=entry.session_id,
            artifact=svg,
            kind="svg",
            routing_reason=decision.reason,
        )

    async def _dispatch_raster(
        self, request: GenerateRequest, decision: RoutingDecision
    ) -> GenerateResult:
        image_bytes = await generate_raster_illustration(
            request.prompt, client=self._client
        )
        entry = await self._sessions.create()
        await self._sessions.update(entry.session_id, image_bytes)
        mime = detect_image_mime(image_bytes)
        data_uri = (
            f"data:{mime};base64,"
            + base64.b64encode(image_bytes).decode("ascii")
        )
        return GenerateResult(
            session_id=entry.session_id,
            artifact=data_uri,
            kind="raster",
            routing_reason=decision.reason,
        )

    async def edit(self, session_id: str, request: EditRequest) -> EditResult:
        entry = await self._sessions.get(session_id)
        if entry is None:
            raise SessionNotFoundError(session_id)
        if not isinstance(entry.artifact, bytes):
            raise UnsupportedSessionKindError(
                "edit operates on raster sessions only; "
                "SVG editing is not yet supported in this version"
            )

        image_bytes: bytes = entry.artifact
        image_mime = detect_image_mime(image_bytes)
        mask_bytes = (
            base64.b64decode(request.mask, validate=True)
            if request.mask is not None
            else None
        )

        new_bytes = await inpaint_region(
            image=image_bytes,
            instruction=request.instruction,
            image_mime=image_mime,
            mask=mask_bytes,
            client=self._client,
        )

        updated = await self._sessions.update(session_id, new_bytes)
        # update() returned None would mean session disappeared between get and
        # update — treat as race; not expected with single-process in-memory store.
        assert updated is not None  # noqa: S101
        revision = len(updated.history)

        new_mime = detect_image_mime(new_bytes)
        data_uri = (
            f"data:{new_mime};base64,"
            + base64.b64encode(new_bytes).decode("ascii")
        )
        logger.info(
            "orchestrator.edit",
            session_id=session_id,
            revision=revision,
            has_mask=mask_bytes is not None,
        )
        return EditResult(
            session_id=session_id,
            artifact=data_uri,
            kind="raster",
            revision=revision,
        )

    async def _resolve_path(
        self, prompt: str, figure_kind: FigureKind
    ) -> RoutingDecision:
        if figure_kind == "raster":
            return RoutingDecision(
                path="C", reason="explicit override (figure_kind=raster)"
            )
        if figure_kind == "mixed":
            return RoutingDecision(
                path="D", reason="explicit override (figure_kind=mixed)"
            )
        # auto and vector both run the router
        decision = await self._router.decide(prompt)
        # vector mode forbids any path with raster content (C raster, D mixed);
        # degrade to pure-vector A. Keep the wrapped reason concise for
        # display/logging by truncating the embedded router reason to ~200 chars.
        if figure_kind == "vector" and decision.path in ("C", "D"):
            wrapper = f"vector forced; router→{decision.path} ("
            suffix = ") → fallback A"
            budget = 200 - len(wrapper) - len(suffix)
            embedded = decision.reason[:budget]
            return RoutingDecision(
                path="A",
                reason=f"{wrapper}{embedded}{suffix}",
            )
        return decision
