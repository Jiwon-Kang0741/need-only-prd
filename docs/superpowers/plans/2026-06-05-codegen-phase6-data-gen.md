# Codegen Rewrite — Phase 6: Data Generators (DDL/SEED) + Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD with scripted fake LLM. Steps use checkbox (`- [ ]`). (Graph rewiring + CODEGEN_RULES deletion = Phase 6b; compile-loops + e2e = Phase 7.)

**Goal:** Build the data generators consuming the Phase-2 Contract+bindings — `gen_ddl` (business `cptb_*` DDL, LLM), `gen_seed` (`cmn_*` upserts, LLM, with deterministic `pgm_url`), and `assemble_sql` (deterministic concat into `db/init.sql`) — plus `data_validate` (DataGuide §12: PostgreSQL terminator, `pgm_url` NO leading slash, MERGE forbidden, seed order). Additive.

**Architecture:** `gen_data.py` LLM generators build a grounded prompt (DataGuide text passed in + contract + bindings) and call `gpt55_client`; `gen_ddl`/`gen_seed` return SQL strings; `assemble_sql` deterministically concatenates DDL → SEED into the bound `db_init_sql` path. `pgm_url` is derived deterministically from `bindings.paths["vue_page"]` (§16.1: strip leading `src/`, no leading slash) and passed into the seed prompt — fixing the live `cpms_checks.py:49` leading-slash bug by construction. `data_validate.py` reuses `tools.validate_sql_impl` (terminator) + adds §12 rules.

**Tech Stack:** Python 3.11+, pytest, `gpt55_client`, reused `tools`/`guide_config`/`_text`/`prompts.GENERATOR_SYSTEM`.

---

## Test harness (reuse)
```bash
export DUMMY_ENV='AZURE_OPENAI_API_KEY=dummy AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com GPT55_AZURE_OPENAI_API_KEY=dummy GPT55_AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com AOAI_API_KEY=dummy AOAI_ENDPOINT=https://dummy.openai.azure.com OPENAI_API_KEY=dummy ANTHROPIC_API_KEY=dummy'
```
Run from `backend`: `source .venv/bin/activate && env $DUMMY_ENV pytest <file> -v`.

## Reusable / context
- `contract["bindings"]["paths"]["db_init_sql"]` == `"db/init.sql"`; `["vue_page"]` == `"src/pages/edu/pondg/cpmsEduPondgLst/index.vue"`.
- `contract["seed"]` = `{labels, menu, common_codes, pgm_url}` (from resolver; pgm_url usually empty → derived here). `contract["identity"]["program_id"]`.
- `contract["table"]` = `{name: "cptb_...", pk, columns:[{snake,camel,db_type,...}]}`.
- `guide_config.load_seed_order()` → `["cmn_class","cmn_code","cmn_lbl","cmn_pgm","cmn_menu","cmn_role_pgm","cmn_role_menu"]`; `guide_config.load_seed_natural_keys()` → dict.
- `tools.validate_sql_impl(sql)` → flags SQL with statements but no `;` terminator.
- §16.1 pgm_url: `src/pages/{m}/{c}/{s}/index.vue` → `pages/{m}/{c}/{s}/index.vue` (strip leading `src/`; NO leading slash).

---

## Task 1: DDL + SEED generators + assemble (`gen_data.py`)

**Files:** Create `backend/app/llm/graph/gen_data.py`, `backend/tests/graph/test_gen_data.py`.

- [ ] **Step 1: failing tests** — `test_gen_data.py`:
```python
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
    # DDL rules called out (PostgreSQL, del_yn, audit, no *_nm)
    assert "del_yn" in u and "BIGSERIAL" in u


async def test_gen_seed_derives_pgm_url_without_leading_slash(monkeypatch):
    c = _Scripted("INSERT INTO cmn_pgm ...;")
    monkeypatch.setattr(gd, "gpt55_client", c)
    await gd.gen_seed(_CONTRACT, guide="GUIDE")
    u = c.last_user
    # pgm_url derived from vue_page: strip 'src/' -> 'pages/...', NO leading slash
    assert "pages/edu/pondg/cpmsEduPondgLst/index.vue" in u
    assert "/pages/edu/pondg" not in u            # leading-slash form must NOT appear
    assert "CPMSEDUPONDGLST" in u                  # program_id grounding
    assert "ON CONFLICT" in u                      # upsert hint


def test_assemble_sql_concats_ddl_then_seed_at_bound_path():
    out = gd.assemble_sql(_CONTRACT, ddl="-- DDL\nCREATE TABLE t();", seed="-- SEED\nINSERT;")
    assert "db/init.sql" in out
    body = out["db/init.sql"]
    assert body.index("-- DDL") < body.index("-- SEED")    # DDL precedes SEED


def test_pgm_url_from_vue_page_helper():
    assert gd.pgm_url_from_vue_page("src/pages/edu/pondg/x/index.vue") == "pages/edu/pondg/x/index.vue"
    assert gd.pgm_url_from_vue_page("pages/edu/x/index.vue") == "pages/edu/x/index.vue"  # idempotent
    assert not gd.pgm_url_from_vue_page("src/pages/x/index.vue").startswith("/")
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: implement `gen_data.py`** with module-level `gpt55_client`, `GENERATOR_SYSTEM`, `_strip_fences`, `json`:
  - `def pgm_url_from_vue_page(vue_page: str) -> str`: `p = vue_page.replace("\\", "/"); p = p[4:] if p.startswith("src/") else p; return p.lstrip("/")` — but must NOT strip a leading slash that's part of nothing; simplest: after removing `src/`, if it starts with `/` remove it. Ensure result starts with `pages/`. (Idempotent for already-`pages/...` input.)
  - `async def gen_ddl(contract, guide) -> str`: prompt includes guide + table name + columns (snake names) + DDL rule reminders containing the literal tokens `BIGSERIAL`, `del_yn`, `timestamptz`, audit columns, "do not store *_nm". Call gpt55, return `_strip_fences(reply)`.
  - `async def gen_seed(contract, guide) -> str`: compute `pgm_url = pgm_url_from_vue_page(contract["bindings"]["paths"]["vue_page"])`; prompt includes guide + program_id + the derived `pgm_url` (the no-leading-slash form) + seed labels/menu/common_codes JSON + rule hints containing `ON CONFLICT` (upsert) and "MERGE 금지" and the seed table order. Call gpt55, return `_strip_fences(reply)`.
  - `def assemble_sql(contract, ddl, seed) -> dict`: path = `contract["bindings"]["paths"].get("db_init_sql", "db/init.sql")`; return `{path: ddl.rstrip() + "\n\n" + seed.lstrip()}`.
- [ ] **Step 4: PASS (5).** **Step 5: commit** (`feat(codegen): data DDL/SEED generators + assemble (pgm_url no leading slash)`).

---

## Task 2: Data validation (`data_validate.py`)

**Files:** Create `backend/app/llm/graph/data_validate.py`, `backend/tests/graph/test_data_validate.py`.

- [ ] **Step 1: failing tests** — assert: (a) SQL with statements but no `;` flagged (reuse tools.validate_sql_impl); (b) a `pgm_url` value starting with `/pages/` is flagged (§16.1 violation — THE bug the old check had backwards); (c) `MERGE ` statement flagged; (d) a clean upsert SQL with `pages/...` (no leading slash) returns no issues. Concrete inline SQL fixtures.
- [ ] **Step 2: FAIL.**
- [ ] **Step 3: implement** `validate_data(sql: str, contract: dict) -> list[dict]`:
  - `issues = list(tools.validate_sql_impl(sql))`.
  - leading-slash pgm_url: if `re.search(r"'/pages/", sql)` OR `re.search(r'"/pages/', sql)` → issue "pgm_url must not have a leading slash (§16.1: 'pages/...')".
  - MERGE: if `re.search(r"\bMERGE\b", sql, re.I)` → issue "MERGE forbidden — use INSERT ... ON CONFLICT (§1.2)".
  - return issues.
- [ ] **Step 4: PASS.** **Step 5: commit** (`feat(codegen): data SQL validation (§12: terminator, pgm_url slash, MERGE)`).

---

## Task 3: Regression + integration smoke

- [ ] **Step 1:** `env $DUMMY_ENV pytest -m "not llm" -q` → green.
- [ ] **Step 2:** Additive check: `git diff --name-only <phase6-base>..HEAD -- backend/app/llm/graph` shows only `gen_data.py` + `data_validate.py` new.
- [ ] **Step 3:** Smoke `test_phase6_data.py` (scripted LLM): contract → `plan_and_bind` → `gen_ddl`/`gen_seed` (scripted: ddl returns a CREATE with `;`, seed returns `INSERT ... ON CONFLICT ...; -- pgm_url pages/edu/...`) → `assemble_sql` → `validate_data(assembled["db/init.sql"], contract)` returns `[]`; AND assert the assembled SQL contains the no-leading-slash `pages/` form (seed prompt grounded it). Commit.

---

## Self-Review
- Spec coverage: spec §5.3 data (DDL early / SEED with real pgm_url / deterministic assemble) → Task 1; §8 #2 pgm_url no-leading-slash fix → `pgm_url_from_vue_page` + Task 2; DataGuide §12 validation → Task 2. SEED's dependency on the FRONTEND vue path is satisfied via `bindings.paths["vue_page"]` (deterministic, available pre-generation) — so seed can run without waiting on the actual generated index.vue content; the component-name dependency (cmn_lbl `{component}`) comes from `contract["frontend"]["components"]` + `contract["seed"]["labels"]`. Ordering into the live wave graph = Phase 6b.
- Placeholders: none. pgm_url derivation fully coded + tested (incl. idempotency + no-leading-slash).
- Type consistency: paths from `bindings.paths`; generators `(contract, guide)` return str; `assemble_sql` returns `{path: sql}`; `gpt55_client` module-level monkeypatchable.
