"""Mocked tests for the LLM router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.router import Router
from app.agent.schemas import RoutingDecision
from app.clients.gemini import GeminiClient


@pytest.mark.asyncio
async def test_decide_returns_routing_decision() -> None:
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(
        return_value=RoutingDecision(path="A", reason="abstract block diagram")
    )
    router = Router(client=client)

    result = await router.decide("MAPK pathway")

    assert isinstance(result, RoutingDecision)
    assert result.path == "A"
    assert result.reason == "abstract block diagram"
    client.generate_text.assert_awaited_once()
    # response_schema must be RoutingDecision
    _, kwargs = client.generate_text.call_args
    assert kwargs.get("response_schema") is RoutingDecision


@pytest.mark.asyncio
async def test_decide_for_path_c() -> None:
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(
        return_value=RoutingDecision(
            path="C", reason="multi-cell illustrative figure"
        )
    )
    router = Router(client=client)

    result = await router.decide("tumor microenvironment with macrophages")

    assert result.path == "C"


@pytest.mark.asyncio
async def test_decide_raises_when_sdk_returns_wrong_type() -> None:
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value="oops, raw string")
    router = Router(client=client)

    with pytest.raises(RuntimeError, match="RoutingDecision"):
        await router.decide("anything")
