"""원본 pfy-front scaffolding/src/utils/llmClient.ts의 Python 포팅.

사내 AOAI 게이트웨이(X-Api-Key 헤더, OpenAI chat 포맷)를 호출한다.
기존 AzureOpenAI SDK와 다른 인증/엔드포인트 구조라 전용 클라이언트로 분리.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class MockupLLMClient:
    def __init__(self) -> None:
        # .env의 AOAI_* 우선, 없으면 MOCKUP_AOAI_* fallback
        self._endpoint = settings.AOAI_ENDPOINT or settings.MOCKUP_AOAI_ENDPOINT
        self._api_key = settings.AOAI_API_KEY or settings.MOCKUP_AOAI_API_KEY
        self._model = settings.AOAI_DEPLOYMENT or settings.MOCKUP_AOAI_DEPLOYMENT

    async def complete(
        self,
        system: str,
        user: str,
        stream: bool = False,
        max_tokens: int | None = None,
        temperature: float = 0.35,
    ) -> str | AsyncIterator[str]:
        # MOCKUP_AOAI_* 가 설정되지 않았거나 접근 불가 환경이면 기본 llm_client로 fallback.
        # (VPN/사내 네트워크 밖에서도 Mockup 파이프라인이 동작하도록)
        if not self._endpoint or not self._api_key:
            from app.llm.client import llm_client
            max_tok = max_tokens if max_tokens is not None else settings.MOCKUP_AOAI_MAX_TOKENS
            return await llm_client.complete(system, user, stream=stream, max_tokens=max_tok)

        max_tok = max_tokens if max_tokens is not None else settings.MOCKUP_AOAI_MAX_TOKENS
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tok,
            "stream": False,
        }
        headers = {"Content-Type": "application/json", "X-Api-Key": self._api_key}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=30.0), verify=False
        ) as c:
            r = await c.post(self._endpoint, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("[MockupLLM] response received — %d chars", len(content) if content else 0)
            content = content or ""

        if not stream:
            return content

        # stream=True인 경우에도 이 게이트웨이는 단일 응답만 반환하므로
        # AsyncIterator로 래핑해서 반환한다.
        async def _as_stream() -> AsyncIterator[str]:
            yield content

        return _as_stream()


mockup_client = MockupLLMClient()
