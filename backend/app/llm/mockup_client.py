"""원본 pfy-front scaffolding/src/utils/llmClient.ts의 Python 포팅.

사내 AOAI 게이트웨이(X-Api-Key 헤더, OpenAI chat 포맷)를 호출한다.
기존 AzureOpenAI SDK와 다른 인증/엔드포인트 구조라 전용 클라이언트로 분리.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings


class MockupLLMClient:
    def __init__(self) -> None:
        self._endpoint = settings.MOCKUP_AOAI_ENDPOINT
        self._api_key = settings.MOCKUP_AOAI_API_KEY
        self._model = settings.MOCKUP_AOAI_DEPLOYMENT

    async def complete(
        self,
        system: str,
        user: str,
        stream: bool = False,
        max_tokens: int | None = None,
        temperature: float = 0.35,
    ) -> str | AsyncIterator[str]:
        if not self._endpoint or not self._api_key:
            raise RuntimeError(
                "MOCKUP_AOAI_ENDPOINT / MOCKUP_AOAI_API_KEY 가 .env에 설정되지 않았습니다."
            )

        max_tok = max_tokens if max_tokens is not None else settings.MOCKUP_AOAI_MAX_TOKENS
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tok,
            "stream": stream,
        }
        headers = {"Content-Type": "application/json", "X-Api-Key": self._api_key}

        if not stream:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0), verify=False
            ) as c:
                r = await c.post(self._endpoint, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]

        async def _stream() -> AsyncIterator[str]:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(None, connect=30.0), verify=False
            ) as c:
                async with c.stream("POST", self._endpoint, json=body, headers=headers) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            obj = json.loads(payload)
                            delta = obj.get("choices", [{}])[0].get("delta", {}).get("content")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        return _stream()


mockup_client = MockupLLMClient()
