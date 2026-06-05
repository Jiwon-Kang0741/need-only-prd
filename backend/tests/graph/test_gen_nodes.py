import pytest
from app.llm.graph import gen_nodes
from app.llm.graph.contract_schema import parse_contract
from app.llm.graph.plan_and_bind import plan_and_bind

pytestmark = pytest.mark.asyncio


def _contract():
    return plan_and_bind({"contract": parse_contract({
        "identity": {"module": "edu", "category": "pondg", "screen_id": "cpmsEduPondgLst",
                     "class_name": "CpmsEduPondgLst", "program_id": "CPMSEDUPONDGLST"},
        "archetype": "list-detail",
        "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
        "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
        "frontend": {"components": ["SearchForm", "DataTable"]},
    }).model_dump()})["contract"]


async def test_gen_backend_node_produces_wrapped_files(monkeypatch):
    from app.llm.graph import gen_backend as gb
    class _C:
        async def complete(self, s, u, max_tokens=16384): return "class X {}"
    monkeypatch.setattr(gb, "gpt55_client", _C())
    out = await gen_nodes.gen_backend_node({"contract": _contract()})
    files = out["files"]
    types = {gf["file_type"] for gf in files.values()}
    assert {"dto_request", "dto_response", "mapper_xml", "dao_impl", "service_impl"} <= types
    for gf in files.values():
        assert set(gf) >= {"file_path", "file_type", "layer", "content", "status"}
        assert gf["layer"] == "backend"


async def test_gen_frontend_node_produces_files(monkeypatch):
    from app.llm.graph import gen_frontend as gfm
    class _C:
        async def complete(self, s, u, max_tokens=16384): return "<template/>"
    monkeypatch.setattr(gfm, "gpt55_client", _C())
    out = await gen_nodes.gen_frontend_node({"contract": _contract()})
    types = {gf["file_type"] for gf in out["files"].values()}
    assert "vue_page" in types and "vue_types" in types and "vue_datatable" in types


async def test_gen_data_node_produces_db_init(monkeypatch):
    from app.llm.graph import gen_data as gd
    class _C:
        async def complete(self, s, u, max_tokens=16384): return "CREATE TABLE t();"
    monkeypatch.setattr(gd, "gpt55_client", _C())
    out = await gen_nodes.gen_data_node({"contract": _contract()})
    paths = {gf["file_path"] for gf in out["files"].values()}
    assert "db/init.sql" in paths


def test_validate_node_runs_all_validators():
    contract = _contract()
    files = {"d/X.java": {"file_path": "d/X.java", "file_type": "dao_impl", "layer": "backend",
                          "wave": 0, "content": "package biz.edu.dao;\nclass X {}",
                          "status": "ok", "status_log": []}}
    out = gen_nodes.validate_node({"contract": contract, "files": files})
    assert "open_issues" in out and isinstance(out["open_issues"], list)
