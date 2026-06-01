"""gpt-5.5 client (Azure Responses API, tool-calling). Renamed from misnamed 'codex'."""

from __future__ import annotations

import asyncio
import logging

import httpx
import openai

from app.config import settings

logger = logging.getLogger(__name__)

_HTTP_CLIENT = httpx.AsyncClient(verify=False, timeout=httpx.Timeout(timeout=None, connect=30.0))
_RETRYABLE = (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.TimeoutException)
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0


async def _with_retry(coro_factory, label: str):
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY * attempt)
            else:
                logger.error("[gpt55] %s failed after %d: %s", label, _MAX_RETRIES, exc)
    raise last_exc


class Gpt55Client:
    """gpt-5.5 via Azure Responses API. (env still named CODEX_* — read as-is for now.)"""

    def __init__(self) -> None:
        self._available = bool(
            settings.CODEX_AZURE_OPENAI_API_KEY and settings.CODEX_AZURE_OPENAI_ENDPOINT
        )
        if self._available:
            self._client = openai.AsyncAzureOpenAI(
                azure_endpoint=settings.CODEX_AZURE_OPENAI_ENDPOINT,
                api_version=settings.CODEX_AZURE_OPENAI_API_VERSION,
                api_key=settings.CODEX_AZURE_OPENAI_API_KEY,
                http_client=_HTTP_CLIENT,
            )
            self._model = settings.CODEX_AZURE_OPENAI_MODEL_NAME

    async def complete(self, system: str, user: str, max_tokens: int = 16384) -> str:
        resp = await _with_retry(
            lambda: self._client.responses.create(
                model=self._model, instructions=system, input=user,
                max_output_tokens=max_tokens),
            "responses.create")
        return resp.output_text

    async def complete_with_tools(self, system: str, user: str, tools: list[dict],
                                  max_tokens: int = 16384):
        """Single Responses API turn with tools. Returns the raw response (output items)."""
        return await _with_retry(
            lambda: self._client.responses.create(
                model=self._model, instructions=system, input=user,
                tools=tools, max_output_tokens=max_tokens),
            "responses.create+tools")


gpt55_client = Gpt55Client()
