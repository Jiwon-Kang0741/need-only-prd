import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_brief_creates_state():
    headers = {"X-Session-ID": "mockup-router-test-1"}
    r = client.post(
        "/api/mockup/brief",
        json={"project_id": "TEST_PRJ", "project_name": "테스트", "brief_md": "# Brief"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["project_id"] == "TEST_PRJ"

    s = client.get("/api/session", headers=headers).json()
    assert s["mockup_state"]["project_id"] == "TEST_PRJ"
    assert s["mockup_state"]["current_step"] == 1


def test_brief_rejects_invalid_project_id():
    r = client.post(
        "/api/mockup/brief",
        json={"project_id": "invalid-id!", "project_name": "X", "brief_md": "x"},
        headers={"X-Session-ID": "mockup-router-test-2"},
    )
    assert r.status_code == 400


def test_reset_clears_state():
    headers = {"X-Session-ID": "mockup-router-test-3"}
    client.post(
        "/api/mockup/brief",
        json={"project_id": "R1", "project_name": "R", "brief_md": "x"},
        headers=headers,
    )
    r = client.post("/api/mockup/reset", headers=headers)
    assert r.status_code == 200
    s = client.get("/api/session", headers=headers).json()
    assert s["mockup_state"] is None


def test_parse_interview_requires_mockup():
    """Step 3는 mockup_vue가 이미 생성되어 있어야 함."""
    headers = {"X-Session-ID": "mockup-router-test-4"}
    client.post(
        "/api/mockup/brief",
        json={"project_id": "P4", "project_name": "X", "brief_md": "x"},
        headers=headers,
    )
    r = client.post(
        "/api/mockup/parse-interview",
        json={"raw_interview_text": "test"},
        headers=headers,
    )
    assert r.status_code == 400
