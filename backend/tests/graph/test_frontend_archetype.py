"""Ported frontend archetype inference (from contract/plan, not ctx). No LLM."""

from app.llm.graph.frontend_ctx import infer_frontend_archetype, frontend_route_parts


def _plan(files):
    return {"files": files}


def test_archetype_editable_grid_from_spec():
    plan = _plan([{"file_type": "vue_page", "layer": "frontend", "description": "list"}])
    arch = infer_frontend_archetype("교육 목록을 저장/삭제한다", plan)
    assert arch == "editable-grid"


def test_archetype_summary_filter_from_sumgrid():
    plan = _plan([{"file_type": "vue_sum_grid", "layer": "frontend", "description": "집계"}])
    arch = infer_frontend_archetype("상태별 집계 화면", plan)
    assert arch == "summary-filter"


def test_archetype_list_query_default():
    plan = _plan([{"file_type": "vue_page", "layer": "frontend", "description": "조회"}])
    arch = infer_frontend_archetype("단순 목록 조회", plan)
    assert arch == "list-query"


def test_archetype_popup_linked():
    plan = _plan([{"file_type": "vue_page", "layer": "frontend", "description": "popup"}])
    arch = infer_frontend_archetype("사용자 검색 팝업 lookup", plan)
    assert arch == "popup-linked"


def test_route_parts_from_plan():
    plan = _plan([
        {"file_type": "vue_page", "layer": "frontend",
         "file_path": "frontend/src/pages/edu/result/CPMSEDURSLTLST/index.vue"},
    ])
    parts = frontend_route_parts(plan)
    assert parts == ("edu", "result", "CPMSEDURSLTLST")


def test_route_parts_none_when_no_match():
    plan = _plan([{"file_type": "vue_page", "layer": "frontend",
                   "file_path": "frontend/src/pages/Foo.vue"}])
    assert frontend_route_parts(plan) is None
