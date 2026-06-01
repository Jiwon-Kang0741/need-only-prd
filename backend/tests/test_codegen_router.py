import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.session import session_store


@pytest.fixture(autouse=True)
def _clear():
    session_store._cache.clear()
    yield
    session_store._cache.clear()


def test_generate_requires_spec():
    client = TestClient(app)
    sess = session_store.get_or_create("rt-1")
    sess.spec_markdown = None
    r = client.post("/api/codegen/generate", headers={"X-Session-ID": "rt-1"})
    assert r.status_code == 400


def test_generate_requires_existing_session_with_spec():
    client = TestClient(app)
    # no session created -> get_or_create makes one with no spec -> 400
    r = client.post("/api/codegen/generate", headers={"X-Session-ID": "rt-missing"})
    assert r.status_code == 400


def test_resume_requires_session():
    client = TestClient(app)
    r = client.post("/api/codegen/resume", headers={"X-Session-ID": "rt-none"})
    # no prior codegen run -> 400 or 404
    assert r.status_code in (400, 404)
