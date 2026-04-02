import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.llm.pipeline import SpecPipeline
from app.models import ChatMessage


@pytest.fixture
def pipeline():
    return SpecPipeline()


MOCK_REQUIREMENTS = {
    "functional_requirements": [{"id": "FR-001", "description": "Login", "priority": "high"}],
    "non_functional_requirements": [],
    "constraints": ["Must use REST"],
    "assumptions": ["Single tenant"],
    "ambiguities": [],
}

MOCK_VALIDATION = {
    "score": 85,
    "covered": [{"id": "FR-001", "evidence": "Section 1 covers login"}],
    "missing": [],
    "suggestions": ["Consider adding rate limiting"],
}


@patch("app.llm.pipeline.llm_client")
@pytest.mark.asyncio
async def test_extract_requirements(mock_client, pipeline):
    mock_client.complete = AsyncMock(return_value=json.dumps(MOCK_REQUIREMENTS))
    result = await pipeline.extract_requirements("Build a login page")

    assert result["functional_requirements"][0]["id"] == "FR-001"
    mock_client.complete.assert_called_once()
    _, kwargs = mock_client.complete.call_args
    assert kwargs.get("stream") is False or not kwargs.get("stream")


@patch("app.llm.pipeline.llm_client")
@pytest.mark.asyncio
async def test_extract_requirements_invalid_json(mock_client, pipeline):
    mock_client.complete = AsyncMock(return_value="not json")
    with pytest.raises(json.JSONDecodeError):
        await pipeline.extract_requirements("some text")


@patch("app.llm.pipeline.llm_client")
@pytest.mark.asyncio
async def test_generate_spec_streaming(mock_client, pipeline):
    async def mock_stream(*args, **kwargs):
        for chunk in ["# Spec\n", "## Overview\n", "Details here"]:
            yield chunk

    mock_client.complete = AsyncMock(return_value=mock_stream())
    chunks = []
    async for chunk in pipeline.generate_spec(MOCK_REQUIREMENTS, "raw text"):
        chunks.append(chunk)

    assert len(chunks) == 3
    assert "".join(chunks) == "# Spec\n## Overview\nDetails here"


@patch("app.llm.pipeline.llm_client")
@pytest.mark.asyncio
async def test_refine_spec_short_history(mock_client, pipeline):
    """History <= 5 rounds should not trigger summarization."""
    async def mock_stream(*args, **kwargs):
        yield "# Updated Spec"

    mock_client.complete = AsyncMock(return_value=mock_stream())
    history = [
        ChatMessage(role="user", content="Add auth", timestamp=datetime.now(timezone.utc)),
        ChatMessage(role="assistant", content="Done", timestamp=datetime.now(timezone.utc)),
    ]
    chunks = []
    async for chunk in pipeline.refine_spec("# Old Spec", history, "Add tests"):
        chunks.append(chunk)

    assert chunks == ["# Updated Spec"]
    # Only 1 call (refinement), no summarization
    assert mock_client.complete.call_count == 1


@patch("app.llm.pipeline.llm_client")
@pytest.mark.asyncio
async def test_refine_spec_long_history_triggers_summarization(mock_client, pipeline):
    """History > 5 rounds should summarize older messages."""
    call_count = 0

    async def mock_complete(system, user, stream=False):
        nonlocal call_count
        call_count += 1
        if not stream:
            # Summarization call
            return "Summary of earlier conversation"

        async def gen():
            yield "# Refined Spec"

        return gen()

    mock_client.complete = AsyncMock(side_effect=mock_complete)

    # 6 rounds = 12 messages
    history = []
    for i in range(6):
        history.append(ChatMessage(role="user", content=f"Change {i}", timestamp=datetime.now(timezone.utc)))
        history.append(ChatMessage(role="assistant", content=f"Done {i}", timestamp=datetime.now(timezone.utc)))

    chunks = []
    async for chunk in pipeline.refine_spec("# Old Spec", history, "Final change"):
        chunks.append(chunk)

    assert chunks == ["# Refined Spec"]
    # 2 calls: summarization + refinement
    assert call_count == 2


@patch("app.llm.pipeline.llm_client")
@pytest.mark.asyncio
async def test_validate_coverage(mock_client, pipeline):
    mock_client.complete = AsyncMock(return_value=json.dumps(MOCK_VALIDATION))
    result = await pipeline.validate_coverage("raw text", "# Spec", MOCK_REQUIREMENTS)

    assert result["score"] == 85
    assert len(result["covered"]) == 1
    assert result["suggestions"] == ["Consider adding rate limiting"]


@patch("app.llm.pipeline.llm_client")
@pytest.mark.asyncio
async def test_validate_coverage_invalid_json(mock_client, pipeline):
    mock_client.complete = AsyncMock(return_value="invalid")
    with pytest.raises(json.JSONDecodeError):
        await pipeline.validate_coverage("raw", "spec", {})
