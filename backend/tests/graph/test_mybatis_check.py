from app.llm.graph.mybatis_check import (
    parse_dao, parse_mapper, match_pairs, check_binding, autofix_binding,
)


def _gf(path, ftype, content):
    return {"file_path": path, "file_type": ftype, "layer": "backend",
            "wave": 2, "status": "ok", "status_log": [], "content": content}

_DAO = """package com.example.cpms.dao;
import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;
public class CpmsEduRsltLstDaoImpl extends AbstractSqlSessionDaoSupport {
    public java.util.List<X> selectCpmsEduRsltList(X p) {
        return super.selectList("selectCpmsEduRsltList", p);
    }
    public int selectCpmsEduRsltCount(X p) {
        Integer c = super.selectOne("selectCpmsEduRsltCount", p);
        return c == null ? 0 : c;
    }
    public int insertCpmsEduRslt(X p) { return super.insert("insertCpmsEduRslt", p); }
}
"""

_MAPPER = """<?xml version="1.0" encoding="UTF-8" ?>
<mapper namespace="com.example.cpms.mapper.CpmsEduRsltLstMapper">
    <select id="selectCpmsEduRsltLstList" resultType="X">SELECT 1</select>
    <select id="selectCpmsEduRsltCount" resultType="int">SELECT 2</select>
    <insert id="insertCpmsEduRslt">INSERT 3</insert>
</mapper>
"""


def test_parse_dao_extracts_statement_ids_and_namespace():
    info = parse_dao(_DAO)
    assert info["statement_ids"] == {
        "selectCpmsEduRsltList", "selectCpmsEduRsltCount", "insertCpmsEduRslt"}
    assert info["expected_namespace"] == "com.example.cpms.dao.CpmsEduRsltLstDaoImpl"


def test_parse_mapper_extracts_ids_and_namespace():
    info = parse_mapper(_MAPPER)
    assert info["namespace"] == "com.example.cpms.mapper.CpmsEduRsltLstMapper"
    assert info["ids"] == {
        "selectCpmsEduRsltLstList", "selectCpmsEduRsltCount", "insertCpmsEduRslt"}


def test_match_pairs_by_name_rule():
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", _DAO),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    pairs, unpaired = match_pairs(files)
    assert len(pairs) == 1
    dao_gf, mapper_gf = pairs[0]
    assert dao_gf["file_path"].endswith("DaoImpl.java")
    assert mapper_gf["file_path"].endswith("Mapper.xml")
    assert unpaired == []


def test_match_pairs_reports_unpaired_dao():
    files = {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", _DAO),
    }
    pairs, unpaired = match_pairs(files)
    assert pairs == []
    assert any("FooDaoImpl" in u["issue"] for u in unpaired)


def test_check_binding_flags_namespace_and_missing_id():
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", _DAO),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    issues = check_binding(files)
    kinds = " ".join(i["issue"] for i in issues)
    assert "namespace" in kinds.lower()
    assert "selectCpmsEduRsltList" in kinds
    assert any(i.get("severity") == "warning" for i in issues)


def test_check_binding_clean_when_aligned():
    dao = _DAO.replace('"selectCpmsEduRsltList"', '"selectCpmsEduRsltLstList"')
    mapper = _MAPPER.replace(
        'namespace="com.example.cpms.mapper.CpmsEduRsltLstMapper"',
        'namespace="com.example.cpms.dao.CpmsEduRsltLstDaoImpl"')
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", dao),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", mapper),
    }
    errors = [i for i in check_binding(files) if i.get("severity") != "warning"]
    assert errors == []


def test_autofix_fixes_namespace_and_close_id():
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", _DAO),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    fixed, logs = autofix_binding(files)
    mapper_content = fixed["b/CpmsEduRsltLstMapper.xml"]["content"]
    assert 'namespace="com.example.cpms.dao.CpmsEduRsltLstDaoImpl"' in mapper_content
    assert 'id="selectCpmsEduRsltList"' in mapper_content
    assert 'id="selectCpmsEduRsltLstList"' not in mapper_content
    errors = [i for i in check_binding(fixed) if i.get("severity") != "warning"]
    assert errors == []
    assert len(logs) >= 2


def test_autofix_skips_ambiguous_id():
    # DAO needs ids far from any mapper id → no rename, left for reviewer
    dao = _DAO.replace('"selectCpmsEduRsltList"', '"selectTotallyDifferentThing"')
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", dao),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    fixed, logs = autofix_binding(files)
    remaining = check_binding(fixed)
    assert any("selectTotallyDifferentThing" in i["issue"] for i in remaining)


# Real defect captured from outputs/code (DAO call vs Mapper id, wrong namespace).
_REAL_DAO = """package com.example.cpms.dao;
import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;
public class CpmsEduRsltLstDaoImpl extends AbstractSqlSessionDaoSupport {
    public java.util.List<X> selectCpmsEduRsltList(X p) {
        return super.selectList("selectCpmsEduRsltList", p);
    }
    public int selectCpmsEduRsltCount(X p) {
        Integer c = super.selectOne("selectCpmsEduRsltCount", p);
        return c == null ? 0 : c;
    }
}
"""

_REAL_MAPPER = """<?xml version="1.0" encoding="UTF-8" ?>
<mapper namespace="com.example.cpms.mapper.CpmsEduRsltLstMapper">
    <select id="selectCpmsEduRsltLstList" resultType="X">SELECT 1</select>
    <select id="selectCpmsEduRsltLstCount" resultType="int">SELECT 2</select>
</mapper>
"""


def test_regression_outputs_code_defect_is_fixed():
    files = {
        "x/CpmsEduRsltLstDaoImpl.java": _gf("x/CpmsEduRsltLstDaoImpl.java", "dao_impl", _REAL_DAO),
        "y/CpmsEduRsltLstMapper.xml": _gf("y/CpmsEduRsltLstMapper.xml", "mapper_xml", _REAL_MAPPER),
    }
    before = [i for i in check_binding(files) if i.get("severity") != "warning"]
    assert len(before) >= 2  # namespace + at least one missing id

    fixed, logs = autofix_binding(files)
    after = [i for i in check_binding(fixed) if i.get("severity") != "warning"]
    assert after == [], f"unresolved after autofix: {after}"
    mc = fixed["y/CpmsEduRsltLstMapper.xml"]["content"]
    assert 'namespace="com.example.cpms.dao.CpmsEduRsltLstDaoImpl"' in mc
    assert 'id="selectCpmsEduRsltList"' in mc
    assert 'id="selectCpmsEduRsltCount"' in mc
