"""Restored high-value CPMS static rules (F6). No LLM."""

from app.llm.graph.tools import static_check_impl


def _be(content):
    return static_check_impl("X.java", content, "service_impl", "backend")


def test_hsc_systemerror_single_arg_flagged():
    issues = _be('throw HscException.systemError("조회 실패");')
    assert any("systemError" in i["issue"] for i in issues)


def test_hsc_systemerror_two_arg_ok():
    issues = _be('throw HscException.systemError("조회 실패", e);')
    assert not any("systemError" in i["issue"] for i in issues)


def test_log_before_throw_flagged():
    issues = _be('log.error("fail");\n        throw HscException.systemError("x", e);')
    assert any("log" in i["issue"].lower() for i in issues)


def test_bare_dao_call_flagged():
    issues = _be("eduDao.selectList(req);")
    assert any("DAO" in i["issue"] or "wrapper" in i["issue"].lower() for i in issues)


def test_dto_array_field_flagged():
    issues = static_check_impl("D.java", "private String[] ids;", "dto_request", "backend")
    assert any("array" in i["issue"].lower() or "List" in i["issue"] for i in issues)


def test_mapper_uuid_javatype_flagged():
    issues = static_check_impl("M.xml", 'javaType="java.util.UUID"', "mapper_xml", "backend")
    assert any("UUID" in i["issue"] for i in issues)


def test_clean_service_no_issues():
    issues = _be('try { eduDao.selectEduList(req); } '
                 'catch (Exception e) { throw HscException.systemError("x", e); }')
    assert issues == []
