# Codegen Rewrite — Phase 2: Contract Resolver + File-Plan/Bindings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the contract-first core: a validated Contract data model, an LLM `contract_resolve` node that produces the single shared contract (incl. `module`/`category` per decision O1), and a deterministic `plan_and_bind` node that derives all paths/bindings/file-plan from the contract — additive modules + nodes, not yet wired into the live graph.

**Architecture:** `contract_schema.py` defines the Contract as pydantic models (validation boundary). `contract_resolve.py` is an async LangGraph node that calls `gpt55_client.complete()` with the spec + confirmed mockup + 테이블정보, parses JSON, validates via pydantic (one retry), and returns `{contract}`. `plan_and_bind.py` is a pure node that consumes the contract and Phase-1 `paths`/`guide_config` + reused `naming` derivations to compute `bindings` (paths, statement-ids, packages, namespace, file list) and returns `{contract, plan}`. No edits to the live graph (`build.py`, old `nodes.py`) this phase.

**Tech Stack:** Python 3.11+, pydantic (available via pydantic-settings), pytest (asyncio_mode=auto), `gpt55_client` (Responses API). Phase-1 modules `app.llm.graph.guide_config` and `app.llm.graph.paths` are available.

---

## Test harness (reuse from Phase 1)

```bash
export DUMMY_ENV='AZURE_OPENAI_API_KEY=dummy AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com GPT55_AZURE_OPENAI_API_KEY=dummy GPT55_AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com AOAI_API_KEY=dummy AOAI_ENDPOINT=https://dummy.openai.azure.com OPENAI_API_KEY=dummy ANTHROPIC_API_KEY=dummy'
```
Run from `/Users/g1kang/projects/need-only-prd/backend` with `source .venv/bin/activate`, tests as `env $DUMMY_ENV pytest ... -v`. Async node tests need no marker (asyncio_mode=auto). LLM-scripted tests use a fake client (no real creds, no `llm` marker).

---

## File Structure

- **Create** `backend/app/llm/graph/contract_schema.py` — pydantic Contract models + `parse_contract(data)->Contract` validator. One responsibility: the contract data shape + validation.
- **Create** `backend/app/llm/graph/contract_resolve.py` — `CONTRACT_RESOLVER_SYSTEM` prompt + `async def contract_resolve(state)` node (LLM → JSON → pydantic validate → 1 retry).
- **Create** `backend/app/llm/graph/plan_and_bind.py` — `def plan_and_bind(state)` pure node: contract → bindings + file plan.
- **Create** tests: `test_contract_schema.py`, `test_contract_resolve.py`, `test_plan_and_bind.py`.

No existing files modified. Reuses (imports only): `app.llm.graph.paths`, `app.llm.graph.guide_config`, and `app.llm.graph.naming` (deterministic fns `statement_id`, `dao_method`, `java_type`, `ops_for_screen_type`, `package_from_java_path`). The old graph wiring stays untouched until Phase 6.

---

## Task 1: Contract data model (`contract_schema.py`)

**Files:** Create `backend/app/llm/graph/contract_schema.py`, `backend/tests/graph/test_contract_schema.py`.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/graph/test_contract_schema.py`:

```python
import pytest
from pydantic import ValidationError

from app.llm.graph.contract_schema import Contract, Identity, parse_contract

_MIN = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list",
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm",
                           "db_type": "varchar(100)", "java_type": "String"}]},
}


def test_parse_contract_minimal_ok():
    c = parse_contract(_MIN)
    assert isinstance(c, Contract)
    assert c.identity.module == "edu"
    assert c.identity.category == "pondg"
    assert c.archetype == "list"
    # optional sections default empty, not None
    assert c.api == [] and c.frontend.components == [] and c.bindings.paths == {}


def test_parse_contract_missing_identity_module_raises():
    bad = {**_MIN, "identity": {**_MIN["identity"]}}
    del bad["identity"]["module"]          # O1: module is REQUIRED on the contract
    with pytest.raises(ValidationError):
        parse_contract(bad)


def test_parse_contract_missing_category_raises():
    bad = {**_MIN, "identity": {**_MIN["identity"]}}
    del bad["identity"]["category"]        # O1: category is REQUIRED on the contract
    with pytest.raises(ValidationError):
        parse_contract(bad)


def test_parse_contract_rejects_non_dict():
    with pytest.raises(ValidationError):
        parse_contract("not a dict")


def test_contract_round_trips_to_dict():
    c = parse_contract(_MIN)
    d = c.model_dump()
    assert d["identity"]["screen_id"] == "cpmsEduPondgLst"
    # re-parse the dumped dict is stable
    assert parse_contract(d).identity.class_name == "CpmsEduPondgLst"
```

- [ ] **Step 2: Run to verify FAIL**

Run: `env $DUMMY_ENV pytest tests/graph/test_contract_schema.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement `contract_schema.py`**

Create `backend/app/llm/graph/contract_schema.py`:

```python
"""The Contract — the single shared artifact every generator consumes.

Defined as pydantic models so the LLM resolver output is validated at one
boundary (parse_contract). `bindings` is filled deterministically later
(plan_and_bind), so it defaults empty here. Mirrors the design spec §3.
"""

from __future__ import annotations

from pydantic import BaseModel


class Identity(BaseModel):
    module: str                 # LV1, e.g. "edu"  (REQUIRED — decision O1)
    category: str               # LV2, e.g. "pondg" (REQUIRED — decision O1)
    screen_id: str              # camelCase, e.g. "cpmsEduPondgLst"
    class_name: str             # PascalCase, e.g. "CpmsEduPondgLst"
    program_id: str             # SPEC #1 verbatim (seed lbl_cd prefix SSOT)
    window_id: str = ""
    menu_id: str = ""
    p_menu_id: str = ""


class Column(BaseModel):
    snake: str
    camel: str
    db_type: str = ""
    java_type: str = ""
    pk: bool = False
    nullable: bool = True
    searchable: bool = False
    audit: bool = False
    code: str | None = None     # cls_id when common-coded (then *_nm is JOIN-resolved)


class Table(BaseModel):
    name: str
    pk: list[str] = []
    columns: list[Column] = []


class ReqField(BaseModel):
    camel: str
    snake: str
    java_type: str = "String"
    optional: bool = True
    filter: str = ""            # ILIKE | eq | range | ""


class ResField(BaseModel):
    camel: str
    snake: str
    java_type: str = "String"
    is_status: bool = False


class Fields(BaseModel):
    request: list[ReqField] = []
    response: list[ResField] = []


class ApiSig(BaseModel):
    method: str
    service_id: str = ""
    url: str = ""
    req_dto: str = ""
    res_dto: str = ""
    authority: str = ""


class FrontendPlan(BaseModel):
    components: list[str] = []          # subset of SearchForm/DataTable/SumGrid/ProgressList
    search_fields: list[str] = []
    columns: list[dict] = []
    common_code_load: str = ""


class SeedMeta(BaseModel):
    labels: list[dict] = []
    menu: dict = {}
    common_codes: list[dict] = []
    pgm_url: str = ""


class Bindings(BaseModel):
    statement_ids: list[str] = []
    dao_methods: list[str] = []
    namespace: str = ""
    packages: dict[str, str] = {}
    audit_map: dict[str, str] = {}      # populated in Phase 4 (Mapper gen)
    paths: dict[str, str] = {}
    files: list[dict] = []


class Contract(BaseModel):
    identity: Identity
    archetype: str
    ops: list[str] = []
    table: Table
    fields: Fields = Fields()
    api: list[ApiSig] = []
    frontend: FrontendPlan = FrontendPlan()
    seed: SeedMeta = SeedMeta()
    bindings: Bindings = Bindings()


def parse_contract(data: object) -> Contract:
    """Validate raw (LLM-parsed) data into a Contract. Raises pydantic ValidationError."""
    return Contract.model_validate(data)
```

- [ ] **Step 4: Run to verify PASS (5 passed).**
- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/graph/contract_schema.py backend/tests/graph/test_contract_schema.py
git commit -m "$(printf 'feat(codegen): Contract pydantic schema (single shared artifact)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 2: Contract Resolver node (`contract_resolve.py`)

**Files:** Create `backend/app/llm/graph/contract_resolve.py`, `backend/tests/graph/test_contract_resolve.py`.

- [ ] **Step 1: Write failing tests (scripted fake LLM client — no real creds)**

Create `backend/tests/graph/test_contract_resolve.py`:

```python
import json
import pytest

from app.llm.graph import contract_resolve as cr

pytestmark = pytest.mark.asyncio

_VALID = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list",
    "ops": ["selectList", "count"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm",
                           "db_type": "varchar(100)", "java_type": "String"}]},
    "frontend": {"components": ["SearchForm", "DataTable"]},
}


class _Scripted:
    """Fake gpt55_client returning queued replies; records calls."""
    def __init__(self, *replies):
        self._replies = list(replies)
        self.calls = []
    async def complete(self, system, user, max_tokens=16384):
        self.calls.append((system, user))
        return self._replies.pop(0)


def _state():
    return {"spec_markdown": "spec", "confirmed_vue": "<template/>",
            "table_info": "cptb_edu_pondg cols...", "page_type": "list"}


async def test_contract_resolve_returns_validated_contract(monkeypatch):
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(_VALID)))
    out = await cr.contract_resolve(_state())
    c = out["contract"]
    assert c["identity"]["module"] == "edu"        # O1: module present
    assert c["identity"]["category"] == "pondg"    # O1: category present
    assert c["archetype"] == "list"
    assert c["table"]["name"] == "cptb_edu_pondg"


async def test_contract_resolve_retries_once_on_bad_json(monkeypatch):
    client = _Scripted("not json {", json.dumps(_VALID))
    monkeypatch.setattr(cr, "gpt55_client", client)
    out = await cr.contract_resolve(_state())
    assert out["contract"]["identity"]["class_name"] == "CpmsEduPondgLst"
    assert len(client.calls) == 2                  # retried exactly once


async def test_contract_resolve_retries_once_on_schema_violation(monkeypatch):
    bad = {**_VALID, "identity": {k: v for k, v in _VALID["identity"].items() if k != "module"}}
    client = _Scripted(json.dumps(bad), json.dumps(_VALID))
    monkeypatch.setattr(cr, "gpt55_client", client)
    out = await cr.contract_resolve(_state())
    assert out["contract"]["identity"]["module"] == "edu"
    assert len(client.calls) == 2


async def test_contract_resolve_raises_after_two_failures(monkeypatch):
    monkeypatch.setattr(cr, "gpt55_client", _Scripted("nope", "still nope"))
    with pytest.raises(ValueError):
        await cr.contract_resolve(_state())


async def test_contract_resolve_emits_contract_event(monkeypatch):
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(_VALID)))
    out = await cr.contract_resolve(_state())
    assert any(e.get("type") == "contract" for e in out["events"])
```

- [ ] **Step 2: Run to verify FAIL** (`module app.llm.graph.contract_resolve` not found).

- [ ] **Step 3: Implement `contract_resolve.py`**

Create `backend/app/llm/graph/contract_resolve.py`:

```python
"""Contract Resolver node — produces the single shared Contract from spec + mockup.

The keystone of the rewrite: one LLM call (gpt-5.5) resolves screen identity
(incl. module/category — decision O1), archetype, ops, target table+columns+PK,
field map, frontend component plan, api/seed metadata. Output is validated against
the pydantic Contract (parse_contract) with one retry, so downstream nodes consume
a guaranteed-shaped artifact. bindings are filled later by plan_and_bind.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from app.llm.graph.llm import gpt55_client
from app.llm.graph.contract_schema import parse_contract
from app.llm.graph._text import strip_fences as _strip_fences

CONTRACT_RESOLVER_SYSTEM = """\
You are a requirements analyst for the CPMS framework. From a spec, a confirmed \
Vue mockup, and real DB table info, produce ONE structured CONTRACT as JSON. \
Do NOT generate code.

Output ONLY a JSON object with keys:
  identity: {module, category, screen_id, class_name, program_id, window_id, menu_id, p_menu_id}
  archetype: one of "list" | "list-detail" | "edit" | "popup" | "tab-detail"
  ops: subset of ["selectList","count","selectOne","insert","update","delete"]
  table: {name, pk: [...], columns: [{snake, camel, db_type, java_type, pk, nullable, searchable, audit, code}]}
  fields: {request: [{camel, snake, java_type, optional, filter}], response: [{camel, snake, java_type, is_status}]}
  api: [{method, service_id, url, req_dto, res_dto, authority}]
  frontend: {components: [...], search_fields: [...], columns: [...], common_code_load}
  seed: {labels: [...], menu: {...}, common_codes: [...], pgm_url}

Rules:
- identity.module is the LV1 domain code (e.g. "edu", "sy"); identity.category is the
  LV2 grouping (e.g. "pondg", "ds"). BOTH are required — infer them from the spec /
  screen code / menu context. screen_id is camelCase; class_name is PascalCase.
- program_id is the SPEC Screen Metadata program id, verbatim.
- Map every Vue field to its real DB column using the table info. Dates/IDs are String.
- frontend.components: include "SumGrid" ONLY if the screen needs per-status aggregate
  counts with click-to-filter; never include "ProgressList" unless explicitly requested.
- The contract is the single source of truth for all downstream generation.
"""


def _build_user(state: dict) -> str:
    return (
        f"=== SPEC ===\n{state.get('spec_markdown', '')}\n\n"
        f"=== CONFIRMED VUE ===\n{state.get('confirmed_vue', '')}\n\n"
        f"=== TABLE INFO ===\n{state.get('table_info', '')}\n\n"
        f"=== CONFIRMED PAGE TYPE ===\n{state.get('page_type', '')}\n"
    )


async def contract_resolve(state: dict) -> dict:
    """LLM → JSON → pydantic-validated Contract (one retry). Returns {contract, events}."""
    user = _build_user(state)
    last_err: Exception | None = None
    for attempt in range(2):
        prompt = user if attempt == 0 else user + "\n\nReturn ONLY valid JSON matching the schema."
        raw = await gpt55_client.complete(CONTRACT_RESOLVER_SYSTEM, prompt)
        try:
            data = json.loads(_strip_fences(raw))
            contract = parse_contract(data)
        except (ValueError, ValidationError) as exc:   # json error or schema violation
            last_err = exc
            continue
        # confirmed mockup page_type is authoritative over the model's archetype guess
        page_type = state.get("page_type") or ""
        cdict = contract.model_dump()
        if page_type:
            cdict["archetype"] = page_type
        return {"contract": cdict,
                "events": [{"type": "contract", "contract": cdict}]}
    raise ValueError(f"contract_resolve: invalid contract after retry: {last_err}")
```

- [ ] **Step 4: Run to verify PASS (5 passed).**
- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/graph/contract_resolve.py backend/tests/graph/test_contract_resolve.py
git commit -m "$(printf 'feat(codegen): contract_resolve LLM node (validated, O1 module/category)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 3: File-Plan + Bindings node (`plan_and_bind.py`)

**Files:** Create `backend/app/llm/graph/plan_and_bind.py`, `backend/tests/graph/test_plan_and_bind.py`.

Reuses Phase-1 `paths` + `guide_config` and the deterministic `naming` fns. Backend generated file types: `db_init_sql`, `dto_request`, `dto_response`, `mapper_xml`, `dao_impl`, `service_impl` (interfaces NOT generated). Frontend types via `paths.frontend_paths`. Statement ids/dao methods from `naming` over the contract ops.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/graph/test_plan_and_bind.py`:

```python
from app.llm.graph.plan_and_bind import plan_and_bind

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
    "frontend": {"components": ["SearchForm", "DataTable"]},
}


def _bind():
    return plan_and_bind({"contract": _CONTRACT})


def test_bind_backend_paths_from_guide_templates():
    b = _bind()["contract"]["bindings"]
    assert b["paths"]["dto_request"] == (
        "src/main/java/biz/edu/dto/request/CpmsEduPondgLstReqDto.java")
    assert b["paths"]["mapper_xml"] == (
        "src/main/resources/biz/edu/mybatis/mappers/CpmsEduPondgLstMapper.xml")
    assert b["paths"]["db_init_sql"] == "db/init.sql"


def test_bind_frontend_paths_present():
    b = _bind()["contract"]["bindings"]
    assert b["paths"]["vue_page"] == "src/pages/edu/pondg/cpmsEduPondgLst/index.vue"
    assert b["paths"]["vue_types"] == "src/api/pages/edu/pondg/types.ts"
    assert b["paths"]["vue_searchform"].endswith("/CpmsEduPondgLstSearchForm.vue")


def test_bind_statement_ids_and_dao_methods_match():
    b = _bind()["contract"]["bindings"]
    assert "selectCpmsEduPondgLstList" in b["statement_ids"]
    assert "insertCpmsEduPondgLst" in b["statement_ids"]
    # dao methods are identical to statement ids (1:1 binding)
    assert b["dao_methods"] == b["statement_ids"]


def test_bind_namespace_and_packages():
    b = _bind()["contract"]["bindings"]
    assert b["namespace"] == "biz.edu.dao.CpmsEduPondgLstDaoImpl"
    assert b["packages"]["dto_request"] == "biz.edu.dto.request"
    assert b["packages"]["service_impl"] == "biz.edu.service"


def test_bind_file_plan_lists_all_artifacts_with_layer():
    plan = _bind()["plan"]
    by_type = {f["file_type"]: f for f in plan["files"]}
    # backend + data
    for ft in ("db_init_sql", "dto_request", "dto_response",
               "mapper_xml", "dao_impl", "service_impl"):
        assert ft in by_type, f"missing {ft}"
    assert by_type["dao_impl"]["layer"] == "backend"
    assert by_type["db_init_sql"]["layer"] == "data"
    # frontend
    assert by_type["vue_page"]["layer"] == "frontend"
    assert by_type["vue_types"]["layer"] == "frontend"


def test_bind_ops_fallback_to_archetype_when_contract_ops_empty():
    c = {**_CONTRACT, "ops": []}
    b = plan_and_bind({"contract": c})["contract"]["bindings"]
    # list-detail archetype implies the full CRUD op set → non-empty statement ids
    assert b["statement_ids"]
```

- [ ] **Step 2: Run to verify FAIL.**

- [ ] **Step 3: Implement `plan_and_bind.py`**

Create `backend/app/llm/graph/plan_and_bind.py`:

```python
"""File-Plan + Bindings — deterministic derivation from the resolved Contract.

Replaces the blind planner + path-rewriting derive_contract. From the contract it
computes: target paths (Phase-1 paths resolver, guide-driven), the statement-id /
dao-method set (naming, 1:1), Java packages + Mapper namespace, and the concrete
file plan (every artifact with path/file_type/layer). Pure — no LLM, no I/O beyond
reading the fixed guide via the path resolver.
"""

from __future__ import annotations

from app.llm.graph import naming, paths

# Generated backend/data file types (interfaces are NOT generated; see BackendGuide §4.4).
_BACKEND_TYPES = ("dto_request", "dto_response", "mapper_xml", "dao_impl", "service_impl")
_DATA_TYPES = ("db_init_sql",)
_LAYER = ({t: "backend" for t in _BACKEND_TYPES}
          | {t: "data" for t in _DATA_TYPES})


def _identity(contract: dict) -> paths.Identity:
    i = contract["identity"]
    return paths.Identity(module=i["module"], category=i["category"],
                          screen_id=i["screen_id"], class_name=i["class_name"])


def _ops(contract: dict) -> list[str]:
    ops = contract.get("ops") or []
    if ops:
        return ops
    return naming.ops_for_screen_type(contract.get("archetype", "list"))


def plan_and_bind(state: dict) -> dict:
    """Contract -> {contract (with bindings), plan}. Deterministic."""
    contract = dict(state["contract"])
    ident = _identity(contract)
    screen = ident.class_name

    # 1) paths (backend/data from §11.4 templates; frontend from resolver)
    path_map: dict[str, str] = {}
    files: list[dict] = []
    for ft in _BACKEND_TYPES + _DATA_TYPES:
        p = paths.backend_path(ft, ident)
        if p:
            path_map[ft] = p
            files.append({"file_path": p, "file_type": ft, "layer": _LAYER[ft]})
    fe = paths.frontend_paths(ident, contract.get("frontend", {}).get("components", []))
    for ft, p in fe.items():
        path_map[ft] = p
        files.append({"file_path": p, "file_type": ft, "layer": "frontend"})

    # 2) statement ids == dao methods (1:1), from ops
    stmt_ids = [naming.statement_id(op, screen) for op in _ops(contract)]

    # 3) packages (from the java paths) + mapper namespace
    pkgs: dict[str, str] = {}
    for ft in _BACKEND_TYPES:
        p = path_map.get(ft)
        if p and p.endswith(".java"):
            pkg = naming.package_from_java_path(p)
            if pkg:
                pkgs[ft] = pkg
    dao_pkg = pkgs.get("dao_impl", f"biz.{ident.module}.dao")
    namespace = f"{dao_pkg}.{screen}DaoImpl"

    contract["bindings"] = {
        **contract.get("bindings", {}),
        "statement_ids": stmt_ids,
        "dao_methods": list(stmt_ids),
        "namespace": namespace,
        "packages": pkgs,
        "paths": path_map,
        "files": files,
    }
    return {"contract": contract,
            "plan": {"files": files},
            "events": [{"type": "plan", "files": files}]}
```

- [ ] **Step 4: Run to verify PASS (6 passed).**
- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/graph/plan_and_bind.py backend/tests/graph/test_plan_and_bind.py
git commit -m "$(printf 'feat(codegen): plan_and_bind deterministic bindings + file plan\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 4: Phase-2 regression + integration check

**Files:** none (verification).

- [ ] **Step 1: Full non-llm suite green**

Run: `env $DUMMY_ENV pytest -m "not llm" -q` → all pass (Phase-1 259 + new Phase-2 tests). No prior test changes.

- [ ] **Step 2: Confirm additive only**

Run: `git diff --name-only fbe175e..HEAD -- backend/app/llm/graph | sort` → only `contract_resolve.py`, `contract_schema.py`, `guide_config.py`, `paths.py`, `plan_and_bind.py` (no `nodes.py`/`build.py`/`naming.py`/`guides.py` modifications). The live graph is unchanged; new nodes are wired in Phase 6.

- [ ] **Step 3: End-to-end deterministic smoke (no LLM)**

Add `backend/tests/graph/test_phase2_pipeline.py`:

```python
from app.llm.graph.contract_schema import parse_contract
from app.llm.graph.plan_and_bind import plan_and_bind


def test_resolved_contract_flows_into_bindings():
    # a pydantic-validated contract (as contract_resolve would emit) feeds plan_and_bind
    contract = parse_contract({
        "identity": {"module": "edu", "category": "pondg",
                     "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                     "program_id": "CPMSEDUPONDGLST"},
        "archetype": "list-detail",
        "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
        "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
        "frontend": {"components": ["SearchForm", "DataTable"]},
    }).model_dump()
    out = plan_and_bind({"contract": contract})
    b = out["contract"]["bindings"]
    assert b["namespace"] == "biz.edu.dao.CpmsEduPondgLstDaoImpl"
    assert b["paths"]["dao_impl"].endswith("CpmsEduPondgLstDaoImpl.java")
    assert {f["file_type"] for f in out["plan"]["files"]} >= {
        "dto_request", "dto_response", "mapper_xml", "dao_impl",
        "service_impl", "db_init_sql", "vue_page", "vue_types"}
```

Run: `env $DUMMY_ENV pytest tests/graph/test_phase2_pipeline.py -v` → PASS. Commit:
```bash
git add backend/tests/graph/test_phase2_pipeline.py
git commit -m "$(printf 'test(codegen): phase-2 contract->bindings integration smoke\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Self-Review

**Spec coverage:** spec §3 Contract schema → Task 1. spec §2 step [1] Contract Resolver (LLM, validated, O1 module/category) → Task 2. spec §2 step [2] File-Plan/Bindings (paths via Phase-1 resolver, statement-ids, packages, namespace, file list) → Task 3. Deferred-by-design: `bindings.audit_map` (Phase 4 Mapper gen), `seed.pgm_url` finalization (Phase 6, needs frontend output), graph wiring (Phase 6). These are noted in code comments, not silent gaps.

**Placeholder scan:** No TBD/TODO. Every code step has complete code; every test step full assertions. The retry/validation logic is concrete.

**Type consistency:** `Identity` fields (`module/category/screen_id/class_name/program_id`) are consistent across `contract_schema.py`, `paths.Identity` (constructed in `plan_and_bind._identity`), and all tests. `parse_contract` returns `Contract`; `.model_dump()` produces the dict consumed by `plan_and_bind`. `contract_resolve` returns `{contract: dict, events}`; `plan_and_bind` consumes `state["contract"]` dict and returns `{contract, plan, events}`. Statement-id/dao-method naming uses `naming.statement_id` consistently (1:1). Backend file-type tuple matches `paths.backend_path` keys and `naming` ops.

**Note on reuse vs de-hardcoding:** `plan_and_bind` reuses `naming.statement_id/dao_method/ops_for_screen_type` which encode §3.6/§4.4.3 conventions in Python (not yet guide-parsed). This is acceptable for Phase 2 (framework-invariant naming scheme, already tested); fully config-driving them by parsing §3.6/§4.4.3 is a candidate hardening flagged for a later pass if a guide swap changes the scheme.
