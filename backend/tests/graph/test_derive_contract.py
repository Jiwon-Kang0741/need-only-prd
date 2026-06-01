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
    assert {"selectList", "selectCount", "select", "insert", "update", "delete"} <= ids
    one = next(o for o in ops if o["op"] == "selectList")
    assert one["dao_method"] == "selectList"
    assert one["mybatis_tag"] == "select"
    assert one["param_type"] == "CpmsEduRsltLstReqDto"


async def test_derive_contract_builds_dtos():
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": _PLAN})
    dtos = {d["name"]: d for d in out["contract"]["dtos"]}
    assert "CpmsEduRsltLstReqDto" in dtos and "CpmsEduRsltLstResDto" in dtos
    res_fields = {f["name"]: f for f in dtos["CpmsEduRsltLstResDto"]["fields"]}
    assert res_fields["employeeName"]["java_type"] == "String"
    assert res_fields["score"]["java_type"] == "Integer"


async def test_derive_contract_skips_op_without_dao_file():
    plan = {"files": [{"file_path": "x/CpmsEduRsltLstResDto.java", "file_type": "dto_response"}]}
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": plan})
    assert out["contract"]["operations"] == []


async def test_derive_contract_empty_fields_no_crash():
    contract = {"screen": {"id": "X", "type": "list"}, "fields": [], "api_signatures": []}
    out = await nodes.derive_contract({"contract": contract, "plan": _PLAN})
    assert "dtos" in out["contract"]
