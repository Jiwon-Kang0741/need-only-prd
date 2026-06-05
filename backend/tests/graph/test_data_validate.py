from app.llm.graph.data_validate import validate_data

_CONTRACT = {"identity": {"program_id": "CPMSEDUPONDGLST"}}


def test_clean_upsert_sql_no_issues():
    sql = ("INSERT INTO cmn_pgm (pgm_id, pgm_url) VALUES ('p', 'pages/edu/pondg/x/index.vue') "
           "ON CONFLICT (pgm_id) DO UPDATE SET pgm_url = EXCLUDED.pgm_url;")
    assert validate_data(sql, _CONTRACT) == []


def test_flags_missing_terminator():
    sql = "CREATE TABLE cptb_x (id BIGSERIAL)"   # no semicolon
    issues = validate_data(sql, _CONTRACT)
    assert any("semicolon" in i["issue"].lower() or "terminat" in i["issue"].lower()
               for i in issues)


def test_flags_pgm_url_leading_slash():
    sql = "INSERT INTO cmn_pgm (pgm_url) VALUES ('/pages/edu/pondg/x/index.vue');"
    issues = validate_data(sql, _CONTRACT)
    assert any("pgm_url" in i["issue"].lower() and "slash" in i["issue"].lower()
               for i in issues)


def test_flags_merge_statement():
    sql = "MERGE INTO cmn_pgm USING dual ON (1=1) WHEN MATCHED THEN UPDATE SET x = 1;"
    issues = validate_data(sql, _CONTRACT)
    assert any("merge" in i["issue"].lower() for i in issues)


def test_double_quoted_leading_slash_also_flagged():
    sql = 'INSERT INTO cmn_pgm (pgm_url) VALUES ("/pages/x/index.vue");'
    issues = validate_data(sql, _CONTRACT)
    assert any("pgm_url" in i["issue"].lower() for i in issues)


def test_merge_word_in_comment_not_flagged():
    sql = "-- merge the lookup data here\nINSERT INTO cmn_pgm(pgm_url) VALUES('pages/x/index.vue');"
    assert validate_data(sql, _CONTRACT) == []
