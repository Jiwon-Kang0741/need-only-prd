# Codegen Rewrite — Phase 6b: Graph Wiring (go-live, no deletions yet) Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. This phase rewires the LIVE graph but DELETES NOTHING (old nodes/CODEGEN_RULES stay as dead code until Phase 6c). Steps use checkbox (`- [ ]`).

**Goal:** Wire the contract-first generators into a runnable LangGraph and make `build_graph` (used by `sse_adapter`/`codegen.py`) the new pipeline. De-risked: prove the new graph runs end-to-end (scripted LLM) BEFORE removing the old path (Phase 6c).

**Architecture:** New `gen_nodes.py` holds LangGraph node wrappers that call the Phase 4–6 generators and wrap each produced `{path: content}` into a `GeneratedFile` (file_type/layer from `bindings.files`). New linear graph: `contract_resolve → plan_and_bind → gen_backend → gen_frontend → gen_data → validate → END`. `sse_adapter` node-name sets updated. Old node functions + CODEGEN_RULES remain (dead) — their direct unit tests still pass; only `test_build.py` (topology) is updated.

**Tech Stack:** LangGraph, reused generators/validators, `guides.load_guide_for_file_type`.

---

## Test harness
```bash
export DUMMY_ENV='AZURE_OPENAI_API_KEY=dummy AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com GPT55_AZURE_OPENAI_API_KEY=dummy GPT55_AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com AOAI_API_KEY=dummy AOAI_ENDPOINT=https://dummy.openai.azure.com OPENAI_API_KEY=dummy ANTHROPIC_API_KEY=dummy'
```
Run from `backend`: `source .venv/bin/activate && env $DUMMY_ENV pytest <file> -v`.

## Context (verified)
- `CodeGenState` (state.py): `files: Annotated[dict, merge_files]`, `events: Annotated[list, add]`, `open_issues: Annotated[list, add]`, `contract`, `plan`, plus inputs `spec_markdown/confirmed_vue/page_type/table_info`. `GeneratedFile` = `{file_path, file_type, layer, wave, content, status, status_log}`.
- `contract_resolve.contract_resolve(state)` (async) → `{contract, events}` (consumes spec_markdown/confirmed_vue/table_info/page_type — exactly what `sse_adapter.build_graph_input` provides).
- `plan_and_bind.plan_and_bind(state)` (sync) → `{contract, plan, events}`; fills `contract["bindings"]` incl. `files: [{file_path,file_type,layer}]` and `paths`.
- Generators: `gen_backend.gen_dtos/gen_mapper/gen_service(...)` (async, return `{path: content}`), `gen_backend.render_dao(contract)` (str); `gen_frontend.gen_types/gen_api/gen_component/gen_index`; `gen_data.gen_ddl/gen_seed` (str) + `assemble_sql(contract, ddl, seed)` (`{path: sql}`).
- Validators: `backend_validate.validate_backend(files, contract)`, `frontend_validate.validate_frontend(files, contract)`, `data_validate.validate_data(sql, contract)`.
- `guides.load_guide_for_file_type("dao_impl")` → whole BackendGuide; `("vue_page")` → FrontendGuide; `("db_init_sql")` → DataGuide.

---

## Task 1: Node wrappers (`gen_nodes.py`)

**Files:** Create `backend/app/llm/graph/gen_nodes.py`, `backend/tests/graph/test_gen_nodes.py`.

- [ ] **Step 1: failing tests** — `test_gen_nodes.py`:
```python
import pytest
from app.llm.graph import gen_nodes
from app.llm.graph.contract_schema import parse_contract
from app.llm.graph.plan_and_bind import plan_and_bind

pytestmark = pytest.mark.asyncio


def _contract():
    return plan_and_bind({"contract": parse_contract({
        "identity": {"module": "edu", "category": "pondg", "screen_id": "cpmsEduPondgLst",
                     "class_name": "CpmsEduPondgLst", "program_id": "CPMSEDUPONDGLST"},
        "archetype": "list-detail",
        "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
        "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
        "frontend": {"components": ["SearchForm", "DataTable"]},
    }).model_dump()})["contract"]


async def test_gen_backend_node_produces_wrapped_files(monkeypatch):
    from app.llm.graph import gen_backend as gb
    class _C:
        async def complete(self, s, u, max_tokens=16384): return "class X {}"
    monkeypatch.setattr(gb, "gpt55_client", _C())
    out = await gen_nodes.gen_backend_node({"contract": _contract()})
    files = out["files"]
    # dto_request/response, mapper, dao, service all present, wrapped as GeneratedFile
    types = {gf["file_type"] for gf in files.values()}
    assert {"dto_request", "dto_response", "mapper_xml", "dao_impl", "service_impl"} <= types
    for gf in files.values():
        assert set(gf) >= {"file_path", "file_type", "layer", "content", "status"}
        assert gf["layer"] == "backend"


async def test_gen_frontend_node_produces_files(monkeypatch):
    from app.llm.graph import gen_frontend as gfm
    class _C:
        async def complete(self, s, u, max_tokens=16384): return "<template/>"
    monkeypatch.setattr(gfm, "gpt55_client", _C())
    out = await gen_nodes.gen_frontend_node({"contract": _contract()})
    types = {gf["file_type"] for gf in out["files"].values()}
    assert "vue_page" in types and "vue_types" in types and "vue_datatable" in types


async def test_gen_data_node_produces_db_init(monkeypatch):
    from app.llm.graph import gen_data as gd
    class _C:
        async def complete(self, s, u, max_tokens=16384): return "CREATE TABLE t();"
    monkeypatch.setattr(gd, "gpt55_client", _C())
    out = await gen_nodes.gen_data_node({"contract": _contract()})
    paths = {gf["file_path"] for gf in out["files"].values()}
    assert "db/init.sql" in paths


def test_validate_node_runs_all_validators():
    contract = _contract()
    # a clean backend dao file -> no issue from validate_node's backend pass
    files = {"d/X.java": {"file_path": "d/X.java", "file_type": "dao_impl", "layer": "backend",
                          "wave": 0, "content": "package biz.edu.dao;\nclass X {}",
                          "status": "ok", "status_log": []}}
    out = gen_nodes.validate_node({"contract": contract, "files": files})
    assert "open_issues" in out and isinstance(out["open_issues"], list)
```

- [ ] **Step 2: FAIL.**
- [ ] **Step 3: implement** `backend/app/llm/graph/gen_nodes.py`:
```python
"""LangGraph node wrappers for the contract-first generators.

Each generator returns {path: content} strings; these wrappers wrap them into the
CodeGenState GeneratedFile shape (file_type/layer looked up from contract bindings)
and accumulate into state["files"]. Linear graph: contract_resolve -> plan_and_bind
-> gen_backend -> gen_frontend -> gen_data -> validate.
"""

from __future__ import annotations

from app.llm.graph import guides, gen_backend, gen_frontend, gen_data
from app.llm.graph.gen_backend import render_dao
from app.llm.graph.backend_validate import validate_backend
from app.llm.graph.frontend_validate import validate_frontend
from app.llm.graph.data_validate import validate_data


def _meta_map(contract: dict) -> dict:
    return {f["file_path"]: f for f in contract.get("bindings", {}).get("files", [])}


def _wrap(files: dict, meta: dict) -> dict:
    out = {}
    for path, content in files.items():
        m = meta.get(path, {})
        out[path] = {"file_path": path, "file_type": m.get("file_type", ""),
                     "layer": m.get("layer", ""), "wave": 0, "content": content,
                     "status": "ok", "status_log": []}
    return out


async def gen_backend_node(state: dict) -> dict:
    contract = state["contract"]
    meta = _meta_map(contract)
    guide = guides.load_guide_for_file_type("dao_impl")  # whole BackendGuide
    dao_path = contract["bindings"]["paths"]["dao_impl"]
    dtos = await gen_backend.gen_dtos(contract, guide)
    mapper = await gen_backend.gen_mapper(contract, guide, dtos)
    dao_src = render_dao(contract)
    service = await gen_backend.gen_service(contract, guide, dao_src, dtos)
    files = {**dtos, **mapper, dao_path: dao_src, **service}
    return {"files": _wrap(files, meta),
            "events": [{"type": "log", "line": f"[backend] generated {len(files)} files"}]}


async def gen_frontend_node(state: dict) -> dict:
    contract = state["contract"]
    meta = _meta_map(contract)
    guide = guides.load_guide_for_file_type("vue_page")  # whole FrontendGuide
    paths = contract["bindings"]["paths"]
    types = await gen_frontend.gen_types(contract, guide)
    types_src = next(iter(types.values()), "")
    api = await gen_frontend.gen_api(contract, guide, types_src)
    comp_files: dict = {}
    child_sources: dict = {}
    screen = contract["identity"]["class_name"]
    for comp in contract.get("frontend", {}).get("components", []):
        cf = await gen_frontend.gen_component(contract, guide, comp, types_src)
        comp_files.update(cf)
        vue_path = paths.get(f"vue_{comp.lower()}")
        if vue_path and vue_path in cf:
            child_sources[f"{screen}{comp}"] = cf[vue_path]
    index = await gen_frontend.gen_index(contract, guide, child_sources, types_src)
    files = {**types, **api, **comp_files, **index}
    return {"files": _wrap(files, meta),
            "events": [{"type": "log", "line": f"[frontend] generated {len(files)} files"}]}


async def gen_data_node(state: dict) -> dict:
    contract = state["contract"]
    meta = _meta_map(contract)
    guide = guides.load_guide_for_file_type("db_init_sql")  # whole DataGuide
    ddl = await gen_data.gen_ddl(contract, guide)
    seed = await gen_data.gen_seed(contract, guide)
    files = gen_data.assemble_sql(contract, ddl, seed)
    return {"files": _wrap(files, meta),
            "events": [{"type": "log", "line": "[data] generated db/init.sql"}]}


def validate_node(state: dict) -> dict:
    contract = state["contract"]
    files = state.get("files", {})
    issues = validate_backend(files, contract) + validate_frontend(files, contract)
    db = next((gf["content"] for gf in files.values()
               if gf.get("file_type") == "db_init_sql"), "")
    if db:
        issues = issues + validate_data(db, contract)
    return {"open_issues": issues,
            "events": [{"type": "log", "line": f"[validate] {len(issues)} issue(s)"}]}
```
- [ ] **Step 4: PASS (4).** **Step 5: commit** (`feat(codegen): LangGraph node wrappers for contract-first generators`).

---

## Task 2: New graph + sse_adapter wiring (go-live)

**Files:** Modify `backend/app/llm/graph/build.py` (replace `build_graph` body), `backend/app/llm/graph/sse_adapter.py` (node-name sets), `backend/tests/graph/test_build.py` (new topology).

- [ ] **Step 1:** Update `test_build.py` to the new topology (RED first). Replace its graph-structure assertions with:
```python
from app.llm.graph.build import build_graph

def test_build_graph_compiles_with_new_nodes():
    g = build_graph()
    names = set(g.get_graph().nodes)
    assert {"contract_resolve", "plan_and_bind", "gen_backend",
            "gen_frontend", "gen_data", "validate"} <= names
    # old nodes are no longer in the live graph
    assert "generate_file" not in names and "derive_contract" not in names
```
(Keep any non-topology tests in the file that still pass; remove/replace only those asserting the OLD nodes/edges.)
- [ ] **Step 2: run → FAIL** (old build_graph still has old nodes).
- [ ] **Step 3:** Rewrite `build_graph` in `build.py` to the linear contract-first chain:
```python
def build_graph(checkpointer=None):
    from app.llm.graph import contract_resolve, plan_and_bind, gen_nodes
    g = StateGraph(CodeGenState)
    g.add_node("contract_resolve", contract_resolve.contract_resolve)
    g.add_node("plan_and_bind", plan_and_bind.plan_and_bind)
    g.add_node("gen_backend", gen_nodes.gen_backend_node)
    g.add_node("gen_frontend", gen_nodes.gen_frontend_node)
    g.add_node("gen_data", gen_nodes.gen_data_node)
    g.add_node("validate", gen_nodes.validate_node)
    g.add_edge(START, "contract_resolve")
    g.add_edge("contract_resolve", "plan_and_bind")
    g.add_edge("plan_and_bind", "gen_backend")
    g.add_edge("gen_backend", "gen_frontend")
    g.add_edge("gen_frontend", "gen_data")
    g.add_edge("gen_data", "validate")
    g.add_edge("validate", END)
    return g.compile(checkpointer=checkpointer)
```
Leave the OLD functions (`_route_waves`, `_wave_gate`, `mybatis_fix`) and imports in build.py for now (dead; removed in 6c). If unused-import lint complains, that's fine for this phase. `make_checkpointer` unchanged.
- [ ] **Step 4:** Update `sse_adapter.py`:
  - `_PUBLIC_NODES = {"contract_resolve", "plan_and_bind", "gen_backend", "gen_frontend", "gen_data", "validate"}`
  - `_EMITTING_NODES = {"contract_resolve", "plan_and_bind", "gen_backend", "gen_frontend", "gen_data", "validate"}`
  (Leave `build_graph_input`/`graph_files_to_pydantic`/`stream_codegen` as-is — inputs and file conversion are unchanged.)
- [ ] **Step 5: run** `env $DUMMY_ENV pytest tests/graph/test_build.py -v` → PASS. Also `env $DUMMY_ENV pytest -m "not llm" -q` → confirm what breaks (expect only previously-old-topology tests; fix/replace any that asserted old graph wiring; old NODE unit tests should still pass since the functions remain).
- [ ] **Step 6: commit** (`feat(codegen): rewire build_graph to contract-first pipeline (go-live)`).

---

## Task 3: End-to-end graph integration test (scripted LLM)

**Files:** Create `backend/tests/graph/test_graph_e2e_scripted.py`.

- [ ] **Step 1:** Test that the whole new graph runs with scripted LLMs and produces files:
```python
import json
import pytest
from app.llm.graph.build import build_graph
from app.llm.graph import contract_resolve, gen_backend, gen_frontend, gen_data

pytestmark = pytest.mark.asyncio

_CONTRACT_JSON = json.dumps({
    "identity": {"module": "edu", "category": "pondg", "screen_id": "cpmsEduPondgLst",
                 "class_name": "CpmsEduPondgLst", "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm", "db_type": "varchar(100)"}]},
    "frontend": {"components": ["SearchForm", "DataTable"]},
})


class _Const:
    def __init__(self, reply): self.reply = reply
    async def complete(self, s, u, max_tokens=16384): return self.reply


async def test_new_graph_runs_end_to_end(monkeypatch):
    monkeypatch.setattr(contract_resolve, "gpt55_client", _Const(_CONTRACT_JSON))
    monkeypatch.setattr(gen_backend, "gpt55_client", _Const("package x;\nclass X {}"))
    monkeypatch.setattr(gen_frontend, "gpt55_client", _Const('<script setup lang="ts"></script>'))
    monkeypatch.setattr(gen_data, "gpt55_client", _Const("CREATE TABLE t();"))

    graph = build_graph()
    out = await graph.ainvoke({
        "spec_markdown": "교육 실적 조회", "confirmed_vue": "<template/>",
        "table_info": "cptb_edu_pondg: emp_nm varchar", "page_type": "list-detail",
        "files": {},
    })
    files = out["files"]
    layers = {gf["layer"] for gf in files.values()}
    assert {"backend", "frontend", "data"} <= layers
    ftypes = {gf["file_type"] for gf in files.values()}
    assert {"dto_request", "mapper_xml", "dao_impl", "service_impl",
            "vue_page", "vue_types", "db_init_sql"} <= ftypes
    assert isinstance(out.get("open_issues", []), list)
```
- [ ] **Step 2: run → PASS.** If `ainvoke` needs a config/recursion limit, pass `config={"recursion_limit": 50}`. If a generator errors on the constant reply, adjust the constant to a minimally-valid form (the goal is to prove the graph wiring runs + accumulates files, not to produce perfect code).
- [ ] **Step 3:** Full suite `env $DUMMY_ENV pytest -m "not llm" -q` → green. Commit (`test(codegen): end-to-end scripted-LLM run of the new graph`).

---

## Self-Review
- Spec coverage: spec §2 pipeline graph (contract_resolve→plan_and_bind→staged gen→validate) → Tasks 1-2; runnable + verified end-to-end (scripted) → Task 3. Ordering: backend→frontend→data(seed last)→validate (seed only needs bindings+contract.frontend.components, both available; placing gen_data after gen_frontend satisfies the spec's "seed after frontend"). CODEGEN_RULES deletion + old-node retirement = Phase 6c (explicitly deferred, de-risking). Compile-loops + real e2e = Phase 7.
- No deletions this phase → old node unit tests remain green; only `test_build.py` topology updated.
- Type consistency: wrappers produce `GeneratedFile` (file_type/layer from `bindings.files`); node return dicts use state channels (`files`/`events`/`open_issues`); `build_graph_input` keys match `contract_resolve` inputs; `graph_files_to_pydantic` reads file_path/file_type/content/layer (all present).
