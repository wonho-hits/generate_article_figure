"""Unit tests for the Gemini client wrapper.

The google-genai SDK is mocked at the genai.Client level so no real API calls
are made. The wrapper's job is: dispatch, parse, retry, log usage. We test
those behaviors, not the SDK itself.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.clients.gemini import GeminiClient, GeminiResponseError


def _fake_text_response(text: str = "hello", *, parsed=None):
    response = MagicMock()
    response.text = text
    response.parsed = parsed
    response.usage_metadata = MagicMock(
        prompt_token_count=10,
        candidates_token_count=5,
        total_token_count=15,
    )
    return response


def _fake_image_response(data: bytes = b"PNGBYTES"):
    response = MagicMock()
    response.text = None
    part = MagicMock()
    part.inline_data = MagicMock(data=data)
    candidate = MagicMock()
    candidate.content = MagicMock(parts=[part])
    response.candidates = [candidate]
    response.usage_metadata = None
    return response


def _fake_image_response_no_inline():
    response = MagicMock()
    part = MagicMock()
    part.inline_data = None
    candidate = MagicMock()
    candidate.content = MagicMock(parts=[part])
    response.candidates = [candidate]
    response.usage_metadata = None
    return response


@pytest.mark.asyncio
async def test_generate_text_returns_string() -> None:
    fake = _fake_text_response("hi there")
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        client = GeminiClient()
        result = await client.generate_text("hello?")

        assert result == "hi there"
        instance.aio.models.generate_content.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_text_with_schema_returns_parsed() -> None:
    class Decision(BaseModel):
        path: str
        reasoning: str

    parsed_obj = Decision(path="A", reasoning="diagrammatic")
    fake = _fake_text_response(text="{...}", parsed=parsed_obj)
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        client = GeminiClient()
        result = await client.generate_text("classify this", response_schema=Decision)

        assert isinstance(result, Decision)
        assert result.path == "A"


@pytest.mark.asyncio
async def test_generate_text_with_schema_raises_when_no_parsed() -> None:
    fake = _fake_text_response(text="{...}", parsed=None)
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        class Schema(BaseModel):
            x: int

        client = GeminiClient()
        with pytest.raises(GeminiResponseError):
            await client.generate_text("x", response_schema=Schema)


@pytest.mark.asyncio
async def test_generate_image_returns_bytes() -> None:
    fake = _fake_image_response(b"\x89PNG-FAKE")
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        client = GeminiClient()
        result = await client.generate_image("draw a cell")

        assert result == b"\x89PNG-FAKE"


@pytest.mark.asyncio
async def test_generate_image_raises_when_no_inline_data() -> None:
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(
            return_value=_fake_image_response_no_inline()
        )

        client = GeminiClient()
        with pytest.raises(GeminiResponseError):
            await client.generate_image("x")


@pytest.mark.asyncio
async def test_retry_on_503_then_success() -> None:
    from google.genai import errors as genai_errors

    transient = genai_errors.APIError.__new__(genai_errors.APIError)
    transient.code = 503
    transient.message = "service unavailable"

    fake = _fake_text_response("ok")
    with (
        patch("app.clients.gemini.genai.Client") as MockClient,
        patch("app.clients.gemini.asyncio.sleep", new=AsyncMock()),
    ):
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(side_effect=[transient, fake])

        client = GeminiClient(max_retries=2)
        result = await client.generate_text("retry me")

        assert result == "ok"
        assert instance.aio.models.generate_content.await_count == 2


@pytest.mark.asyncio
async def test_edit_image_returns_bytes() -> None:
    fake = _fake_image_response(b"\xff\xd8\xff\xe0EDITED")
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        client = GeminiClient()
        out = await client.edit_image(
            image=b"\x89PNG\r\n\x1a\nSRC",
            instruction="change something",
            image_mime="image/png",
        )

        assert out == b"\xff\xd8\xff\xe0EDITED"
        # Multi-input contents: 2 parts (no mask) — image, then text
        _, kwargs = instance.aio.models.generate_content.call_args
        contents = kwargs["contents"]
        assert len(contents) == 2  # image + instruction


@pytest.mark.asyncio
async def test_edit_image_with_mask_passes_three_parts() -> None:
    fake = _fake_image_response(b"\x89PNG\r\n\x1a\nMASKED-OUT")
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        client = GeminiClient()
        out = await client.edit_image(
            image=b"\x89PNG\r\n\x1a\nSRC",
            instruction="edit masked area",
            image_mime="image/png",
            mask=b"\x89PNG\r\n\x1a\nMASK",
        )

        assert out == b"\x89PNG\r\n\x1a\nMASKED-OUT"
        _, kwargs = instance.aio.models.generate_content.call_args
        contents = kwargs["contents"]
        assert len(contents) == 3  # image + mask + instruction


@pytest.mark.asyncio
async def test_edit_image_raises_when_no_image_part() -> None:
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(
            return_value=_fake_image_response_no_inline()
        )

        client = GeminiClient()
        with pytest.raises(GeminiResponseError):
            await client.edit_image(
                image=b"\x89PNG\r\n\x1a\nSRC",
                instruction="x",
                image_mime="image/png",
            )


@pytest.mark.asyncio
async def test_generate_text_with_schema_falls_back_to_text_parse() -> None:
    """SDK does not auto-populate response.parsed; client must parse JSON."""
    from pydantic import BaseModel

    class Decision(BaseModel):
        path: str

    fake = _fake_text_response(text='{"path": "A"}', parsed=None)
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        client = GeminiClient()
        result = await client.generate_text("classify", response_schema=Decision)

        assert isinstance(result, Decision)
        assert result.path == "A"


@pytest.mark.asyncio
async def test_generate_text_schema_fallback_raises_on_bad_json() -> None:
    from pydantic import BaseModel

    class Decision(BaseModel):
        path: str

    fake = _fake_text_response(text="not json {{{", parsed=None)
    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(return_value=fake)

        client = GeminiClient()
        with pytest.raises(GeminiResponseError, match="failed to parse"):
            await client.generate_text("classify", response_schema=Decision)


@pytest.mark.asyncio
async def test_non_retryable_error_propagates() -> None:
    from google.genai import errors as genai_errors

    permanent = genai_errors.APIError.__new__(genai_errors.APIError)
    permanent.code = 400
    permanent.message = "bad request"

    with patch("app.clients.gemini.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.aio.models.generate_content = AsyncMock(side_effect=permanent)

        client = GeminiClient(max_retries=3)
        with pytest.raises(genai_errors.APIError):
            await client.generate_text("nope")

        assert instance.aio.models.generate_content.await_count == 1
