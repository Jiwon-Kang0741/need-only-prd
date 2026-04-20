import pytest
from unittest.mock import AsyncMock, patch
from app.llm.mockup_client import MockupLLMClient


def test_client_reads_config():
    client = MockupLLMClient()
    assert hasattr(client, "_endpoint")
    assert hasattr(client, "_api_key")
    assert hasattr(client, "_model")


@pytest.mark.asyncio
async def test_complete_non_streaming_raises_without_config():
    client = MockupLLMClient()
    client._endpoint = ""
    client._api_key = ""
    with pytest.raises(RuntimeError, match="MOCKUP_AOAI"):
        await client.complete("sys", "usr", stream=False)


@pytest.mark.asyncio
async def test_complete_non_streaming_returns_content():
    client = MockupLLMClient()
    client._endpoint = "http://fake"
    client._api_key = "fake"
    client._model = "gpt-5.2"

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {
        "choices": [{"message": {"content": "hello world"}}]
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await client.complete("sys", "usr", stream=False)

    assert result == "hello world"
