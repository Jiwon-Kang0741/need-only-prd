from app.llm.graph.nodes import _contract_section_for

_CONTRACT = {
    "operations": [
        {"op": "selectList", "statement_id": "selectList", "dao_method": "selectList",
         "param_type": "FooReqDto", "return_type": "List<FooResDto>", "mybatis_tag": "select"},
        {"op": "insert", "statement_id": "insert", "dao_method": "insert",
         "param_type": "FooReqDto", "return_type": "int", "mybatis_tag": "insert"},
    ],
    "dtos": [
        {"name": "FooReqDto", "kind": "request",
         "fields": [{"name": "employeeName", "java_type": "String"}]},
        {"name": "FooResDto", "kind": "response",
         "fields": [{"name": "score", "java_type": "Integer"}]},
    ],
}


def test_section_for_dao_lists_operations():
    s = _contract_section_for("dao_impl", _CONTRACT)
    assert "selectList" in s and "insert" in s
    assert "FooReqDto" in s


def test_section_for_mapper_lists_statement_ids_and_tags():
    s = _contract_section_for("mapper_xml", _CONTRACT)
    assert "selectList" in s and "select" in s


def test_section_for_dto_request_lists_only_that_dto_fields():
    s = _contract_section_for("dto_request", _CONTRACT)
    assert "employeeName" in s and "String" in s
    assert "score" not in s


def test_section_for_unrelated_filetype_empty():
    assert _contract_section_for("db_init_sql", _CONTRACT) == ""
    assert _contract_section_for("vue_page", _CONTRACT) == ""


def test_section_for_no_operations_empty():
    assert _contract_section_for("dao_impl", {}) == ""
