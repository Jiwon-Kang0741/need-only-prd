"""Phase-4 integration smoke: contract -> bindings -> deterministic DAO -> validation.

No LLM. Confirms the deterministic backend slice composes: a validated contract
flows through plan_and_bind, render_dao produces a DaoImpl whose methods match the
bindings statement-ids, and backend_validate finds no issues on that DAO.
"""

from app.llm.graph.contract_schema import parse_contract
from app.llm.graph.plan_and_bind import plan_and_bind
from app.llm.graph.gen_backend import render_dao
from app.llm.graph.backend_validate import validate_backend


def _contract():
    c = parse_contract({
        "identity": {"module": "edu", "category": "pondg",
                     "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                     "program_id": "CPMSEDUPONDGLST"},
        "archetype": "list-detail",
        "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
        "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
        "frontend": {"components": ["SearchForm", "DataTable"]},
    }).model_dump()
    return plan_and_bind({"contract": c})["contract"]


def test_rendered_dao_matches_bindings_and_passes_validation():
    contract = _contract()
    b = contract["bindings"]
    dao_src = render_dao(contract)

    # package + namespace consistency
    assert f"package {b['packages']['dao_impl']};" in dao_src
    # every bindings statement-id is a generated DAO method
    for sid in b["statement_ids"]:
        assert f"{sid}(" in dao_src

    # backend_validate finds no issue on the deterministic DAO (mapper omitted -> its
    # cross-file checks are skipped; the per-file static_check + dao-method check pass)
    dao_path = b["paths"]["dao_impl"]
    files = {dao_path: {"file_path": dao_path, "file_type": "dao_impl",
                        "layer": "backend", "content": dao_src}}
    assert validate_backend(files, contract) == []
