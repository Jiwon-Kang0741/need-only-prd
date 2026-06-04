import pytest

from app.llm.graph import nodes

pytestmark = pytest.mark.asyncio

_CONTRACT = {
    "screen": {"id": "CPMSEDURSLTLST", "name": "교육이수현황", "type": "list-detail"},
    "fields": [
        {"vue_field": "employeeName", "db_column": "EMP_NM", "type": "string"},
        {"vue_field": "score", "db_column": "SCORE", "type": "number"},
    ],
    "api_signatures": [],
}
_PLAN = {"files": [
    {"file_path": "x/CpmsEduRsltLstReqDto.java", "file_type": "dto_request"},
    {"file_path": "x/CpmsEduRsltLstResDto.java", "file_type": "dto_response"},
    {"file_path": "x/CpmsEduRsltLstDaoImpl.java", "file_type": "dao_impl"},
    {"file_path": "x/CpmsEduRsltLstMapper.xml", "file_type": "mapper_xml"},
    {"file_path": "x/CpmsEduRsltLstServiceImpl.java", "file_type": "service_impl"},
]}


async def test_derive_contract_builds_operations():
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": _PLAN})
    ops = out["contract"]["operations"]
    ids = {o["statement_id"] for o in ops}
    # screen_code derived from plan = "CpmsEduRsltLst" → suffixed ids
    assert {"selectCpmsEduRsltLstList", "selectCpmsEduRsltLstCount",
            "selectCpmsEduRsltLst", "insertCpmsEduRsltLst",
            "updateCpmsEduRsltLst", "deleteCpmsEduRsltLst"} <= ids
    one = next(o for o in ops if o["op"] == "selectList")
    assert one["dao_method"] == "selectCpmsEduRsltLstList"
    assert one["mybatis_tag"] == "select"
    assert one["param_type"] == "CpmsEduRsltLstReqDto"


async def test_derive_contract_builds_dtos():
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": _PLAN})
    dtos = {d["name"]: d for d in out["contract"]["dtos"]}
    assert "CpmsEduRsltLstReqDto" in dtos and "CpmsEduRsltLstResDto" in dtos
    res_fields = {f["name"]: f for f in dtos["CpmsEduRsltLstResDto"]["fields"]}
    assert res_fields["employeeName"]["java_type"] == "String"
    assert res_fields["score"]["java_type"] == "Integer"


async def test_derive_contract_reconciles_plan_dto_files_to_contract():
    # planner invented 3 request DTOs + 2 response DTOs; contract defines exactly
    # ReqDto + ResDto. The returned plan must keep only the 2 contract DTO files
    # (plus non-DTO files untouched) so generator/binding stay consistent.
    plan = {"files": [
        {"file_path": "x/CpmsEduRsltLstSearchRequest.java", "file_type": "dto_request"},
        {"file_path": "x/CpmsEduRsltLstRowRequest.java", "file_type": "dto_request"},
        {"file_path": "x/CpmsEduRsltLstSaveRequest.java", "file_type": "dto_request"},
        {"file_path": "x/CpmsEduRsltLstRowResponse.java", "file_type": "dto_response"},
        {"file_path": "x/CpmsEduRsltLstListResponse.java", "file_type": "dto_response"},
        {"file_path": "x/CpmsEduRsltLstDaoImpl.java", "file_type": "dao_impl"},
        {"file_path": "x/CpmsEduRsltLstMapper.xml", "file_type": "mapper_xml"},
        {"file_path": "x/CpmsEduRsltLstServiceImpl.java", "file_type": "service_impl"},
    ]}
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": plan})
    files = out["plan"]["files"]
    req = [f for f in files if f["file_type"] == "dto_request"]
    res = [f for f in files if f["file_type"] == "dto_response"]
    # exactly one ReqDto + one ResDto, named per contract
    assert [f["file_path"].split("/")[-1] for f in req] == ["CpmsEduRsltLstReqDto.java"]
    assert [f["file_path"].split("/")[-1] for f in res] == ["CpmsEduRsltLstResDto.java"]
    # non-DTO files untouched
    assert any(f["file_type"] == "dao_impl" for f in files)
    assert any(f["file_type"] == "service_impl" for f in files)


async def test_derive_contract_rewrites_paths_per_guide_biz_module():
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": _PLAN})
    by_type = {f["file_type"]: f["file_path"] for f in out["plan"]["files"]}
    base = "src/main/java/biz/cpms"
    assert by_type["dto_request"] == f"{base}/dto/request/CpmsEduRsltLstReqDto.java"
    assert by_type["dto_response"] == f"{base}/dto/response/CpmsEduRsltLstResDto.java"
    assert by_type["dao_impl"] == f"{base}/dao/CpmsEduRsltLstDaoImpl.java"
    assert by_type["service_impl"] == f"{base}/service/CpmsEduRsltLstServiceImpl.java"
    assert by_type["mapper_xml"] == (
        "src/main/resources/biz/cpms/mybatis/mappers/CpmsEduRsltLstMapper.xml")


async def test_derive_contract_enforces_layer_by_file_type():
    # planner mislabels layers; derive_contract must correct them (a mapper landing
    # in frontend/ would never be found by MyBatis at runtime).
    plan = {"files": [
        {"file_path": "x/CpmsEduRsltLstDaoImpl.java", "file_type": "dao_impl",
         "layer": "frontend"},
        {"file_path": "x/CpmsEduRsltLstMapper.xml", "file_type": "mapper_xml",
         "layer": "frontend"},
        {"file_path": "x/CpmsEduRsltLst.vue", "file_type": "vue_page",
         "layer": "backend"},
    ]}
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": plan})
    by_type = {f["file_type"]: f for f in out["plan"]["files"]}
    assert by_type["dao_impl"]["layer"] == "backend"
    assert by_type["mapper_xml"]["layer"] == "backend"
    assert by_type["vue_page"]["layer"] == "frontend"


async def test_derive_contract_drops_legacy_com_example_default():
    # the old hardcoded 'src/main/java/com/example/cpms/dto' default must be gone
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": _PLAN})
    assert all("com/example" not in f["file_path"] for f in out["plan"]["files"])


async def test_derive_contract_skips_op_without_dao_file():
    plan = {"files": [{"file_path": "x/CpmsEduRsltLstResDto.java", "file_type": "dto_response"}]}
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": plan})
    assert out["contract"]["operations"] == []


async def test_derive_contract_empty_fields_no_crash():
    contract = {"screen": {"id": "X", "type": "list"}, "fields": [], "api_signatures": []}
    out = await nodes.derive_contract({"contract": contract, "plan": _PLAN})
    assert "dtos" in out["contract"]


import json as _json


class _ScriptedClient:
    def __init__(self, reply):
        self._reply = reply
    async def complete(self, system, user, max_tokens=16384):
        return self._reply


async def test_contract_extract_overrides_screen_type_with_page_type(monkeypatch):
    # LLM returns type=list, but confirmed page_type=list-detail must win
    llm_contract = {"screen": {"id": "X", "name": "n", "type": "list"},
                    "fields": [], "tables": [], "search_conditions": [],
                    "table_columns": [], "api_signatures": []}
    monkeypatch.setattr(nodes, "gpt55_client", _ScriptedClient(_json.dumps(llm_contract)))
    out = await nodes.contract_extract({
        "spec_markdown": "s", "confirmed_vue": "v", "table_info": "t",
        "page_type": "list-detail"})
    assert out["contract"]["screen"]["type"] == "list-detail"


async def test_contract_extract_keeps_llm_type_without_page_type(monkeypatch):
    llm_contract = {"screen": {"id": "X", "name": "n", "type": "edit"},
                    "fields": [], "tables": [], "search_conditions": [],
                    "table_columns": [], "api_signatures": []}
    monkeypatch.setattr(nodes, "gpt55_client", _ScriptedClient(_json.dumps(llm_contract)))
    out = await nodes.contract_extract({
        "spec_markdown": "s", "confirmed_vue": "v", "table_info": "t", "page_type": ""})
    assert out["contract"]["screen"]["type"] == "edit"
