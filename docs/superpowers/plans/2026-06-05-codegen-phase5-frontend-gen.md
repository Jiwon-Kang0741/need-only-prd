# Codegen Rewrite — Phase 5: Frontend Generators + Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD with scripted fake LLM (no real creds). Steps use checkbox (`- [ ]`).

**Goal:** Build the frontend generators consuming the Phase-2 Contract+bindings — `types.ts`, the API file, child components (DataTable/SearchForm/SumGrid, multi-file), and `index.vue` (generated LAST, bound to the real children) — plus a guide-driven frontend static validation. Additive (not wired; wiring + the vite compile-loop are Phase 6).

**Architecture:** `gen_frontend.py` holds async LLM generators that build a grounded prompt (FrontendGuide text passed in + contract + `bindings.paths`/components + dependency file contents) and call `gpt55_client`. Each returns `{bound_path: content}` from `contract["bindings"]["paths"]`. `frontend_validate.py` reuses `tools.static_check_impl` (frontend rules: scrollHeight flex, `<script>` without setup, alert/confirm) + cross-file checks (DataTable2 `:columns` prop usage, types-import path, child props referenced by index.vue).

**Tech Stack:** Python 3.11+, pytest, `gpt55_client`, reused `guides`/`tools`/`_text`/`prompts.GENERATOR_SYSTEM`.

---

## Test harness (reuse)
```bash
export DUMMY_ENV='AZURE_OPENAI_API_KEY=dummy AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com GPT55_AZURE_OPENAI_API_KEY=dummy GPT55_AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com AOAI_API_KEY=dummy AOAI_ENDPOINT=https://dummy.openai.azure.com OPENAI_API_KEY=dummy ANTHROPIC_API_KEY=dummy'
```
Run from `backend`: `source .venv/bin/activate && env $DUMMY_ENV pytest <file> -v`.

## Frontend bindings paths (from Phase-2 `paths.frontend_paths`)
Keys present in `contract["bindings"]["paths"]`: `vue_page` (index.vue), `vue_page_scss`, `vue_api` ([screenId].ts), `vue_types` (types.ts), and per component `vue_searchform`(+`_scss`), `vue_datatable`(+`_scss`), `vue_datatable_utils`, `vue_sumgrid`(+`_scss`). `contract["frontend"]["components"]` lists which components exist. `contract["frontend"]["columns"]`, `["search_fields"]`, `["common_code_load"]` carry FE plan detail. `contract["api"]` carries `{method, service_id, url, req_dto, res_dto}`.

## Shared fixture (used by all test files in this phase)
```python
_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST", "window_id": "cpmsEduPondgLst"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
    "fields": {"request": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String", "filter": "ILIKE"}],
               "response": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String"}]},
    "api": [{"method": "selectList", "service_id": "CpmsEduPondgLst/selectList",
             "url": "/online/mvcJson/CpmsEduPondgLst-selectList",
             "req_dto": "CpmsEduPondgLstReqDto", "res_dto": "CpmsEduPondgLstResDto"}],
    "frontend": {"components": ["SearchForm", "DataTable"],
                 "search_fields": ["empNm"],
                 "columns": [{"field": "empNm", "header": "사원명", "width": "140px"}],
                 "common_code_load": "ensureLoaded"},
    "bindings": {
        "paths": {
            "vue_page": "src/pages/edu/pondg/cpmsEduPondgLst/index.vue",
            "vue_page_scss": "src/pages/edu/pondg/cpmsEduPondgLst/cpmsEduPondgLst.scss",
            "vue_api": "src/api/pages/edu/pondg/cpmsEduPondgLst.ts",
            "vue_types": "src/api/pages/edu/pondg/types.ts",
            "vue_searchform": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstSearchForm/CpmsEduPondgLstSearchForm.vue",
            "vue_searchform_scss": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstSearchForm/CpmsEduPondgLstSearchForm.scss",
            "vue_datatable": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstDataTable/CpmsEduPondgLstDataTable.vue",
            "vue_datatable_scss": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstDataTable/CpmsEduPondgLstDataTable.scss",
            "vue_datatable_utils": "src/pages/edu/pondg/cpmsEduPondgLst/components/cpmsEduPondgLstDataTable/utils/index.ts",
        },
    },
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
```

---

## Task 1: types.ts + API generators (`gen_frontend.py`)

**Files:** Create `backend/app/llm/graph/gen_frontend.py`, `backend/tests/graph/test_gen_frontend_io.py`.

- [ ] **Step 1: failing tests** — `test_gen_frontend_io.py` (paste the shared fixture + `_Scripted` above, then):
```python
import pytest
from app.llm.graph import gen_frontend as gf
pytestmark = pytest.mark.asyncio

async def test_gen_types_returns_types_file(monkeypatch):
    c = _Scripted("```ts\nexport interface X {}\n```")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_types(_CONTRACT, guide="GUIDE")
    assert _CONTRACT["bindings"]["paths"]["vue_types"] in out
    assert all("```" not in v for v in out.values())
    u = c.last_user
    assert "empNm" in u and "GUIDE" in u           # fields + guide grounded

async def test_gen_api_grounds_in_serviceid_and_types(monkeypatch):
    c = _Scripted("export const api = {}")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_api(_CONTRACT, guide="GUIDE", types="export interface R {}")
    assert _CONTRACT["bindings"]["paths"]["vue_api"] in out
    u = c.last_user
    assert "/online/mvcJson/CpmsEduPondgLst-selectList" in u   # URL from api sig
    assert "api.post" in u                                      # POST-only rule hint
    assert "interface R" in u                                   # dep types injected
```
- [ ] **Step 2: FAIL.**
- [ ] **Step 3: implement** `gen_frontend.py` with module-level `from app.llm.graph.llm import gpt55_client`, `from app.llm.graph.prompts import GENERATOR_SYSTEM`, `from app.llm.graph._text import strip_fences as _strip_fences`, `import json`.
  - `async def gen_types(contract, guide) -> dict`: prompt includes guide + `contract["fields"]` (so `empNm` appears) + `contract["api"]` (DTO names) + target path; instruct: define `SearchParams` + `*ResDto` interfaces in `api/pages/{module}/{category}/types.ts`. Return `{vue_types_path: stripped}`.
  - `async def gen_api(contract, guide, types) -> dict`: prompt includes guide + each `api[].url` (so the literal `/online/mvcJson/CpmsEduPondgLst-selectList` appears) + the dep `types` source + an explicit `api.post` (GET 금지) hint. Return `{vue_api_path: stripped}`.
- [ ] **Step 4: PASS (2).** **Step 5: commit** (`feat(codegen): frontend types + API generators`).

---

## Task 2: component generators + index.vue (`gen_frontend.py`)

**Files:** extend `gen_frontend.py`; create `backend/tests/graph/test_gen_frontend_components.py`.

- [ ] **Step 1: failing tests** (paste shared fixture + `_Scripted`, then):
```python
import pytest
from app.llm.graph import gen_frontend as gf
pytestmark = pytest.mark.asyncio

async def test_gen_component_datatable_returns_vue_scss_utils(monkeypatch):
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_component(_CONTRACT, guide="GUIDE", comp="DataTable", types="export interface R{}")
    p = _CONTRACT["bindings"]["paths"]
    assert p["vue_datatable"] in out and p["vue_datatable_scss"] in out and p["vue_datatable_utils"] in out
    u = c.last_user
    assert "GUIDE" in u and "DataTable2" in u and ":columns" in u   # wrapper + columns prop hints

async def test_gen_component_searchform_no_utils(monkeypatch):
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    out = await gf.gen_component(_CONTRACT, guide="GUIDE", comp="SearchForm", types="x")
    p = _CONTRACT["bindings"]["paths"]
    assert p["vue_searchform"] in out and p["vue_searchform_scss"] in out
    assert p["vue_datatable_utils"] not in out          # only DataTable has utils

async def test_gen_index_generated_last_binds_children(monkeypatch):
    c = _Scripted("<template/>")
    monkeypatch.setattr(gf, "gpt55_client", c)
    children = {"CpmsEduPondgLstSearchForm": "<template>SF</template>",
                "CpmsEduPondgLstDataTable": "<template>DT</template>"}
    out = await gf.gen_index(_CONTRACT, guide="GUIDE", components=children, types="x")
    p = _CONTRACT["bindings"]["paths"]
    assert p["vue_page"] in out and p["vue_page_scss"] in out
    u = c.last_user
    assert "CpmsEduPondgLstSearchForm" in u and "CpmsEduPondgLstDataTable" in u  # sees real children
    assert "provide" in u and "searchParams" in u        # orchestrator state pattern hint
```
- [ ] **Step 2: FAIL.**
- [ ] **Step 3: implement**:
  - `async def gen_component(contract, guide, comp, types) -> dict`: ONE call. Prompt includes guide + `<script setup lang="ts">` requirement + the component's role; for DataTable add `DataTable2` wrapper + `:columns` prop + `TableColumn` + `scrollHeight="540px"` hints and the `columns` from `contract["frontend"]["columns"]`; for SearchForm add `inject('searchParams')` + `SearchFormRow` + watch `!== undefined` hints and `search_fields`; dep `types`. Returns the component `.vue` + `.scss` from bindings (`vue_{comp.lower()}`, `..._scss`), and for DataTable also `vue_datatable_utils` (a second call OR a single reply split — simplest: a separate gpt call for utils, OR generate utils inline; for the test just return all three keys; you may make 1 call for vue and synthesize a minimal utils stub, but PREFER 2 calls: one for the .vue, one for utils/index.ts. The .scss can be a small generated stub or a 3rd call — to satisfy the test, return a non-empty .scss string; a focused `gpt` call or a minimal `/* {Comp} styles */` placeholder is acceptable since scss is style-only). Keep it pragmatic: vue via LLM; scss minimal stub; utils via LLM for DataTable.
  - `async def gen_index(contract, guide, components: dict, types) -> dict`: ONE call. Prompt includes guide + the child component SOURCES (so index.vue binds real props/emits) + orchestrator hints (`provide('searchParams')`, `provide('t')`, `onMounted(handleSearch)`, ContentHeader). Returns `{vue_page_path: stripped, vue_page_scss_path: scss_stub}`.
- [ ] **Step 4: PASS (3).** **Step 5: commit** (`feat(codegen): frontend component + index.vue generators (index last)`).

---

## Task 3: Frontend static validation (`frontend_validate.py`)

**Files:** Create `backend/app/llm/graph/frontend_validate.py`, `backend/tests/graph/test_frontend_validate.py`.

- [ ] **Step 1: failing tests** asserting: (a) a `.vue` with `scrollHeight="flex"` is flagged; (b) `alert(`/`confirm(` flagged; (c) `<script>` without `setup` flagged; (d) a DataTable `.vue` using `<Column>` children instead of `:columns` prop flagged; (e) a clean set returns []. Reuse `tools.static_check_impl(path, content, file_type, "frontend")` for (a-c); implement (d) as a cross-file/per-file regex (`<Column ` present in a `vue_datatable` file AND no `:columns`).
- [ ] **Step 2: FAIL.**
- [ ] **Step 3: implement** `validate_frontend(files, contract) -> list[dict]`: per frontend file → `tools.static_check_impl(..., "frontend")`; plus a DataTable check (file_type in {vue_datatable, vue_page}: if `<Column ` appears and `:columns` does not → issue "DataTable must use :columns prop, not <Column> children"). Return issues list.
- [ ] **Step 4: PASS.** **Step 5: commit** (`feat(codegen): frontend static validation`).

---

## Task 4: Regression + integration smoke

- [ ] **Step 1:** `env $DUMMY_ENV pytest -m "not llm" -q` → green.
- [ ] **Step 2:** Additive check: `git diff --name-only <phase5-base>..HEAD -- backend/app/llm/graph` shows only `gen_frontend.py` + `frontend_validate.py` new.
- [ ] **Step 3:** Smoke `test_phase5_frontend.py` (scripted LLM): contract → `plan_and_bind` → run `gen_types`/`gen_api`/`gen_component`(×components)/`gen_index` with a `_Scripted` client → assert every `bindings.paths` frontend key has a produced file, and `validate_frontend(produced, contract)` on a clean `<script setup>` reply returns []. Commit.

---

## Self-Review
- Spec coverage: spec §5.2 frontend (types→API→components→index.vue last, multi-file via Phase-1 frontend_paths) → Tasks 1-2; FE static-check (§6 [4]) → Task 3. Deferred: vite compile-loop (§6 [5]) + wiring → Phase 6.
- Placeholders: scss generated as a minimal stub (style-only, refined by the compile-loop later) — explicitly noted, not a silent gap.
- Type consistency: all paths read from `contract["bindings"]["paths"]` (Phase-2 keys); generator signatures `(contract, guide, ...deps)` consistent with Phase-4 style; `gpt55_client` module-level + monkeypatchable.
