from app.llm.graph.naming import (
    statement_id, dao_method, mybatis_tag, dto_class, java_type, ops_for_screen_type,
    package_from_java_path,
)


_SC = "CpmsEduRsltLst"


def test_statement_id_suffixed():
    assert statement_id("selectList", _SC) == "selectCpmsEduRsltLstList"
    assert statement_id("selectOne", _SC) == "selectCpmsEduRsltLst"
    assert statement_id("count", _SC) == "selectCpmsEduRsltLstCount"
    assert statement_id("insert", _SC) == "insertCpmsEduRsltLst"
    assert statement_id("update", _SC) == "updateCpmsEduRsltLst"
    assert statement_id("delete", _SC) == "deleteCpmsEduRsltLst"


def test_dao_method_equals_statement_id():
    for op in ("selectList", "selectOne", "count", "insert", "update", "delete"):
        assert dao_method(op, _SC) == statement_id(op, _SC)


def test_mybatis_tag():
    assert mybatis_tag("selectList") == "select"
    assert mybatis_tag("count") == "select"
    assert mybatis_tag("insert") == "insert"
    assert mybatis_tag("update") == "update"
    assert mybatis_tag("delete") == "delete"


def test_dto_class():
    assert dto_class("CpmsEduRsltLst", "request") == "CpmsEduRsltLstReqDto"
    assert dto_class("CpmsEduRsltLst", "response") == "CpmsEduRsltLstResDto"


def test_java_type_mapping():
    assert java_type("string") == "String"
    assert java_type("number") == "Integer"
    assert java_type("date") == "String"
    assert java_type("boolean") == "Boolean"
    assert java_type("unknown-xyz") == "String"  # default


def test_ops_for_screen_type():
    assert ops_for_screen_type("list") == ["selectList", "count"]
    ld = ops_for_screen_type("list-detail")
    assert "selectList" in ld and "selectOne" in ld and "insert" in ld and "delete" in ld
    assert ops_for_screen_type("mystery") == ["selectList", "count"]


def test_package_from_java_path_matches_directory():
    p = "src/main/java/hsc/tomms/web/cpms/edursltlst/dao/CpmsEduRsltLstDaoImpl.java"
    assert package_from_java_path(p) == "hsc.tomms.web.cpms.edursltlst.dao"


def test_package_from_java_path_non_java_returns_none():
    assert package_from_java_path("src/main/resources/x/Foo.xml") is None
    assert package_from_java_path("src/pages/a/b/c/index.vue") is None
