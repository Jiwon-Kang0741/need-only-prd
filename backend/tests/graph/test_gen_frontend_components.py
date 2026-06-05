import pytest
from app.llm.graph import gen_frontend as gf

pytestmark = pytest.mark.asyncio

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST", "window_id": "cpmsEduPondgLst"},
    "archetype": "list-detail",
    "frontend": {"components": ["SearchForm", "DataTable"], "search_fields": ["empNm"],
                 "columns": [{"field": "empNm", "header": "사원명", "width": "140px"}],
                 "common_code_load": "ensureLoaded"},
    "bindings": {"paths": {
        "vue_page": "src/pages/edu/pondg/cpmsEduPondgLst/index.vue",
        "vue_page_scss": "src/pages/edu/pondg/cpmsEduPondgLst/cpmsEduPondgLst.scss",
        "vue_searchform": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstSearchForm/CpmsEduPondgLstSearchForm.vue",
        "vue_searchform_scss": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstSearchForm/CpmsEduPondgLstSearchForm.scss",
        "vue_datatable": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstDataTable/CpmsEduPondgLstDataTable.vue",
        "vue_datatable_scss": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstDataTable/CpmsEduPondgLstDataTable.scss",
        "vue_datatable_utils": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstDataTable/utils/index.ts",
    }},
}


class _Scripted:
    def __init__(self, reply):
        self.reply = reply
        self.last_user = None
        self.calls = 0
    async def complete(self, system, user, max_tokens=16384):
        self.calls += 1
        self.last_user = user
        return self.reply


async def test_gen_component_datatable_returns_vue_scss_utils(monkeypatch):
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_component(_CONTRACT, guide="GUIDE", comp="DataTable", types="export interface R{}")
    p = _CONTRACT["bindings"]["paths"]
    assert p["vue_datatable"] in out and p["vue_datatable_scss"] in out and p["vue_datatable_utils"] in out
    assert c.calls == 2
    u = c.last_user
    assert "GUIDE" in u and "DataTable2" in u and ":columns" in u


async def test_gen_component_searchform_no_utils(monkeypatch):
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_component(_CONTRACT, guide="GUIDE", comp="SearchForm", types="x")
    p = _CONTRACT["bindings"]["paths"]
    assert p["vue_searchform"] in out and p["vue_searchform_scss"] in out
    assert p["vue_datatable_utils"] not in out
    assert c.calls == 1
    u = c.last_user
    assert "inject" in u and "searchParams" in u          # SearchForm state pattern


async def test_gen_component_unknown_raises(monkeypatch):
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    with pytest.raises(ValueError):
        await gf.gen_component(_CONTRACT, guide="GUIDE", comp="Bogus", types="x")


async def test_gen_index_generated_last_binds_children(monkeypatch):
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    children = {"CpmsEduPondgLstSearchForm": "<template>SF</template>",
                "CpmsEduPondgLstDataTable": "<template>DT</template>"}
    out = await gf.gen_index(_CONTRACT, guide="GUIDE", components=children, types="x")
    p = _CONTRACT["bindings"]["paths"]
    assert p["vue_page"] in out and p["vue_page_scss"] in out
    assert c.calls == 1
    u = c.last_user
    assert "CpmsEduPondgLstSearchForm" in u and "CpmsEduPondgLstDataTable" in u
    assert "provide" in u and "searchParams" in u
    assert "<template>SF</template>" in u


async def test_gen_index_wires_real_api_not_stub(monkeypatch):
    # The index must call the real generated API client in its handlers, not stub
    # handleSearch with empty arrays / TODO. So gen_index gets the api source and
    # the prompt mandates calling it.
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    children = {"CpmsEduPondgLstSearchForm": "<template>SF</template>"}
    api_src = "export function fetchCpmsEduPondgLstList(p) { return api.post('/x', p); }"
    out = await gf.gen_index(_CONTRACT, guide="GUIDE", components=children, types="x", api=api_src)
    assert _CONTRACT["bindings"]["paths"]["vue_page"] in out
    u = c.last_user
    assert "fetchCpmsEduPondgLstList" in u          # real API source provided to the prompt
    assert "stub" in u.lower()                       # explicit "do NOT stub" instruction
    assert "handleSearch" in u                        # wire the actual list-fetch handler
