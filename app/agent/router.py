"""LLM router: decides Path A (vector) vs Path C (raster) for a given prompt.

Single short text-only Gemini call with structured Pydantic output.
Cost is ~50 input + ~30 output tokens — negligible vs. generation cost.
"""

from __future__ import annotations

import structlog

from app.agent.prompts.router import ROUTER_SYSTEM
from app.agent.schemas import RoutingDecision
from app.clients.gemini import GeminiClient

logger = structlog.get_logger(__name__)


class Router:
    def __init__(self, *, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()

    async def decide(self, prompt: str) -> RoutingDecision:
        decision = await self._client.generate_text(
            prompt,
            system=ROUTER_SYSTEM,
            response_schema=RoutingDecision,
        )
        if not isinstance(decision, RoutingDecision):
            raise RuntimeError(
                f"router expected RoutingDecision, got {type(decision).__name__}"
            )
        logger.info("router.decide", path=decision.path, reason=decision.reason[:80])
        return decision
