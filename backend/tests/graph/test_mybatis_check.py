from app.llm.graph.mybatis_check import parse_dao, parse_mapper

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
