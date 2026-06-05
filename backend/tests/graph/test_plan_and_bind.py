from app.llm.graph.plan_and_bind import plan_and_bind

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
    "frontend": {"components": ["SearchForm", "DataTable"]},
}


def _bind():
    return plan_and_bind({"contract": _CONTRACT})


def test_bind_backend_paths_from_guide_templates():
    b = _bind()["contract"]["bindings"]
    assert b["paths"]["dto_request"] == (
        "src/main/java/biz/edu/dto/request/CpmsEduPondgLstReqDto.java")
    assert b["paths"]["mapper_xml"] == (
        "src/main/resources/biz/edu/mybatis/mappers/CpmsEduPondgLstMapper.xml")
    assert b["paths"]["db_init_sql"] == "db/init.sql"


def test_bind_frontend_paths_present():
    b = _bind()["contract"]["bindings"]
    assert b["paths"]["vue_page"] == "src/pages/edu/pondg/cpmsEduPondgLst/index.vue"
    assert b["paths"]["vue_types"] == "src/api/pages/edu/pondg/types.ts"
    assert b["paths"]["vue_searchform"].endswith("/CpmsEduPondgLstSearchForm.vue")


def test_bind_statement_ids_and_dao_methods_match():
    b = _bind()["contract"]["bindings"]
    assert "selectCpmsEduPondgLstList" in b["statement_ids"]
    assert "insertCpmsEduPondgLst" in b["statement_ids"]
    assert b["dao_methods"] == b["statement_ids"]


def test_bind_namespace_and_packages():
    b = _bind()["contract"]["bindings"]
    assert b["namespace"] == "biz.edu.dao.CpmsEduPondgLstDaoImpl"
    assert b["packages"]["dto_request"] == "biz.edu.dto.request"
    assert b["packages"]["service_impl"] == "biz.edu.service"


def test_bind_file_plan_lists_all_artifacts_with_layer():
    plan = _bind()["plan"]
    by_type = {f["file_type"]: f for f in plan["files"]}
    for ft in ("db_init_sql", "dto_request", "dto_response",
               "mapper_xml", "dao_impl", "service_impl"):
        assert ft in by_type, f"missing {ft}"
    assert by_type["dao_impl"]["layer"] == "backend"
    assert by_type["db_init_sql"]["layer"] == "data"
    assert by_type["vue_page"]["layer"] == "frontend"
    assert by_type["vue_types"]["layer"] == "frontend"


def test_bind_ops_fallback_to_archetype_when_contract_ops_empty():
    c = {**_CONTRACT, "ops": []}
    b = plan_and_bind({"contract": c})["contract"]["bindings"]
    assert b["statement_ids"]


def test_bind_files_outputs_are_equal_but_independent():
    r = _bind()
    bf = r["contract"]["bindings"]["files"]
    pf = r["plan"]["files"]
    ef = r["events"][0]["files"]
    assert bf == pf == ef            # same content
    assert pf is not bf and ef is not bf and pf is not ef   # independent objects
    pf.append({"x": 1})              # mutating one must not affect the others
    assert len(bf) != len(pf)


def test_bind_rejects_unknown_op():
    import pytest
    c = {**_CONTRACT, "ops": ["selectList", "frobnicate"]}
    with pytest.raises(ValueError):
        plan_and_bind({"contract": c})


def test_bind_namespace_fallback_when_dao_impl_path_missing(monkeypatch):
    import app.llm.graph.plan_and_bind as m
    orig = m.paths.backend_path
    monkeypatch.setattr(m.paths, "backend_path",
                        lambda ft, ident: None if ft == "dao_impl" else orig(ft, ident))
    b = plan_and_bind({"contract": _CONTRACT})["contract"]["bindings"]
    assert b["namespace"] == "biz.edu.dao.CpmsEduPondgLstDaoImpl"


def test_bind_list_archetype_is_read_only():
    c = {**_CONTRACT, "ops": [], "archetype": "list"}
    b = plan_and_bind({"contract": c})["contract"]["bindings"]
    assert b["statement_ids"] == ["selectCpmsEduPondgLstList", "selectCpmsEduPondgLstCount"]


def test_bind_frontend_sumgrid_path_present():
    c = {**_CONTRACT, "frontend": {"components": ["SearchForm", "DataTable", "SumGrid"]}}
    b = plan_and_bind({"contract": c})["contract"]["bindings"]
    assert "vue_sumgrid" in b["paths"]
    assert any(f["file_type"] == "vue_sumgrid" for f in b["files"])
