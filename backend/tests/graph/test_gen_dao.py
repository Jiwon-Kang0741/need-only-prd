from app.llm.graph.gen_backend import render_dao

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
    "bindings": {
        "statement_ids": ["selectCpmsEduPondgLstList", "selectCpmsEduPondgLstCount",
                          "selectCpmsEduPondgLst", "insertCpmsEduPondgLst",
                          "updateCpmsEduPondgLst", "deleteCpmsEduPondgLst"],
        "packages": {"dao_impl": "biz.edu.dao",
                     "dto_request": "biz.edu.dto.request",
                     "dto_response": "biz.edu.dto.response"},
        "paths": {"dao_impl": "src/main/java/biz/edu/dao/CpmsEduPondgLstDaoImpl.java"},
    },
}


def test_render_dao_header_and_class():
    src = render_dao(_CONTRACT)
    assert "package biz.edu.dao;" in src
    assert "import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;" in src
    assert "import biz.edu.dto.request.CpmsEduPondgLstReqDto;" in src
    assert "import biz.edu.dto.response.CpmsEduPondgLstResDto;" in src
    assert "@Repository" in src
    assert "public class CpmsEduPondgLstDaoImpl extends AbstractSqlSessionDaoSupport {" in src


def test_render_dao_methods_per_op():
    src = render_dao(_CONTRACT)
    assert ("public java.util.List<CpmsEduPondgLstResDto> selectCpmsEduPondgLstList("
            "CpmsEduPondgLstReqDto param)") in src
    assert 'return super.selectList("selectCpmsEduPondgLstList", param);' in src
    assert "public int selectCpmsEduPondgLstCount(CpmsEduPondgLstReqDto param)" in src
    assert 'return super.selectOne("selectCpmsEduPondgLstCount", param);' in src
    assert "public CpmsEduPondgLstResDto selectCpmsEduPondgLst(CpmsEduPondgLstReqDto param)" in src
    assert 'return super.insert("insertCpmsEduPondgLst", param);' in src
    assert ("public int updateCpmsEduPondgLst("
            "java.util.List<CpmsEduPondgLstReqDto> param)") in src
    assert 'return super.batchUpdateReturnSumAffectedRows("updateCpmsEduPondgLst", param);' in src
    assert 'return super.batchUpdateReturnSumAffectedRows("deleteCpmsEduPondgLst", param);' in src


def test_render_dao_no_bare_crud_calls():
    src = render_dao(_CONTRACT)
    import re
    methods = re.findall(r"public [^\n]+ (\w+)\(", src)
    assert set(methods) == set(_CONTRACT["bindings"]["statement_ids"])
