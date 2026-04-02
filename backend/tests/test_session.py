import pytest
from fastapi import HTTPException

from app.config import settings
from app.session import SessionStore


@pytest.fixture
def store():
    s = SessionStore()
    return s


def test_create(store):
    session = store.create("sid-1")
    assert session.session_id == "sid-1"
    assert session.llm_call_count == 0
    assert session.raw_input is None


def test_get(store):
    created = store.create("sid-2")
    fetched = store.get("sid-2")
    assert fetched is created


def test_get_nonexistent(store):
    result = store.get("does-not-exist")
    assert result is None


def test_get_or_create_creates(store):
    session = store.get_or_create("new-sid")
    assert session.session_id == "new-sid"


def test_get_or_create_returns_existing(store):
    first = store.create("existing-sid")
    second = store.get_or_create("existing-sid")
    assert first is second


def test_delete(store):
    store.create("to-delete")
    assert store.get("to-delete") is not None
    store.delete("to-delete")
    assert store.get("to-delete") is None


def test_delete_nonexistent_noop(store):
    # Should not raise
    store.delete("never-existed")


def test_increment_llm_calls(store):
    store.create("sid-count")
    store.increment_llm_calls("sid-count")
    store.increment_llm_calls("sid-count")
    session = store.get("sid-count")
    assert session.llm_call_count == 2


def test_increment_llm_calls_nonexistent(store):
    with pytest.raises(HTTPException) as exc_info:
        store.increment_llm_calls("ghost-session")
    assert exc_info.value.status_code == 404


def test_rate_limit(store):
    store.create("rate-sid")
    # Manually set count to the limit
    session = store.get("rate-sid")
    session.llm_call_count = settings.MAX_LLM_CALLS_PER_SESSION

    with pytest.raises(HTTPException) as exc_info:
        store.increment_llm_calls("rate-sid")
    assert exc_info.value.status_code == 429
