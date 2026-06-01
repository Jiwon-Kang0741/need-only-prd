from app.llm.graph.tools import static_check_impl, validate_sql_impl


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
