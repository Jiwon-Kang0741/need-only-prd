import json
import pytest
from app.llm.graph.build import build_graph
from app.llm.graph import contract_resolve, gen_backend, gen_frontend, gen_data

pytestmark = pytest.mark.asyncio

_CONTRACT_JSON = json.dumps({
    "identity": {"module": "edu", "category": "pondg", "screen_id": "cpmsEduPondgLst",
                 "class_name": "CpmsEduPondgLst", "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm", "db_type": "varchar(100)"}]},
    "frontend": {"components": ["SearchForm", "DataTable"]},
})


class _Const:
    def __init__(self, reply): self.reply = reply
    async def complete(self, s, u, max_tokens=16384): return self.reply


async def test_new_graph_runs_end_to_end(monkeypatch):
    monkeypatch.setattr(contract_resolve, "gpt55_client", _Const(_CONTRACT_JSON))
    monkeypatch.setattr(gen_backend, "gpt55_client", _Const("package x;\nclass X {}"))
    monkeypatch.setattr(gen_frontend, "gpt55_client", _Const('<script setup lang="ts"></script>'))
    monkeypatch.setattr(gen_data, "gpt55_client", _Const("CREATE TABLE t();"))

    graph = build_graph()
    out = await graph.ainvoke({
        "spec_markdown": "교육 실적 조회", "confirmed_vue": "<template/>",
        "table_info": "cptb_edu_pondg: emp_nm varchar", "page_type": "list-detail",
        "files": {},
    }, {"recursion_limit": 50})
    files = out["files"]
    layers = {gf["layer"] for gf in files.values()}
    assert {"backend", "frontend", "data"} <= layers
    ftypes = {gf["file_type"] for gf in files.values()}
    assert {"dto_request", "mapper_xml", "dao_impl", "service_impl",
            "vue_page", "vue_types", "db_init_sql"} <= ftypes
    assert isinstance(out.get("open_issues", []), list)
