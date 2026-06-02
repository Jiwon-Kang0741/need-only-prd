from app.llm.graph.build import mybatis_fix

_DAO = """package com.example.cpms.dao;
public class FooDaoImpl extends Base {
    public int selectFooList(X p) { return super.selectList("selectFooList", p); }
}
"""
_MAPPER_BAD = """<mapper namespace="com.example.cpms.mapper.FooMapper">
    <select id="selectFooLst">SELECT 1</select>
</mapper>
"""


def _gf(path, ftype, content):
    return {"file_path": path, "file_type": ftype, "layer": "backend",
            "wave": 2, "status": "ok", "status_log": [], "content": content}


def test_mybatis_fix_node_corrects_and_reports():
    state = {"files": {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", _DAO),
        "b/FooMapper.xml": _gf("b/FooMapper.xml", "mapper_xml", _MAPPER_BAD),
    }}
    out = mybatis_fix(state)
    mc = out["files"]["b/FooMapper.xml"]["content"]
    assert 'namespace="com.example.cpms.dao.FooDaoImpl"' in mc
    assert 'id="selectFooList"' in mc
    assert any("MYBATIS-FIX" in e.get("line", "") for e in out["events"])


def test_mybatis_fix_node_clean_input_noop():
    dao = """package p; public class FooDaoImpl extends B {
        public int x(X p){ return super.selectList("selectFoo", p); } }"""
    mapper = '<mapper namespace="p.FooDaoImpl"><select id="selectFoo">S</select></mapper>'
    state = {"files": {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", dao),
        "b/FooMapper.xml": _gf("b/FooMapper.xml", "mapper_xml", mapper),
    }}
    out = mybatis_fix(state)
    errs = [i for i in out.get("open_issues", []) if i.get("severity") != "warning"]
    assert errs == []


def test_mybatis_fix_uses_contract_when_present():
    dao = """package p; public class FooDaoImpl extends B {
        public int a(X q){ return super.selectList("selectListX", q); } }"""
    mapper = '<mapper namespace="p.FooDaoImpl"><select id="selectLst">S</select></mapper>'
    contract = {"operations": [
        {"op": "selectList", "statement_id": "selectList", "dao_method": "selectList",
         "mybatis_tag": "select"}]}
    state = {"files": {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", dao),
        "b/FooMapper.xml": _gf("b/FooMapper.xml", "mapper_xml", mapper),
    }, "contract": contract}
    out = mybatis_fix(state)
    dao_c = out["files"]["a/FooDaoImpl.java"]["content"]
    mapper_c = out["files"]["b/FooMapper.xml"]["content"]
    assert '"selectList"' in dao_c
    assert 'id="selectList"' in mapper_c


def test_mybatis_fix_includes_cpms_checks():
    # db_init_sql missing seed tables → cpms db_seed check surfaces in open_issues
    sql = "CREATE TABLE foo (id int);"  # no cmn_* seed tables
    state = {"files": {
        "d/init.sql": _gf("db/init.sql", "db_init_sql", sql),
    }}
    out = mybatis_fix(state)
    assert any("seed tables" in i["issue"] for i in out.get("open_issues", []))
