import anthropic
import openai
from collections.abc import AsyncIterator

from app.config import settings


class LLMClient:
    def __init__(self):
        if settings.LLM_PROVIDER == "anthropic":
            self.anthropic = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            self.openai = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def complete(self, system: str, user: str, stream: bool = False) -> str | AsyncIterator[str]:
        if settings.LLM_PROVIDER == "anthropic":
            return await self._anthropic_complete(system, user, stream)
        else:
            return await self._openai_complete(system, user, stream)

    async def _anthropic_complete(self, system: str, user: str, stream: bool) -> str | AsyncIterator[str]:
        if stream:
            return self._anthropic_stream(system, user)
        response = await self.anthropic.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    async def _anthropic_stream(self, system: str, user: str) -> AsyncIterator[str]:
        async with self.anthropic.messages.stream(
            model=settings.LLM_MODEL,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _openai_complete(self, system: str, user: str, stream: bool) -> str | AsyncIterator[str]:
        if stream:
            return self._openai_stream(system, user)
        response = await self.openai.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content

    async def _openai_stream(self, system: str, user: str) -> AsyncIterator[str]:
        stream = await self.openai.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


llm_client = LLMClient()
