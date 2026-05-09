"""Async wrapper around the google-genai SDK.

Centralizes:
- API key + model selection (from app.config)
- Retry on transient errors with exponential backoff
- Structured-output parsing via Pydantic schemas
- Cost / token-usage logging via structlog

Used by every downstream tool. Built once, used everywhere.
"""

from __future__ import annotations

import asyncio
from typing import Type, TypeVar

import structlog
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from app.config import get_settings

T = TypeVar("T", bound=BaseModel)

logger = structlog.get_logger(__name__)

_RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}


class GeminiResponseError(RuntimeError):
    """Raised when the Gemini response is missing the expected payload."""


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        text_model: str | None = None,
        image_model: str | None = None,
        max_retries: int | None = None,
    ) -> None:
        s = get_settings()
        self._text_model = text_model or s.gemini_text_model
        self._image_model = image_model or s.gemini_image_model
        self._max_retries = max_retries if max_retries is not None else s.gemini_max_retries
        self._client = genai.Client(api_key=api_key or s.google_api_key)

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        response_schema: Type[T] | None = None,
        model: str | None = None,
    ) -> str | T:
        """Generate text. If response_schema is given, return parsed Pydantic model."""
        config_kwargs: dict = {}
        if system is not None:
            config_kwargs["system_instruction"] = system
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema
        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        response = await self._call_with_retry(
            model=model or self._text_model,
            contents=prompt,
            config=config,
        )
        self._log_usage(response, kind="text")

        if response_schema is not None:
            parsed = getattr(response, "parsed", None)
            if parsed is not None:
                return parsed  # type: ignore[return-value]
            # SDK did not auto-parse; fall back to manual validation against
            # response.text. Observed on google-genai 1.x with some models.
            text = response.text or ""
            if not text:
                raise GeminiResponseError(
                    "response_schema requested but Gemini returned neither "
                    "parsed object nor text"
                )
            try:
                return response_schema.model_validate_json(text)
            except Exception as exc:
                raise GeminiResponseError(
                    f"failed to parse Gemini JSON into "
                    f"{response_schema.__name__}: {exc}"
                ) from exc
        return response.text or ""

    async def generate_image(self, prompt: str, *, model: str | None = None) -> bytes:
        """Generate image, return raw image bytes. Format chosen by the model
        (typically JPEG on gemini-3.1-flash-image-preview)."""
        response = await self._call_with_retry(
            model=model or self._image_model,
            contents=prompt,
            config=None,
        )
        self._log_usage(response, kind="image")
        return self._extract_image_bytes(response)

    async def edit_image(
        self,
        image: bytes,
        instruction: str,
        *,
        image_mime: str,
        mask: bytes | None = None,
        mask_mime: str = "image/png",
        model: str | None = None,
    ) -> bytes:
        """Edit an existing image via Nano Banana 2 multi-input.

        - mask=None → conversational reprompt (text instruction only).
        - mask=bytes → mask-based edit. Industry convention: pixels that are
          WHITE in the mask = edit region; BLACK = preserve. Caller is
          responsible for honoring the convention; the model treats both
          images as input context.
        """
        parts: list = [types.Part.from_bytes(data=image, mime_type=image_mime)]
        if mask is not None:
            parts.append(types.Part.from_bytes(data=mask, mime_type=mask_mime))
        parts.append(instruction)

        response = await self._call_with_retry(
            model=model or self._image_model,
            contents=parts,
            config=None,
        )
        self._log_usage(response, kind="image_edit")
        return self._extract_image_bytes(response)

    @staticmethod
    def _extract_image_bytes(response) -> bytes:
        for candidate in response.candidates or []:
            content = getattr(candidate, "content", None)
            if content is None:
                continue
            for part in content.parts or []:
                inline = getattr(part, "inline_data", None)
                if inline is not None and inline.data:
                    return inline.data
        raise GeminiResponseError("Gemini response contained no image part")

    async def _call_with_retry(self, *, model: str, contents: str, config):
        attempt = 0
        while True:
            try:
                return await self._client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            except genai_errors.APIError as exc:
                code = getattr(exc, "code", None)
                if code in _RETRYABLE_CODES and attempt < self._max_retries:
                    backoff = 2**attempt
                    logger.warning(
                        "gemini.retry",
                        attempt=attempt + 1,
                        backoff_seconds=backoff,
                        error_code=code,
                    )
                    await asyncio.sleep(backoff)
                    attempt += 1
                    continue
                raise

    def _log_usage(self, response, *, kind: str) -> None:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return
        logger.info(
            "gemini.usage",
            kind=kind,
            prompt_tokens=getattr(usage, "prompt_token_count", None),
            response_tokens=getattr(usage, "candidates_token_count", None),
            total_tokens=getattr(usage, "total_token_count", None),
        )
