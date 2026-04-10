import httpx
import anthropic
import openai
from collections.abc import AsyncIterator

from app.config import settings

# Corporate proxy environments often insert self-signed certs into the TLS chain.
# Disable SSL verification globally for the LLM clients so the SDK can reach the API.
_HTTP_CLIENT = httpx.AsyncClient(verify=False)


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
        response = await self.anthropic.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
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
        response = await self.openai.chat.completions.create(
            model=self._model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content

    async def _openai_stream(self, system: str, user: str, max_tokens: int = 8192) -> AsyncIterator[str]:
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
        response = await self._client.responses.create(
            model=self._model,
            instructions=system,
            input=user,
            max_output_tokens=max_tokens,
        )
        return response.output_text

    async def _stream(self, system: str, user: str, max_tokens: int = 8192) -> AsyncIterator[str]:
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


codex_client = CodexLLMClient()
