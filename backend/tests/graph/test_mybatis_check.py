from app.llm.graph.mybatis_check import parse_dao, parse_mapper, match_pairs


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
