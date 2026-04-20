"""Mockup 기반 4단계 spec 생성 파이프라인.

원본 pfy-front 플로우:
  brief.md → Mockup.vue → interviewNotes.md → spec.md

모든 LLM 호출은 mockup_client(gpt-5.2, 원본 사내 게이트웨이)를 사용한다.
기존 llm_client(gpt-5.4)는 코드 생성 / 텍스트 spec 파이프라인 전용.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm.mockup_client import mockup_client
from app.llm.mockup_prompts import (
    interview_parser_prompt,
    master_spec_prompt,
    mockup_generation_prompt,
)


class MockupPipeline:
    async def generate_mockup_streaming(self, brief_md: str) -> AsyncIterator[str]:
        system, user = mockup_generation_prompt(brief_md)
        result = await mockup_client.complete(system, user, stream=True)
        async for chunk in _as_async_iter(result):
            yield chunk

    async def parse_interview(self, mockup_vue: str, raw_interview_text: str) -> str:
        system, user = interview_parser_prompt(mockup_vue, raw_interview_text)
        response = await mockup_client.complete(system, user, stream=False)
        return str(response)

    async def generate_spec_streaming(
        self,
        brief_md: str,
        mockup_vue: str,
        interview_notes_md: str,
    ) -> AsyncIterator[str]:
        system, user = master_spec_prompt(brief_md, mockup_vue, interview_notes_md)
        result = await mockup_client.complete(system, user, stream=True)
        async for chunk in _as_async_iter(result):
            yield chunk


async def _as_async_iter(result) -> AsyncIterator[str]:
    """게이트웨이가 stream 미지원 시 전체 응답 문자열 → 줄 단위 yield로 에뮬레이션."""
    if hasattr(result, "__aiter__"):
        async for chunk in result:
            yield chunk
    else:
        text = str(result)
        for line in text.splitlines(keepends=True):
            yield line


mockup_pipeline = MockupPipeline()
