from app.llm.graph.tools import (
    static_check_impl,
    validate_sql_impl,
    cross_check_impl,
    lookup_class_impl,
    get_dto_fields_impl,
    list_generated_files_impl,
)

_DTO = {
    "file_path": "CpmsEduResDto.java", "file_type": "dto_response", "layer": "backend",
    "wave": 1, "status": "ok", "status_log": "",
    "content": "public class CpmsEduResDto { private String eduPgmNm; private Integer cnt; }",
}
_SVC = {
    "file_path": "CpmsEduServiceImpl.java", "file_type": "service_impl", "layer": "backend",
    "wave": 3, "status": "ok", "status_log": "",
    "content": "CpmsEduResDto d; d.getEduPgmNm(); d.getMissingField();",
}


def test_static_check_flags_uuid_import():
    issues = static_check_impl("Foo.java", "import java.util.UUID;\nclass Foo {}", "dto_request", "backend")
    assert any("UUID" in i["issue"] for i in issues)


def test_static_check_flags_scrollheight_flex():
    issues = static_check_impl("Foo.vue", '<DataTable scrollHeight="flex" />', "vue_page", "frontend")
    assert any("scrollHeight" in i["issue"] for i in issues)


def test_static_check_clean_backend_returns_empty():
    issues = static_check_impl("Foo.java", "class Foo { private String id; }", "dto_request", "backend")
    assert issues == []


def test_static_check_only_checks_matching_layer():
    # frontend rule must not fire on backend file
    issues = static_check_impl("Foo.java", 'scrollHeight="flex"', "dto_request", "backend")
    assert issues == []


def test_validate_sql_flags_missing_semicolon_statements():
    issues = validate_sql_impl("CREATE TABLE x (id INT)\nCREATE TABLE y (id INT)")
    assert any("semicolon" in i["issue"].lower() or "세미콜론" in i["issue"] for i in issues)


def test_validate_sql_clean_returns_empty():
    issues = validate_sql_impl("CREATE TABLE x (id INT);")
    assert issues == []


def test_get_dto_fields_returns_fields():
    fields = get_dto_fields_impl("CpmsEduResDto", {"CpmsEduResDto.java": _DTO})
    names = {f["name"] for f in fields}
    assert names == {"eduPgmNm", "cnt"}


def test_lookup_class_returns_none_for_unknown():
    assert lookup_class_impl("NoSuch", {"CpmsEduResDto.java": _DTO}) is None


def test_lookup_class_returns_fields_for_known():
    info = lookup_class_impl("CpmsEduResDto", {"CpmsEduResDto.java": _DTO})
    assert info is not None
    assert "eduPgmNm" in {f["name"] for f in info["fields"]}


def test_cross_check_flags_missing_getter_field():
    files = {"CpmsEduResDto.java": _DTO, "CpmsEduServiceImpl.java": _SVC}
    issues = cross_check_impl(files, contract={})
    assert any("getMissingField" in i["issue"] or "MissingField" in i["issue"] for i in issues)


def test_cross_check_clean_when_all_getters_exist():
    svc_ok = {**_SVC, "content": "CpmsEduResDto d; d.getEduPgmNm();"}
    files = {"CpmsEduResDto.java": _DTO, "CpmsEduServiceImpl.java": svc_ok}
    issues = cross_check_impl(files, contract={})
    assert issues == []


def test_list_generated_files_summary():
    out = list_generated_files_impl({"CpmsEduResDto.java": _DTO})
    assert out == [{"file_path": "CpmsEduResDto.java", "file_type": "dto_response",
                    "layer": "backend", "status": "ok"}]


def test_validate_mybatis_binding_tool_forwards_contract_phase2():
    # review #3: dispatch_tool must pass `contract` to check_binding so the
    # reviewer tool uses Phase-2 (contract truth), same as the mybatis_fix node.
    from app.llm.graph.tools import dispatch_tool
    from app.llm.graph.mybatis_check import check_binding
    dao = ("package com.x.dao;\n"
           "public class FooDaoImpl extends AbstractSqlSessionDaoSupport {\n"
           "  public Object selectFooList(Object p){return super.selectList(\"selectFooList\", p);}\n"
           "}\n")
    mapper = ('<mapper namespace="com.x.dao.FooDaoImpl">\n'
              '  <select id="selectFooList">SELECT 1</select>\n</mapper>\n')
    files = {
        "d": {"file_path": "a/FooDaoImpl.java", "file_type": "dao_impl",
              "layer": "backend", "content": dao},
        "m": {"file_path": "a/FooMapper.xml", "file_type": "mapper_xml",
              "layer": "backend", "content": mapper},
    }
    # contract truth differs from the (self-consistent) DAO/Mapper ids
    contract = {"operations": [{"statement_id": "selectBarList"}]}
    # Phase-1 (no contract) sees DAO==Mapper -> clean
    assert check_binding(files) == []
    # The tool must now report the Phase-2 contract mismatch (contract forwarded)
    result = dispatch_tool("validate_mybatis_binding", {}, files, contract)
    assert result == check_binding(files, contract)
    assert result != []
    assert any("contract" in i["issue"].lower() for i in result)
