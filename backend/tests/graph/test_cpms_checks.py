"""Ported CPMS domain checks (db_seed + frontend local imports). No LLM."""

from app.llm.graph.cpms_checks import (
    check_db_seed_sql, check_frontend_local_imports, extract_markdown_section,
)


def _gf(path, ftype, layer, content):
    return {"file_path": path, "file_type": ftype, "layer": layer,
            "wave": 1, "status": "ok", "status_log": [], "content": content}


def test_extract_markdown_section():
    md = "## 6. foo\nsix\n## 7. seed\nseven body\n## 8. bar\neight"
    sec = extract_markdown_section(md, "## 7.")
    assert "seven body" in sec
    assert "eight" not in sec and "six" not in sec


def test_db_seed_missing_required_tables_flagged():
    sql = "CREATE TABLE x (id int); INSERT INTO cmn_lbl ..."  # only cmn_lbl
    files = {"a": _gf("db/init.sql", "db_init_sql", "backend", sql)}
    issues = check_db_seed_sql(files)
    assert any("missing required seed tables" in i["issue"] for i in issues)


def test_db_seed_clean_passes_table_presence():
    sql = ("insert into cmn_lbl (lang_cd) values ('ko-KR') on conflict do update; "
           "'SCR.SearchForm.title' "
           "insert into cmn_pgm; insert into cmn_menu; "
           "insert into cmn_role_pgm dev_auto root98; insert into cmn_role_menu dev_auto;")
    files = {"a": _gf("db/init.sql", "db_init_sql", "backend", sql)}
    issues = check_db_seed_sql(files)
    # required-tables issue should NOT be present (all 5 tables mentioned)
    assert not any("missing required seed tables" in i["issue"] for i in issues)


def test_db_seed_order_violation_flagged():
    # cmn_menu appears before cmn_lbl → order violation
    sql = ("insert into cmn_pgm; insert into cmn_menu; insert into cmn_lbl 'a.b.c' on conflict ko-kr; "
           "insert into cmn_role_pgm dev_auto root98; insert into cmn_role_menu dev_auto;"
           " searchform.")
    files = {"a": _gf("db/init.sql", "db_init_sql", "backend", sql)}
    issues = check_db_seed_sql(files)
    assert any("order" in i["issue"].lower() for i in issues)


def test_frontend_local_import_missing_flagged():
    files = {
        "p": _gf("src/pages/x/index.vue", "vue_page", "frontend",
                 "import Child from './ChildTable.vue'"),
    }
    issues = check_frontend_local_imports(files)
    assert any("does not resolve" in i["issue"] for i in issues)


def test_frontend_local_import_resolves_ok():
    files = {
        "p": _gf("src/pages/x/index.vue", "vue_page", "frontend",
                 "import Child from './ChildTable.vue'"),
        "c": _gf("src/pages/x/ChildTable.vue", "vue_page", "frontend", "<template/>"),
    }
    issues = check_frontend_local_imports(files)
    assert issues == []


from app.llm.graph.cpms_checks import check_lv2_whitelist


def test_lv2_whitelist_valid_screen_code_ok():
    # CPMSEDURSLTLST → LV2=EDU (whitelisted) → no issue
    assert check_lv2_whitelist("CPMSEDURSLTLST") == []


def test_lv2_whitelist_invalid_lv2_flagged():
    # CPMSXYZRSLT → LV2=XYZ (not in whitelist) → issue
    issues = check_lv2_whitelist("CPMSXYZRSLT")
    assert any("LV2" in i["issue"] for i in issues)


def test_lv2_whitelist_non_cpms_skipped():
    # not a CPMS code → no opinion
    assert check_lv2_whitelist("FOOBAR") == []


def test_lv2_whitelist_empty_skipped():
    assert check_lv2_whitelist("") == []
