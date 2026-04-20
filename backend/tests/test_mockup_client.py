import pytest
from unittest.mock import AsyncMock, patch
from app.llm.mockup_client import MockupLLMClient


def test_client_reads_config():
    client = MockupLLMClient()
    assert hasattr(client, "_endpoint")
    assert hasattr(client, "_api_key")
    assert hasattr(client, "_model")


@pytest.mark.asyncio
async def test_complete_falls_back_to_llm_client_when_config_missing():
    """MOCKUP_AOAI_* 미설정 시 기본 llm_client로 fallback."""
    client = MockupLLMClient()
    client._endpoint = ""
    client._api_key = ""
    with patch("app.llm.client.llm_client") as mock_client:
        mock_client.complete = AsyncMock(return_value="fallback-ok")
        result = await client.complete("sys", "usr", stream=False)
        assert result == "fallback-ok"
        mock_client.complete.assert_called_once()


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
