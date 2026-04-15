import asyncio
import logging
import httpx
import anthropic
import openai
from collections.abc import AsyncIterator

from app.config import settings

logger = logging.getLogger(__name__)

# Corporate proxy environments often insert self-signed certs into the TLS chain.
# Disable SSL verification globally for the LLM clients so the SDK can reach the API.
# Streaming LLM responses can take several minutes with long idle gaps between chunks.
# Use no read/write timeout, but keep a reasonable connect timeout.
_HTTP_CLIENT = httpx.AsyncClient(
    verify=False,
    timeout=httpx.Timeout(timeout=None, connect=30.0),
)

# Errors that indicate a transient connection drop from the peer / proxy.
# These are safe to retry because no side-effects have been committed yet.
_RETRYABLE_ERRORS = (
    httpx.RemoteProtocolError,   # "peer closed connection" / incomplete chunked read
    httpx.ReadError,             # connection reset mid-stream
    httpx.ConnectError,          # connection refused / DNS failure
    httpx.TimeoutException,      # connect timeout (shouldn't happen, but be safe)
)
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds


async def _with_retry(coro_factory, label: str):
    """Call coro_factory() up to _MAX_RETRIES times on transient connection errors."""
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except _RETRYABLE_ERRORS as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                wait = _RETRY_DELAY * attempt
                logger.warning(
                    "[LLM] %s — transient error on attempt %d/%d: %s. Retrying in %.0fs…",
                    label, attempt, _MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "[LLM] %s — failed after %d attempts: %s", label, _MAX_RETRIES, exc
                )
    raise last_exc


class LLMClient:
    def __init__(self):
        if settings.LLM_PROVIDER == "anthropic":
            self.anthropic = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                http_client=_HTTP_CLIENT,
            )
        elif settings.LLM_PROVIDER == "azure_openai":
            self.openai = openai.AsyncAzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                api_key=settings.AZURE_OPENAI_API_KEY,
                http_client=_HTTP_CLIENT,
            )
            self._model = settings.AZURE_OPENAI_MODEL_NAME
        else:
            self.openai = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                http_client=_HTTP_CLIENT,
            )
            self._model = settings.LLM_MODEL

    async def complete(self, system: str, user: str, stream: bool = False, max_tokens: int = 8192) -> str | AsyncIterator[str]:
        if settings.LLM_PROVIDER == "anthropic":
            return await self._anthropic_complete(system, user, stream, max_tokens)
        else:
            return await self._openai_complete(system, user, stream, max_tokens)

    async def _anthropic_complete(self, system: str, user: str, stream: bool, max_tokens: int = 8192) -> str | AsyncIterator[str]:
        if stream:
            return self._anthropic_stream(system, user, max_tokens)
        response = await _with_retry(
            lambda: self.anthropic.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            ),
            "anthropic.messages.create",
        )
        return response.content[0].text

    async def _anthropic_stream(self, system: str, user: str, max_tokens: int = 8192) -> AsyncIterator[str]:
        async with self.anthropic.messages.stream(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _openai_complete(self, system: str, user: str, stream: bool, max_tokens: int = 8192) -> str | AsyncIterator[str]:
        if stream:
            return self._openai_stream(system, user, max_tokens)
        response = await _with_retry(
            lambda: self.openai.chat.completions.create(
                model=self._model,
                max_completion_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            ),
            "openai.chat.completions.create",
        )
        return response.choices[0].message.content

    async def _openai_stream(self, system: str, user: str, max_tokens: int = 8192) -> AsyncIterator[str]:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                stream = await self.openai.chat.completions.create(
                    model=self._model,
                    max_completion_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    stream=True,
                )
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except _RETRYABLE_ERRORS as exc:
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_DELAY * attempt
                    logger.warning(
                        "[LLM] openai stream — transient error attempt %d/%d: %s. Retrying in %.0fs…",
                        attempt, _MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("[LLM] openai stream — failed after %d attempts: %s", _MAX_RETRIES, exc)
                    raise


llm_client = LLMClient()


class CodexLLMClient:
    """LLM client using gpt-5.3-codex via the OpenAI Responses API."""

    def __init__(self):
        if settings.CODEX_AZURE_OPENAI_API_KEY and settings.CODEX_AZURE_OPENAI_ENDPOINT:
            self._client = openai.AsyncAzureOpenAI(
                azure_endpoint=settings.CODEX_AZURE_OPENAI_ENDPOINT,
                api_version=settings.CODEX_AZURE_OPENAI_API_VERSION,
                api_key=settings.CODEX_AZURE_OPENAI_API_KEY,
                http_client=_HTTP_CLIENT,
            )
            self._model = settings.CODEX_AZURE_OPENAI_MODEL_NAME
            self._available = True
        else:
            self._available = False

    async def complete(self, system: str, user: str, stream: bool = False, max_tokens: int = 8192) -> str | AsyncIterator[str]:
        if not self._available:
            return await llm_client.complete(system, user, stream, max_tokens)
        if stream:
            return self._stream(system, user, max_tokens)
        response = await _with_retry(
            lambda: self._client.responses.create(
                model=self._model,
                instructions=system,
                input=user,
                max_output_tokens=max_tokens,
            ),
            "codex.responses.create",
        )
        return response.output_text

    async def _stream(self, system: str, user: str, max_tokens: int = 8192) -> AsyncIterator[str]:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                stream = self._client.responses.stream(
                    model=self._model,
                    instructions=system,
                    input=user,
                    max_output_tokens=max_tokens,
                )
                async with stream as s:
                    async for event in s:
                        if hasattr(event, 'type') and event.type == 'response.output_text.delta':
                            yield event.delta
                return
            except _RETRYABLE_ERRORS as exc:
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_DELAY * attempt
                    logger.warning(
                        "[LLM] codex stream — transient error attempt %d/%d: %s. Retrying in %.0fs…",
                        attempt, _MAX_RETRIES, exc, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("[LLM] codex stream — failed after %d attempts: %s", _MAX_RETRIES, exc)
                    raise


codex_client = CodexLLMClient()
