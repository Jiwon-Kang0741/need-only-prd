from app.llm.graph.backend_validate import validate_backend

_CONTRACT = {
    "identity": {"class_name": "CpmsEduPondgLst"},
    "bindings": {
        "statement_ids": ["selectCpmsEduPondgLstList", "insertCpmsEduPondgLst"],
        "dao_methods": ["selectCpmsEduPondgLstList", "insertCpmsEduPondgLst"],
        "namespace": "biz.edu.dao.CpmsEduPondgLstDaoImpl",
    },
}

_DAO_OK = """package biz.edu.dao;
public class CpmsEduPondgLstDaoImpl extends AbstractSqlSessionDaoSupport {
    public java.util.List<X> selectCpmsEduPondgLstList(R param) { return super.selectList("selectCpmsEduPondgLstList", param); }
    public int insertCpmsEduPondgLst(java.util.List<R> param) { return super.batchUpdateReturnSumAffectedRows("insertCpmsEduPondgLst", param); }
}
"""

_MAPPER_OK = """<?xml version="1.0"?>
<mapper namespace="biz.edu.dao.CpmsEduPondgLstDaoImpl">
  <select id="selectCpmsEduPondgLstList">SELECT 1</select>
  <insert id="insertCpmsEduPondgLst">INSERT</insert>
</mapper>
"""


def _files(dao=_DAO_OK, mapper=_MAPPER_OK, extra=None):
    f = {
        "d/CpmsEduPondgLstDaoImpl.java": {"file_path": "d/CpmsEduPondgLstDaoImpl.java",
            "file_type": "dao_impl", "layer": "backend", "content": dao},
        "m/CpmsEduPondgLstMapper.xml": {"file_path": "m/CpmsEduPondgLstMapper.xml",
            "file_type": "mapper_xml", "layer": "backend", "content": mapper},
    }
    if extra:
        f.update(extra)
    return f


def test_clean_set_no_issues():
    assert validate_backend(_files(), _CONTRACT) == []


def test_flags_uuid_import_via_static_check():
    bad = {"x/CpmsEduPondgLstReqDto.java": {"file_path": "x/CpmsEduPondgLstReqDto.java",
        "file_type": "dto_request", "layer": "backend",
        "content": "package x;\nimport java.util.UUID;\nclass R{}"}}
    issues = validate_backend(_files(extra=bad), _CONTRACT)
    assert any("UUID" in i["issue"] for i in issues)


def test_flags_mapper_namespace_mismatch():
    bad_mapper = _MAPPER_OK.replace("biz.edu.dao.CpmsEduPondgLstDaoImpl", "biz.wrong.dao.X")
    issues = validate_backend(_files(mapper=bad_mapper), _CONTRACT)
    assert any("namespace" in i["issue"].lower() for i in issues)


def test_flags_missing_statement_in_mapper():
    bad_mapper = _MAPPER_OK.replace('<insert id="insertCpmsEduPondgLst">INSERT</insert>', "")
    issues = validate_backend(_files(mapper=bad_mapper), _CONTRACT)
    assert any("insertCpmsEduPondgLst" in i["issue"] and "mapper" in i["issue"].lower()
               for i in issues)


def test_flags_missing_method_in_dao():
    bad_dao = _DAO_OK.replace("insertCpmsEduPondgLst", "somethingElse")
    issues = validate_backend(_files(dao=bad_dao), _CONTRACT)
    assert any("insertCpmsEduPondgLst" in i["issue"] and "dao" in i["issue"].lower()
               for i in issues)
