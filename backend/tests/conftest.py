import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.session import session_store

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def session_id():
    return "test-session-123"

@pytest.fixture(autouse=True)
def clear_sessions():
    session_store._cache.clear()
    yield
    session_store._cache.clear()
