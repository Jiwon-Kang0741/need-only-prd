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


import json


@pytest.mark.llm
def test_generate_streams_to_complete(monkeypatch):
    # keep generator prompts small
    import app.llm.graph.nodes as nodes_mod
    monkeypatch.setattr(nodes_mod.guides, "load_guide_for_file_type",
                        lambda ft: "Use String for IDs. Follow CPMS.")
    client = TestClient(app)
    sess = session_store.get_or_create("rt-e2e")
    sess.spec_markdown = "# 교육 (EDU001)\n교육명(eduPgmNm) 텍스트.\n"
    from app.models import MockupState
    sess.mockup_state = MockupState(
        screen_id="EDU001", screen_name="교육", page_type="list",
        vue_code='<template><Column field="eduPgmNm"/></template>')

    types_seen = []
    with client.stream("POST", "/api/codegen/generate",
                       headers={"X-Session-ID": "rt-e2e"}) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = json.loads(line[len("data:"):].strip())
            types_seen.append(payload.get("type"))
            if payload.get("type") in ("complete", "error"):
                break

    assert "complete" in types_seen
    assert "error" not in types_seen
    # we saw node-level progress
    assert "node_start" in types_seen
