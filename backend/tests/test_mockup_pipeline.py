import pytest
from unittest.mock import AsyncMock, patch

from app.llm.mockup_pipeline import mockup_pipeline


@pytest.mark.asyncio
async def test_generate_mockup_streaming_yields_chunks():
    async def fake_stream():
        yield "<template>"
        yield "</template>"

    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value=fake_stream())
        result = []
        async for chunk in mockup_pipeline.generate_mockup_streaming("# brief"):
            result.append(chunk)
        assert "".join(result) == "<template></template>"


@pytest.mark.asyncio
async def test_generate_mockup_streaming_fallback_when_not_async_iter():
    """게이트웨이가 스트리밍 미지원 → 전체 문자열 반환 시 줄 단위 에뮬레이션."""
    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value="line1\nline2\n")
        result = []
        async for chunk in mockup_pipeline.generate_mockup_streaming("# brief"):
            result.append(chunk)
        assert "".join(result) == "line1\nline2\n"


@pytest.mark.asyncio
async def test_parse_interview_returns_string():
    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value="## Keep\n- ...")
        out = await mockup_pipeline.parse_interview("<vue>", "raw text")
        assert out.startswith("## Keep")


@pytest.mark.asyncio
async def test_generate_spec_streaming():
    async def fake_stream():
        yield "# Spec\n"
        yield "## 1. "

    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value=fake_stream())
        result = []
        async for chunk in mockup_pipeline.generate_spec_streaming("b", "v", "n"):
            result.append(chunk)
        assert "".join(result) == "# Spec\n## 1. "
