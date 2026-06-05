"""Phase-2 integration smoke: a validated Contract flows into deterministic bindings.

No LLM. Confirms contract_schema (validation boundary) and plan_and_bind (bindings)
compose: a pydantic-validated contract — the shape contract_resolve emits — drives
the file plan + cross-file bindings the downstream generators will consume.
"""

from app.llm.graph.contract_schema import parse_contract
from app.llm.graph.plan_and_bind import plan_and_bind


def test_resolved_contract_flows_into_bindings():
    contract = parse_contract({
        "identity": {"module": "edu", "category": "pondg",
                     "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                     "program_id": "CPMSEDUPONDGLST"},
        "archetype": "list-detail",
        "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
        "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
        "frontend": {"components": ["SearchForm", "DataTable"]},
    }).model_dump()

    out = plan_and_bind({"contract": contract})
    b = out["contract"]["bindings"]

    # cross-file binding: mapper namespace == dao package + DaoImpl
    assert b["namespace"] == "biz.edu.dao.CpmsEduPondgLstDaoImpl"
    assert b["paths"]["dao_impl"].endswith("CpmsEduPondgLstDaoImpl.java")
    # statement ids == dao methods (1:1)
    assert b["dao_methods"] == b["statement_ids"]
    assert "selectCpmsEduPondgLstList" in b["statement_ids"]
    # full file plan spans backend + data + frontend
    assert {f["file_type"] for f in out["plan"]["files"]} >= {
        "dto_request", "dto_response", "mapper_xml", "dao_impl",
        "service_impl", "db_init_sql", "vue_page", "vue_types"}
