from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import (
    ChatMessage,
    ChatRequest,
    InputRequest,
    RawInput,
    SessionState,
)


def test_raw_input_valid():
    now = datetime.now(timezone.utc)
    raw = RawInput(text="hello", source_type="text", uploaded_at=now)
    assert raw.text == "hello"
    assert raw.source_type == "text"
    assert raw.uploaded_at == now


def test_raw_input_default_source_type():
    now = datetime.now(timezone.utc)
    raw = RawInput(text="hello", uploaded_at=now)
    assert raw.source_type == "text"


def test_session_state_defaults():
    now = datetime.now(timezone.utc)
    state = SessionState(session_id="abc", created_at=now)
    assert state.session_id == "abc"
    assert state.raw_input is None
    assert state.extracted_requirements is None
    assert state.spec_markdown is None
    assert state.spec_version == 0
    assert state.chat_history == []
    assert state.validation_result is None
    assert state.llm_call_count == 0


def test_chat_message_user():
    now = datetime.now(timezone.utc)
    msg = ChatMessage(role="user", content="hi", timestamp=now)
    assert msg.role == "user"
    assert msg.content == "hi"


def test_chat_message_assistant():
    now = datetime.now(timezone.utc)
    msg = ChatMessage(role="assistant", content="hello", timestamp=now)
    assert msg.role == "assistant"


def test_chat_message_invalid_role():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError):
        ChatMessage(role="system", content="oops", timestamp=now)


def test_input_request_valid():
    req = InputRequest(text="some requirements")
    assert req.text == "some requirements"


def test_input_request_missing_text():
    with pytest.raises(ValidationError):
        InputRequest()


def test_chat_request_valid():
    req = ChatRequest(message="update the spec")
    assert req.message == "update the spec"


def test_chat_request_missing_message():
    with pytest.raises(ValidationError):
        ChatRequest()
