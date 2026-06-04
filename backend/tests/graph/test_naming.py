from app.llm.graph.naming import (
    statement_id, dao_method, mybatis_tag, dto_class, java_type, ops_for_screen_type,
    screen_segments, file_path, package_from_java_path,
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


# ── deterministic target path derivation (hsc.tomms.web grounding) ──

def test_screen_segments_splits_pascal_case():
    # [LV1][rest] → module = LV1 lower, screen = rest joined lower
    assert screen_segments("CpmsEduRsltLst") == ("cpms", "edursltlst")
    assert screen_segments("CmnUsrLst") == ("cmn", "usrlst")


def test_screen_segments_single_token_falls_back():
    # only one token → screen mirrors module (never empty, avoids dangling pkg)
    assert screen_segments("Foo") == ("foo", "foo")


def test_file_path_backend_uses_biz_module_package():
    # paths come from the guide (CODEGEN_RULES.md codegen-paths) → biz.{module}
    base = "src/main/java/biz/cpms"
    assert file_path("dto_request", _SC) == f"{base}/dto/request/CpmsEduRsltLstReqDto.java"
    assert file_path("dto_response", _SC) == f"{base}/dto/response/CpmsEduRsltLstResDto.java"
    assert file_path("dao", _SC) == f"{base}/dao/CpmsEduRsltLstDao.java"
    assert file_path("dao_impl", _SC) == f"{base}/dao/CpmsEduRsltLstDaoImpl.java"
    assert file_path("service", _SC) == f"{base}/service/CpmsEduRsltLstService.java"
    assert file_path("service_impl", _SC) == f"{base}/service/CpmsEduRsltLstServiceImpl.java"


def test_file_path_mapper_under_biz_mybatis_mappers_resource():
    assert file_path("mapper_xml", _SC) == (
        "src/main/resources/biz/cpms/mybatis/mappers/CpmsEduRsltLstMapper.xml")


def test_file_path_frontend_and_sql():
    assert file_path("vue_page", _SC) == "src/pages/cpms/edursltlst/CpmsEduRsltLst/index.vue"
    assert file_path("vue_types", _SC) == "src/api/pages/cpms/edursltlst/types.ts"
    assert file_path("db_init_sql", _SC) == "db/init.sql"


def test_file_path_unknown_type_returns_none():
    assert file_path("mystery_type", _SC) is None


def test_file_path_uses_biz_not_legacy_roots():
    for ft in ("dto_request", "dao_impl", "service_impl", "mapper_xml"):
        p = file_path(ft, _SC)
        assert "com/example" not in p
        assert "hsc/tomms/web" not in p
        assert "biz/" in p


def test_file_path_is_guide_driven_not_hardcoded(monkeypatch):
    # swapping the guide's template changes the output — proves it isn't hardcoded
    from app.llm.graph import guides
    monkeypatch.setattr(guides, "load_path_templates",
                        lambda: {"dao_impl": "custom/{module}/{Screen}DaoImpl.java"})
    assert file_path("dao_impl", "CpmsEduRsltLst") == "custom/cpms/CpmsEduRsltLstDaoImpl.java"


def test_package_from_java_path_matches_directory():
    p = "src/main/java/hsc/tomms/web/cpms/edursltlst/dao/CpmsEduRsltLstDaoImpl.java"
    assert package_from_java_path(p) == "hsc.tomms.web.cpms.edursltlst.dao"


def test_package_from_java_path_non_java_returns_none():
    assert package_from_java_path("src/main/resources/x/Foo.xml") is None
    assert package_from_java_path("src/pages/a/b/c/index.vue") is None
