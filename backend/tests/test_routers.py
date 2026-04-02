import pytest


SESSION_HEADER = {"X-Session-ID": "test-session-123"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_input_text(client):
    response = client.post(
        "/api/input",
        params={"text": "We need a login system"},
        headers=SESSION_HEADER,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["chars"] == len("We need a login system")


def test_input_no_session(client):
    response = client.post(
        "/api/input",
        data={"text": "hello"},
    )
    assert response.status_code == 400


def test_input_too_long(client):
    long_text = "a" * 50001
    response = client.post(
        "/api/input",
        params={"text": long_text},
        headers=SESSION_HEADER,
    )
    assert response.status_code == 413


def test_get_session(client):
    # Create a session via input first
    client.post(
        "/api/input",
        params={"text": "requirements text"},
        headers=SESSION_HEADER,
    )
    response = client.get("/api/session", headers=SESSION_HEADER)
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "test-session-123"
    assert body["raw_input"]["text"] == "requirements text"


def test_get_session_not_found(client):
    # GET /api/session with an unknown session still creates one via get_or_create
    # so we verify it returns 200 with the new session (no 404 from this endpoint)
    response = client.get("/api/session", headers={"X-Session-ID": "unknown-999"})
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "unknown-999"


def test_export_no_session(client):
    response = client.get("/api/export", headers={"X-Session-ID": "no-such-session"})
    assert response.status_code == 404


def test_export_no_spec(client):
    # Create session via input, then try to export without a spec
    client.post(
        "/api/input",
        params={"text": "some text"},
        headers=SESSION_HEADER,
    )
    response = client.get("/api/export", headers=SESSION_HEADER)
    assert response.status_code == 400


def test_session_restore(client):
    from datetime import datetime, timezone

    session_data = {
        "session_id": "restored-session",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "spec_markdown": "# My Spec",
        "spec_version": 1,
        "llm_call_count": 5,
    }
    response = client.post(
        "/api/session/restore",
        json={"session_state": session_data},
        headers={"X-Session-ID": "restored-session"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "restored-session"
    assert body["spec_markdown"] == "# My Spec"
    assert body["spec_version"] == 1
    assert body["llm_call_count"] == 5
