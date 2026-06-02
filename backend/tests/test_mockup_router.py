from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_scaffold_creates_mockup_state():
    headers = {"X-Session-ID": "mockup-router-scaffold-1"}
    r = client.post(
        "/api/mockup/scaffold",
        json={
            "screen_id": "TestScreen",
            "screen_name": "테스트 화면",
            "page_type": "list",
            "fields": [
                {
                    "key": "name",
                    "label": "이름",
                    "type": "text",
                    "searchable": True,
                    "listable": True,
                    "detailable": False,
                    "editable": False,
                    "required": False,
                }
            ],
        },
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert "vue_code" in body
    assert len(body["vue_code"]) > 0

    s = client.get("/api/session", headers=headers).json()
    assert s["mockup_state"] is not None
    assert s["mockup_state"]["screen_id"] == "TestScreen"
    assert s["mockup_state"]["current_step"] == 2


def test_scaffold_rejects_invalid_page_type():
    r = client.post(
        "/api/mockup/scaffold",
        json={
            "screen_id": "X",
            "screen_name": "Y",
            "page_type": "not-a-valid-type",
            "fields": [{"key": "a", "label": "A", "type": "text"}],
        },
        headers={"X-Session-ID": "mockup-router-scaffold-2"},
    )
    assert r.status_code == 422


def test_ai_annotate_requires_vue_code():
    """스캐폴드 없이 주석 분석 호출 시 400."""
    headers = {"X-Session-ID": "mockup-router-annotate-1"}
    r = client.post("/api/mockup/ai-annotate", headers=headers)
    assert r.status_code == 400
