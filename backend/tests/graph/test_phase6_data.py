"""Phase-6 integration smoke: contract -> bindings -> DDL+SEED -> assemble -> validate.

Scripted LLM (no real creds). Confirms the data slice composes: gen_ddl/gen_seed
produce SQL, assemble_sql concatenates into db/init.sql, the derived pgm_url has NO
leading slash, and validate_data passes the assembled file.
"""

import pytest

from app.llm.graph import gen_data as gd
from app.llm.graph.contract_schema import parse_contract
from app.llm.graph.plan_and_bind import plan_and_bind
from app.llm.graph.data_validate import validate_data


class _Queue:
    def __init__(self, *replies):
        self.q = list(replies)
    async def complete(self, system, user, max_tokens=16384):
        return self.q.pop(0)


async def test_data_pipeline_assembles_and_validates(monkeypatch):
    ddl = "CREATE TABLE cptb_edu_pondg (pondg_id BIGSERIAL, del_yn CHAR(1) DEFAULT 'N');"
    seed = ("INSERT INTO cmn_pgm (pgm_id, pgm_url) VALUES "
            "('CPMSEDUPONDGLST', 'pages/edu/pondg/cpmsEduPondgLst/index.vue') "
            "ON CONFLICT (pgm_id) DO UPDATE SET pgm_url = EXCLUDED.pgm_url;")
    monkeypatch.setattr(gd, "gpt55_client", _Queue(ddl, seed))

    contract = plan_and_bind({"contract": parse_contract({
        "identity": {"module": "edu", "category": "pondg", "screen_id": "cpmsEduPondgLst",
                     "class_name": "CpmsEduPondgLst", "program_id": "CPMSEDUPONDGLST"},
        "archetype": "list-detail",
        "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
        "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
        "frontend": {"components": ["SearchForm", "DataTable"]},
    }).model_dump()})["contract"]

    ddl_sql = await gd.gen_ddl(contract, guide="G")
    seed_sql = await gd.gen_seed(contract, guide="G")
    assembled = gd.assemble_sql(contract, ddl_sql, seed_sql)

    path = contract["bindings"]["paths"]["db_init_sql"]
    assert path == "db/init.sql"
    sql = assembled[path]
    # DDL precedes SEED, both present
    assert sql.index("CREATE TABLE") < sql.index("INSERT INTO")
    # pgm_url stored as 'pages/...' with NO leading slash
    assert "pages/edu/pondg/cpmsEduPondgLst/index.vue" in sql
    assert "'/pages/" not in sql and '"/pages/' not in sql
    # the assembled file passes data validation
    assert validate_data(sql, contract) == []
