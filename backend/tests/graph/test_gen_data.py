import pytest
from app.llm.graph import gen_data as gd

pytestmark = pytest.mark.asyncio

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg", "screen_id": "cpmsEduPondgLst",
                 "class_name": "CpmsEduPondgLst", "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm", "db_type": "varchar(100)"}]},
    "seed": {"labels": [{"program_id": "CPMSEDUPONDGLST", "component": "SearchForm",
                         "label_id": "empNm", "text": "사원명"}],
             "menu": {"menu_id": "ROOT0201", "p_menu_id": "ROOT02"},
             "common_codes": [], "pgm_url": ""},
    "bindings": {"paths": {"db_init_sql": "db/init.sql",
                           "vue_page": "src/pages/edu/pondg/cpmsEduPondgLst/index.vue"}},
}


class _Scripted:
    def __init__(self, reply):
        self.reply = reply
        self.last_user = None
        self.calls = 0
    async def complete(self, system, user, max_tokens=16384):
        self.calls += 1
        self.last_user = user
        return self.reply


async def test_gen_ddl_grounds_in_table_and_returns_sql(monkeypatch):
    c = _Scripted("```sql\nCREATE TABLE cptb_edu_pondg (pondg_id BIGSERIAL);\n```")
    monkeypatch.setattr(gd, "gpt55_client", c)
    sql = await gd.gen_ddl(_CONTRACT, guide="GUIDE")
    assert "```" not in sql
    u = c.last_user
    assert "cptb_edu_pondg" in u and "emp_nm" in u and "GUIDE" in u
    assert "del_yn" in u and "BIGSERIAL" in u


async def test_gen_seed_derives_pgm_url_without_leading_slash(monkeypatch):
    c = _Scripted("INSERT INTO cmn_pgm ...;")
    monkeypatch.setattr(gd, "gpt55_client", c)
    await gd.gen_seed(_CONTRACT, guide="GUIDE")
    u = c.last_user
    assert "pages/edu/pondg/cpmsEduPondgLst/index.vue" in u
    assert "/pages/edu/pondg" not in u
    assert "CPMSEDUPONDGLST" in u
    assert "ON CONFLICT" in u


def test_assemble_sql_concats_ddl_then_seed_at_bound_path():
    out = gd.assemble_sql(_CONTRACT, ddl="-- DDL\nCREATE TABLE t();", seed="-- SEED\nINSERT;")
    assert "db/init.sql" in out
    body = out["db/init.sql"]
    assert body.index("-- DDL") < body.index("-- SEED")


def test_pgm_url_from_vue_page_helper():
    assert gd.pgm_url_from_vue_page("src/pages/edu/pondg/x/index.vue") == "pages/edu/pondg/x/index.vue"
    assert gd.pgm_url_from_vue_page("pages/edu/x/index.vue") == "pages/edu/x/index.vue"
    assert not gd.pgm_url_from_vue_page("src/pages/x/index.vue").startswith("/")
