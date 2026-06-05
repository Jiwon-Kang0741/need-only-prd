import pytest
from app.llm.graph import gen_frontend as gf

pytestmark = pytest.mark.asyncio

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST", "window_id": "cpmsEduPondgLst"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
    "fields": {"request": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String", "filter": "ILIKE"}],
               "response": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String"}]},
    "api": [{"method": "selectList", "service_id": "CpmsEduPondgLst/selectList",
             "url": "/online/mvcJson/CpmsEduPondgLst-selectList",
             "req_dto": "CpmsEduPondgLstReqDto", "res_dto": "CpmsEduPondgLstResDto"}],
    "frontend": {"components": ["SearchForm", "DataTable"], "search_fields": ["empNm"],
                 "columns": [{"field": "empNm", "header": "사원명", "width": "140px"}],
                 "common_code_load": "ensureLoaded"},
    "bindings": {"paths": {
        "vue_page": "src/pages/edu/pondg/cpmsEduPondgLst/index.vue",
        "vue_page_scss": "src/pages/edu/pondg/cpmsEduPondgLst/cpmsEduPondgLst.scss",
        "vue_api": "src/api/pages/edu/pondg/cpmsEduPondgLst.ts",
        "vue_types": "src/api/pages/edu/pondg/types.ts",
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


async def test_gen_types_returns_types_file(monkeypatch):
    c = _Scripted("```ts\nexport interface X {}\n```")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_types(_CONTRACT, guide="GUIDE")
    assert _CONTRACT["bindings"]["paths"]["vue_types"] in out
    assert all("```" not in v for v in out.values())
    assert c.calls == 1
    u = c.last_user
    assert "empNm" in u and "GUIDE" in u
    assert "CpmsEduPondgLstResDto" in u


async def test_gen_api_grounds_in_serviceid_and_types(monkeypatch):
    c = _Scripted("export const api = {}")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_api(_CONTRACT, guide="GUIDE", types="export interface R {}")
    assert _CONTRACT["bindings"]["paths"]["vue_api"] in out
    assert c.calls == 1
    u = c.last_user
    assert "/online/mvcJson/CpmsEduPondgLst-selectList" in u
    assert "api.post" in u
    assert "interface R" in u
