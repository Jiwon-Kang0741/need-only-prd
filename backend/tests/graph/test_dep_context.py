"""_dep_context injects only referenced dependency file types (F9). No LLM."""

from app.llm.graph import nodes


def _f(path, ftype, wave, content="X"):
    return {"file_path": path, "file_type": ftype, "layer": "backend",
            "wave": wave, "status": "ok", "status_log": [], "content": content}


def _state():
    return {"files": {
        "Req.java": _f("Req.java", "dto_request", 1, "REQ_CONTENT"),
        "Res.java": _f("Res.java", "dto_response", 1, "RES_CONTENT"),
        "T.ts": _f("T.ts", "vue_types", 1, "TYPES_CONTENT"),
        "Dao.java": _f("Dao.java", "dao_impl", 2, "DAO_CONTENT"),
        "Page.vue": _f("Page.vue", "vue_page", 2, "PAGE_CONTENT"),
    }}


def test_service_gets_dto_and_dao_not_vue():
    spec = {"file_type": "service_impl", "wave": 3}
    ctx = nodes._dep_context(_state(), spec)
    assert "REQ_CONTENT" in ctx and "RES_CONTENT" in ctx and "DAO_CONTENT" in ctx
    assert "TYPES_CONTENT" not in ctx  # vue_types is irrelevant to a service
    assert "PAGE_CONTENT" not in ctx


def test_vue_page_gets_only_vue_types():
    spec = {"file_type": "vue_page", "wave": 2}
    ctx = nodes._dep_context(_state(), spec)
    assert "TYPES_CONTENT" in ctx
    assert "DAO_CONTENT" not in ctx
    assert "REQ_CONTENT" not in ctx


def test_dao_gets_only_dtos():
    spec = {"file_type": "dao_impl", "wave": 2}
    ctx = nodes._dep_context(_state(), spec)
    assert "REQ_CONTENT" in ctx and "RES_CONTENT" in ctx
    assert "TYPES_CONTENT" not in ctx


def test_leaf_file_gets_no_deps():
    spec = {"file_type": "dto_request", "wave": 1}
    assert nodes._dep_context(_state(), spec) == ""
