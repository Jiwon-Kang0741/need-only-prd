# Codegen Rewrite — Phase 1: Foundation (Guide-Driven Config + Path Resolver) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic, LLM-free foundation of the rewritten codegen pipeline — read-only parsers that source rules from the FIXED guides, plus a path resolver — fully unit/golden tested, added without touching the live graph (zero regression).

**Architecture:** Two new pure modules. `guide_config.py` parses the machine-readable parts of the fixed guides (BackendGuide §11.4 path table, DataGuide §5 Natural Keys, DataGuide seed order) into Python dicts/lists, re-read fresh so guide edits/swaps reflect with no code change. `paths.py` resolves backend paths from the parsed §11.4 templates and resolves frontend paths via a code resolver (the guide has no parseable FE path table), with guide examples as golden tests. No live-graph wiring in this phase — these modules are consumed in Phase 2+.

**Tech Stack:** Python 3.11+, pytest (asyncio_mode=auto), regex parsing, dataclasses. Guides at `pfy_prompt/` (settings.PROMPT_REFERENCE_DIR, default `../pfy_prompt`).

---

## Test harness (used by every test step below)

Tests import `app.main` via `tests/conftest.py`, which instantiates LLM clients at import → dummy creds required. Define once and reuse:

```bash
export DUMMY_ENV='AZURE_OPENAI_API_KEY=dummy AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com GPT55_AZURE_OPENAI_API_KEY=dummy GPT55_AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com AOAI_API_KEY=dummy AOAI_ENDPOINT=https://dummy.openai.azure.com OPENAI_API_KEY=dummy ANTHROPIC_API_KEY=dummy'
```

All test commands run from `/Users/g1kang/projects/need-only-prd/backend` with the venv active (`source .venv/bin/activate`) and prefixed with `env $DUMMY_ENV`.

---

## File Structure

- **Create** `backend/app/llm/graph/guide_config.py` — read-only guide parsers. Pure functions; split-parse design (`_parse_*(text)` testable in isolation + `load_*()` reading the real fixed guide).
- **Create** `backend/app/llm/graph/paths.py` — `Identity` dataclass + `backend_path()` (from §11.4 templates) + `frontend_paths()` (code resolver) + `data_path()`.
- **Create** `backend/tests/graph/test_guide_config.py` — unit (fixtures) + integration (real fixed guide) tests.
- **Create** `backend/tests/graph/test_paths.py` — golden-example tests from the guide.

No existing files are modified in Phase 1. `naming.py`/`guides.py`/`CODEGEN_RULES.md` stay untouched until Phase 6 wiring.

---

## Task 1: Guide config parsers (`guide_config.py`)

**Files:**
- Create: `backend/app/llm/graph/guide_config.py`
- Test: `backend/tests/graph/test_guide_config.py`

- [ ] **Step 1: Write failing tests for `_parse_backend_path_templates` (fixture-based)**

Create `backend/tests/graph/test_guide_config.py`:

```python
from app.llm.graph import guide_config as gc

_BACKEND_114 = """\
### 11.4 파일 경로 규칙 (코드 생성 시)

| 파일 유형 | 경로 패턴 |
|-----------|-----------|
| DB Init SQL | `db/init.sql` |
| DTO Request | `src/main/java/biz/{module}/dto/request/{ClassName}ReqDto.java` |
| DTO Response | `src/main/java/biz/{module}/dto/response/{ClassName}ResDto.java` |
| DAO Impl | `src/main/java/biz/{module}/dao/{ClassName}DaoImpl.java` |
| Service Impl | `src/main/java/biz/{module}/service/{ClassName}ServiceImpl.java` |
| Mapper XML | `src/main/resources/biz/{module}/mybatis/mappers/{ClassName}Mapper.xml` |

### 11.5 다음 섹션
"""


def test_parse_backend_path_templates_normalizes_labels():
    out = gc._parse_backend_path_templates(_BACKEND_114)
    assert out["db_init_sql"] == "db/init.sql"
    assert out["dto_request"] == "src/main/java/biz/{module}/dto/request/{ClassName}ReqDto.java"
    assert out["dto_response"] == "src/main/java/biz/{module}/dto/response/{ClassName}ResDto.java"
    assert out["dao_impl"] == "src/main/java/biz/{module}/dao/{ClassName}DaoImpl.java"
    assert out["service_impl"] == "src/main/java/biz/{module}/service/{ClassName}ServiceImpl.java"
    assert out["mapper_xml"] == "src/main/resources/biz/{module}/mybatis/mappers/{ClassName}Mapper.xml"


def test_parse_backend_path_templates_drops_header_and_separator():
    out = gc._parse_backend_path_templates(_BACKEND_114)
    assert "파일_유형" not in out
    assert len(out) == 6


def test_parse_backend_path_templates_empty_when_section_absent():
    assert gc._parse_backend_path_templates("# no 11.4 here\n| a | b |\n") == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `env $DUMMY_ENV pytest tests/graph/test_guide_config.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute '_parse_backend_path_templates'`.

- [ ] **Step 3: Implement `guide_config.py` parsers (minimal to pass Task 1 tests)**

Create `backend/app/llm/graph/guide_config.py`:

```python
"""Read-only parsers over the FIXED guide md files.

The guides (pfy_prompt/{BackendGuide,FrontendGuide,DataGuide}) are immutable
external input — never edited. These parsers read the machine-readable parts
(Markdown tables, ordered lists) so codegen rules come from the guide as-is, with
no hardcoded rule values and no guide annotation. Each loader re-reads the file,
so a guide swap/edit reflects on the next call. `_parse_*(text)` helpers are pure
(unit-testable); `load_*()` read the real guide then parse.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import settings


def _read(relpath: str) -> str:
    p = Path(settings.PROMPT_REFERENCE_DIR) / relpath
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _normalize_label(label: str) -> str:
    """'DAO Impl' -> 'dao_impl' (lower, trim, spaces->underscore)."""
    return re.sub(r"\s+", "_", label.strip().lower())


_TABLE_ROW = re.compile(r"^\|(?P<c1>[^|\n]+)\|(?P<c2>[^|\n]+)\|\s*$", re.MULTILINE)
_BACKTICK = re.compile(r"`([^`]+)`")
_SEP_CHARS = set("-: ")


def _parse_backend_path_templates(text: str) -> dict[str, str]:
    """Parse BackendGuide §11.4 'file path rules' Markdown table -> {file_type: tpl}."""
    sec = re.search(r"###\s*11\.4.*?(?=\n###\s|\Z)", text, re.DOTALL)
    if not sec:
        return {}
    out: dict[str, str] = {}
    for m in _TABLE_ROW.finditer(sec.group(0)):
        label, val = m.group("c1").strip(), m.group("c2").strip()
        if not label or label == "파일 유형" or set(label) <= _SEP_CHARS:
            continue
        bt = _BACKTICK.search(val)
        if bt:
            out[_normalize_label(label)] = bt.group(1).strip()
    return out


def load_backend_path_templates() -> dict[str, str]:
    return _parse_backend_path_templates(_read("BackendGuide/표준.md"))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `env $DUMMY_ENV pytest tests/graph/test_guide_config.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/graph/guide_config.py backend/tests/graph/test_guide_config.py
git commit -m "feat(codegen): guide_config parser for BackendGuide §11.4 path table"
```

- [ ] **Step 6: Write failing tests for seed Natural Keys + seed order (fixtures)**

Append to `backend/tests/graph/test_guide_config.py`:

```python
_SEED = """\
## 5. Natural Key (Upsert 기준)

| 테이블 | Natural Key |
|--------|-------------|
| `cmn_class` | `(lang_cd, cls_id)` |
| `cmn_code` | `(cls_id, code_cd)` |
| `cmn_lbl` | `(lbl_cd, lang_cd)` |
| `cmn_menu` | `menu_id` |
| `cmn_pgm` | `pgm_id` |
| `cmn_role_menu` | `(role_id, menu_id)` |
| `cmn_role_pgm` | `(role_id, pgm_id)` |

모든 Upsert는 위 Key 기준 사용한다.

## 3. 생성 순서

1. `cmn_class`
2. `cmn_code`
3. `cmn_lbl`
4. `cmn_pgm`
5. `cmn_menu`
6. `cmn_role_pgm`
7. `cmn_role_menu`

순서 변경 금지.
"""


def test_parse_seed_natural_keys():
    out = gc._parse_seed_natural_keys(_SEED)
    assert out["cmn_class"] == ["lang_cd", "cls_id"]
    assert out["cmn_code"] == ["cls_id", "code_cd"]
    assert out["cmn_menu"] == ["menu_id"]
    assert out["cmn_role_pgm"] == ["role_id", "pgm_id"]
    assert len(out) == 7


def test_parse_seed_order():
    out = gc._parse_seed_order(_SEED)
    assert out == ["cmn_class", "cmn_code", "cmn_lbl", "cmn_pgm",
                   "cmn_menu", "cmn_role_pgm", "cmn_role_menu"]
```

- [ ] **Step 7: Run to verify they fail**

Run: `env $DUMMY_ENV pytest tests/graph/test_guide_config.py -k "seed" -v`
Expected: FAIL — `_parse_seed_natural_keys` not defined.

- [ ] **Step 8: Implement seed parsers**

Append to `backend/app/llm/graph/guide_config.py`:

```python
_NK_ROW = re.compile(r"^\|\s*`(cmn_\w+)`\s*\|\s*`([^`]+)`\s*\|", re.MULTILINE)
_ORDER_ROW = re.compile(r"^\s*\d+\.\s*`?(cmn_\w+)`?", re.MULTILINE)


def _parse_seed_natural_keys(text: str) -> dict[str, list[str]]:
    """DataGuide §5 'Natural Key' table -> {table: [key columns]}."""
    sec = re.search(r"(Natural\s*Key.*?)(?=\n##\s|\Z)", text, re.DOTALL | re.IGNORECASE)
    scope = sec.group(1) if sec else text
    out: dict[str, list[str]] = {}
    for m in _NK_ROW.finditer(scope):
        out[m.group(1)] = re.findall(r"[a-z_]+", m.group(2))
    return out


def _parse_seed_order(text: str) -> list[str]:
    """DataGuide §3/§14 seed generation order (ordered list of cmn_* tables)."""
    sec = re.search(r"(생성\s*순서.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    scope = sec.group(1) if sec else text
    return [m.group(1) for m in _ORDER_ROW.finditer(scope)]


def load_seed_natural_keys() -> dict[str, list[str]]:
    return _parse_seed_natural_keys(_read("DataGuide/01.seed_standard.md"))


def load_seed_order() -> list[str]:
    return _parse_seed_order(_read("DataGuide/01.seed_standard.md"))
```

- [ ] **Step 9: Run to verify they pass**

Run: `env $DUMMY_ENV pytest tests/graph/test_guide_config.py -v`
Expected: PASS (5 passed).

- [ ] **Step 10: Commit**

```bash
git add backend/app/llm/graph/guide_config.py backend/tests/graph/test_guide_config.py
git commit -m "feat(codegen): guide_config parsers for DataGuide seed Natural Keys + order"
```

- [ ] **Step 11: Write integration tests against the REAL fixed guides**

Append to `backend/tests/graph/test_guide_config.py`:

```python
def test_load_backend_path_templates_from_real_guide():
    # The fixed BackendGuide/표준.md §11.4 must yield all 6 generated backend/data types.
    out = gc.load_backend_path_templates()
    for ft in ("db_init_sql", "dto_request", "dto_response",
               "dao_impl", "service_impl", "mapper_xml"):
        assert ft in out, f"missing {ft} in §11.4 parse: {list(out)}"
    assert out["dto_request"].startswith("src/main/java/biz/{module}/dto/request/")


def test_load_seed_order_from_real_guide():
    assert gc.load_seed_order() == [
        "cmn_class", "cmn_code", "cmn_lbl", "cmn_pgm",
        "cmn_menu", "cmn_role_pgm", "cmn_role_menu"]


def test_load_seed_natural_keys_from_real_guide():
    nk = gc.load_seed_natural_keys()
    assert nk.get("cmn_lbl") == ["lbl_cd", "lang_cd"]
    assert nk.get("cmn_role_pgm") == ["role_id", "pgm_id"]
    assert set(nk) >= {"cmn_class", "cmn_code", "cmn_lbl", "cmn_pgm",
                       "cmn_menu", "cmn_role_menu", "cmn_role_pgm"}
```

- [ ] **Step 12: Run integration tests; fix parser if real-guide format differs**

Run: `env $DUMMY_ENV pytest tests/graph/test_guide_config.py -k "real_guide" -v`
Expected: PASS. If a regex fails to match the real heading/table (e.g. §5 heading text differs, or the order list lives under a different heading), adjust the `re.search` scope pattern in the corresponding `_parse_*` until these pass — the real fixed guide is the source of truth. Do NOT edit the guide.

- [ ] **Step 13: Commit**

```bash
git add backend/tests/graph/test_guide_config.py backend/app/llm/graph/guide_config.py
git commit -m "test(codegen): integration tests for guide_config against fixed guides"
```

---

## Task 2: Path resolver (`paths.py`)

**Files:**
- Create: `backend/app/llm/graph/paths.py`
- Test: `backend/tests/graph/test_paths.py`

- [ ] **Step 1: Write failing tests for backend path resolution**

Create `backend/tests/graph/test_paths.py`:

```python
from app.llm.graph.paths import Identity, backend_path, frontend_paths, data_path

# CPMS domain-function family: screenId camelCase, className PascalCase.
CPMS = Identity(module="edu", category="pondg",
                screen_id="cpmsEduPondgLst", class_name="CpmsEduPondgLst")


def test_backend_path_dto_request():
    assert backend_path("dto_request", CPMS) == (
        "src/main/java/biz/edu/dto/request/CpmsEduPondgLstReqDto.java")


def test_backend_path_mapper_xml():
    assert backend_path("mapper_xml", CPMS) == (
        "src/main/resources/biz/edu/mybatis/mappers/CpmsEduPondgLstMapper.xml")


def test_backend_path_unknown_type_returns_none():
    assert backend_path("not_a_type", CPMS) is None


def test_data_path():
    assert data_path() == "db/init.sql"
```

- [ ] **Step 2: Run to verify they fail**

Run: `env $DUMMY_ENV pytest tests/graph/test_paths.py -v`
Expected: FAIL — module `app.llm.graph.paths` does not exist.

- [ ] **Step 3: Implement `paths.py` (backend + data)**

Create `backend/app/llm/graph/paths.py`:

```python
"""Deterministic target-path resolver for generated files.

Backend/data paths come from the FIXED BackendGuide §11.4 table (parsed by
guide_config) — guide-driven, read-only. Frontend paths are a CODE resolver:
the FrontendGuide states them only as prose/examples (no parseable table), so we
substitute a fixed project-layout template validated by guide examples (golden
tests). Takes (module, category, screenId, className) — the resolver substitutes,
it does not derive casing (the Contract supplies both screenId and className).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.graph import guide_config


@dataclass(frozen=True)
class Identity:
    module: str
    category: str
    screen_id: str       # camelCase, e.g. "cpmsEduPondgLst"
    class_name: str      # PascalCase, e.g. "CpmsEduPondgLst" (== {ClassName}/{Screen})


def backend_path(file_type: str, ident: Identity) -> str | None:
    """Backend/data path from §11.4 template, or None if the guide has no template."""
    tpl = guide_config.load_backend_path_templates().get(file_type)
    if not tpl:
        return None
    return (tpl.replace("{module}", ident.module)
               .replace("{ClassName}", ident.class_name)
               .replace("{Screen}", ident.class_name))


def data_path() -> str:
    """The db init SQL output path (db_init_sql template == 'db/init.sql')."""
    return guide_config.load_backend_path_templates().get("db_init_sql", "db/init.sql")
```

- [ ] **Step 4: Run to verify backend/data tests pass**

Run: `env $DUMMY_ENV pytest tests/graph/test_paths.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/graph/paths.py backend/tests/graph/test_paths.py
git commit -m "feat(codegen): backend/data path resolver from §11.4 templates"
```

- [ ] **Step 6: Write failing golden tests for the frontend path resolver**

Append to `backend/tests/graph/test_paths.py`:

```python
# SY system-module family golden example from FrontendGuide (pmdp020 / PMDP020).
SY = Identity(module="sy", category="ds",
              screen_id="pmdp020", class_name="PMDP020")


def test_frontend_paths_page_and_types_and_api():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable"])
    assert fe["vue_page"] == "src/pages/sy/ds/pmdp020/index.vue"
    assert fe["vue_page_scss"] == "src/pages/sy/ds/pmdp020/pmdp020.scss"
    assert fe["vue_types"] == "src/api/pages/sy/ds/types.ts"          # category-shared
    assert fe["vue_api"] == "src/api/pages/sy/ds/pmdp020.ts"


def test_frontend_paths_components_folder_camel_file_pascal():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable"])
    assert fe["vue_searchform"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020SearchForm/PMDP020SearchForm.vue")
    assert fe["vue_searchform_scss"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020SearchForm/PMDP020SearchForm.scss")
    assert fe["vue_datatable"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020DataTable/PMDP020DataTable.vue")
    # only DataTable has a utils/index.ts
    assert fe["vue_datatable_utils"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020DataTable/utils/index.ts")


def test_frontend_paths_omits_sumgrid_when_not_requested():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable"])
    assert "vue_sumgrid" not in fe


def test_frontend_paths_includes_sumgrid_when_requested():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable", "SumGrid"])
    assert fe["vue_sumgrid"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020SumGrid/PMDP020SumGrid.vue")
    assert "vue_datatable_utils" in fe   # SumGrid does NOT add a utils dir
    assert "vue_sumgrid_utils" not in fe
```

- [ ] **Step 7: Run to verify they fail**

Run: `env $DUMMY_ENV pytest tests/graph/test_paths.py -k "frontend" -v`
Expected: FAIL — `frontend_paths` not defined.

- [ ] **Step 8: Implement the frontend path resolver**

Append to `backend/app/llm/graph/paths.py`:

```python
_FE_PAGE_BASE = "src/pages/{module}/{category}/{screenId}"
_FE_API_BASE = "src/api/pages/{module}/{category}"


def _sub(tpl: str, ident: Identity) -> str:
    return (tpl.replace("{module}", ident.module)
               .replace("{category}", ident.category)
               .replace("{screenId}", ident.screen_id)
               .replace("{ClassName}", ident.class_name))


def frontend_paths(ident: Identity, components: list[str]) -> dict[str, str]:
    """Resolve every frontend file path for one screen.

    Folder segments use the camelCase screenId ({screenId}{Comp}); .vue/.scss
    filenames use the PascalCase className ({ClassName}{Comp}). index.vue/ts,
    utils/index.ts, types.ts are lowercase exceptions. types.ts is category-shared.
    Only DataTable gets a utils/ dir.
    """
    page_base = _sub(_FE_PAGE_BASE, ident)
    api_base = _sub(_FE_API_BASE, ident)
    out: dict[str, str] = {
        "vue_page": f"{page_base}/index.vue",
        "vue_page_scss": f"{page_base}/{ident.screen_id}.scss",
        "vue_api": f"{api_base}/{ident.screen_id}.ts",
        "vue_types": f"{api_base}/types.ts",
    }
    for comp in components:           # "SearchForm" | "DataTable" | "SumGrid" | "ProgressList"
        folder = f"{page_base}/components/{ident.screen_id}{comp}"
        key = f"vue_{comp.lower()}"
        out[key] = f"{folder}/{ident.class_name}{comp}.vue"
        out[f"{key}_scss"] = f"{folder}/{ident.class_name}{comp}.scss"
        if comp == "DataTable":
            out["vue_datatable_utils"] = f"{folder}/utils/index.ts"
    return out
```

- [ ] **Step 9: Run to verify all path tests pass**

Run: `env $DUMMY_ENV pytest tests/graph/test_paths.py -v`
Expected: PASS (8 passed).

- [ ] **Step 10: Commit**

```bash
git add backend/app/llm/graph/paths.py backend/tests/graph/test_paths.py
git commit -m "feat(codegen): frontend path resolver (golden-tested from guide examples)"
```

---

## Task 3: Full-suite regression check (no live wiring changed)

**Files:** none (verification only).

- [ ] **Step 1: Run the whole non-LLM test suite**

Run: `env $DUMMY_ENV pytest -m "not llm" -q`
Expected: PASS — the pre-existing suite is green AND the new `test_guide_config.py` / `test_paths.py` pass. Phase 1 added only new modules + tests, so no prior test should change.

- [ ] **Step 2: Confirm zero live-graph changes**

Run: `git diff --name-only HEAD~6 -- backend/app/llm/graph | sort`
Expected: only `guide_config.py` and `paths.py` appear (no `nodes.py`, `naming.py`, `guides.py`, `build.py`). This proves the foundation is additive and CODEGEN_RULES.md is still intact for the live pipeline (it is deleted in Phase 6).

---

## Phase Roadmap (subsequent plans — authored when each phase begins)

Each is its own plan file under `docs/superpowers/plans/`, producing working/testable software:

- **Phase 2 — Contract Resolver + File-Plan/Bindings.** `contract_schema.py` (JSON Schema for §3 Contract), `contract_resolve` node (LLM, StructuredOutput against schema), `plan_and_bind` (deterministic: paths via Phase-1 resolver, statement-ids, packages, namespace, DAO method surface, audit map). Replaces blind `planner` + path-rewriting `derive_contract`.
- **Phase 3 — Skeleton Boot3/Java21/jakarta upgrade** (prerequisite for backend compile). pom parent 3.x, java 21, javax→jakarta vendored classes, JDK21 docker base; assembled skeleton compiles.
- **Phase 4 — Backend generation** staged (DTO → Mapper → DAO-template → Service) + backend static-check (§11.5) rewritten guide-driven + backend `mvn compile` fix loop.
- **Phase 5 — Frontend generation** (types → API → components → index.vue last), full ~8–12 file set via Phase-1 `frontend_paths`, FE static-check + existing vite fix loop.
- **Phase 6 — Data generation** (DDL early / SEED after frontend / deterministic `assemble_sql`), DataGuide §12/§16 validators (pgm_url no leading slash fix), **graph rewiring** to the new topology, **delete `CODEGEN_RULES.md`**, retire hollow reviewer, remove stale `hsc.tomms.web` strings.
- **Phase 7 — End-to-end** smoke (real gpt-5.5 once) + assembled `mvn compile` + `vite build` green; port reusable tests from the old suite; delete dead old nodes.

---

## Self-Review

**Spec coverage (Phase 1 portion):** Spec §4.1 (parseable→config: §11.4, Natural Keys, seed order) → Task 1. Spec §4.3 (path resolver: backend §11.4 parse + FE code resolver + golden tests) → Task 2. Spec §4.4 (CODEGEN_RULES.md deletion) → deferred to Phase 6 (correctly, to avoid breaking the live pipeline). Other spec sections map to Phases 2–7 in the roadmap. Phase-1 scope is complete.

**Placeholder scan:** No TBD/TODO/"handle appropriately". Every code step has full code; every test step has full assertions; Step 12 gives a concrete fix instruction (adjust the `re.search` scope) rather than a vague "fix it".

**Type consistency:** `Identity(module, category, screen_id, class_name)` is used identically in `test_paths.py`, `backend_path`, `frontend_paths`, `_sub`. `load_backend_path_templates()` returns `dict[str,str]` consumed by `backend_path`/`data_path`. `frontend_paths(ident, components)` signature matches all call sites. Parser names (`_parse_backend_path_templates`, `_parse_seed_natural_keys`, `_parse_seed_order`) match their `load_*` wrappers and tests.
