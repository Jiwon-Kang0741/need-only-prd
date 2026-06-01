# Contract-Driven Generation (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** contract를 식별자(operations)+DTO 스키마(dtos)까지 정의하는 진실 출처로 승격하고, 생성 노드가 프롬프트로 그 식별자를 강제 주입받으며, mybatis_check가 contract 기준으로 검증·교정하게 한다.

**Architecture:** 신규 `naming.py`(순수 함수, namebook bare 규칙)로 식별자를 결정론 파생하고, planner 직후 `derive_contract` 노드가 contract에 operations/dtos를 병합한다. generate_file은 파일타입별 "REQUIRED IDENTIFIERS" 섹션을 주입(예방)하고, mybatis_check는 `contract` 옵션 인자로 contract 기준 검증·교정(교정) + DTO 필드 검증을 한다. contract=None이면 Phase 1 동작으로 폴백(하위호환).

**Tech Stack:** Python 3.12, LangGraph, pytest (식별자/파생/검증은 결정론 → LLM mock 불필요)

**참조 설계:** `docs/superpowers/specs/2026-06-02-contract-driven-generation-design.md`
**선행:** Phase 1 (`backend/app/llm/graph/mybatis_check.py`, `build.mybatis_fix`, `nodes.generate_file`)

**명명 규칙 (확정):** namebook 공식 = **bare 식별자**. selectList→`selectList`, selectOne→`select`, count→`selectCount`, insert→`insert`, update→`update`, delete→`delete`. 화면당 Mapper 1개라 화면코드 접두/접미 불필요.

---

## File Structure

### 신규 생성
- `backend/app/llm/graph/naming.py` — 식별자 파생 순수 함수 (op→bare id, dto_class, java_type, ops_for_screen_type)
- `backend/tests/graph/test_naming.py`
- `backend/tests/graph/test_derive_contract.py`
- `backend/tests/graph/test_contract_injection.py`

### 수정
- `backend/app/llm/graph/nodes.py` — `derive_contract` 노드 + `_contract_section_for` 헬퍼 + generate_file 프롬프트 주입
- `backend/app/llm/graph/build.py` — derive_contract 노드 등록 + 라우팅(planner→derive_contract→waves) + mybatis_fix에 contract 전달
- `backend/app/llm/graph/mybatis_check.py` — check_binding/autofix_binding에 contract 인자 + check_dto_fields/autofix_dto_fields 신규
- `backend/app/llm/graph/prompts.py` — GENERATOR_SYSTEM 보강
- `backend/app/llm/graph/sse_adapter.py` — _EMITTING_NODES에 derive_contract 추가
- `backend/tests/graph/test_mybatis_check.py` — contract 기준 테스트 추가 (기존 9개 하위호환 유지)

---

## Task 1: naming.py — 식별자 파생 순수 함수

**Files:**
- Create: `backend/app/llm/graph/naming.py`
- Test: `backend/tests/graph/test_naming.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_naming.py`:

```python
from app.llm.graph.naming import (
    statement_id, dao_method, mybatis_tag, dto_class, java_type, ops_for_screen_type,
)


def test_statement_id_bare():
    assert statement_id("selectList") == "selectList"
    assert statement_id("selectOne") == "select"
    assert statement_id("count") == "selectCount"
    assert statement_id("insert") == "insert"
    assert statement_id("update") == "update"
    assert statement_id("delete") == "delete"


def test_dao_method_equals_statement_id():
    for op in ("selectList", "selectOne", "count", "insert", "update", "delete"):
        assert dao_method(op) == statement_id(op)


def test_mybatis_tag():
    assert mybatis_tag("selectList") == "select"
    assert mybatis_tag("count") == "select"
    assert mybatis_tag("insert") == "insert"
    assert mybatis_tag("update") == "update"
    assert mybatis_tag("delete") == "delete"


def test_dto_class():
    assert dto_class("CpmsEduRsltLst", "request") == "CpmsEduRsltLstReqDto"
    assert dto_class("CpmsEduRsltLst", "response") == "CpmsEduRsltLstResDto"


def test_java_type_mapping():
    assert java_type("string") == "String"
    assert java_type("number") == "Integer"
    assert java_type("date") == "String"
    assert java_type("boolean") == "Boolean"
    assert java_type("unknown-xyz") == "String"  # default


def test_ops_for_screen_type():
    assert ops_for_screen_type("list") == ["selectList", "count"]
    ld = ops_for_screen_type("list-detail")
    assert "selectList" in ld and "selectOne" in ld and "insert" in ld and "delete" in ld
    # unknown type → safe default (list)
    assert ops_for_screen_type("mystery") == ["selectList", "count"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_naming.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.naming'`

- [ ] **Step 3: Write naming.py**

`backend/app/llm/graph/naming.py`:

```python
"""Deterministic CPMS identifier derivation (namebook rules, bare statement ids).

Single source of truth for statement ids, DAO method names, DTO class names and
Java types. Because identifiers are derived by code (not the LLM), every file that
references the same contract uses identical names — mismatches become impossible.
"""

from __future__ import annotations

# op → (statement_id / dao_method, mybatis tag). Bare per namebook (one mapper/screen).
_OP_TABLE: dict[str, tuple[str, str]] = {
    "selectList": ("selectList", "select"),
    "selectOne": ("select", "select"),
    "count": ("selectCount", "select"),
    "insert": ("insert", "insert"),
    "update": ("update", "update"),
    "delete": ("delete", "delete"),
}

_SCREEN_OPS: dict[str, list[str]] = {
    "list": ["selectList", "count"],
    "list-detail": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "edit": ["selectOne", "insert", "update", "delete"],
    "tab-detail": ["selectList", "count", "selectOne", "insert", "update", "delete"],
}

_TYPE_MAP: dict[str, str] = {
    "string": "String",
    "text": "String",
    "number": "Integer",
    "int": "Integer",
    "long": "Long",
    "decimal": "Double",
    "boolean": "Boolean",
    "date": "String",
    "datetime": "String",
}


def statement_id(op: str) -> str:
    entry = _OP_TABLE.get(op)
    return entry[0] if entry else op


def dao_method(op: str) -> str:
    return statement_id(op)


def mybatis_tag(op: str) -> str:
    entry = _OP_TABLE.get(op)
    return entry[1] if entry else "select"


def dto_class(screen_code: str, kind: str) -> str:
    suffix = "ReqDto" if kind == "request" else "ResDto"
    return f"{screen_code}{suffix}"


def java_type(contract_type: str) -> str:
    return _TYPE_MAP.get((contract_type or "").lower(), "String")


def ops_for_screen_type(screen_type: str) -> list[str]:
    return list(_SCREEN_OPS.get(screen_type, _SCREEN_OPS["list"]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_naming.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/naming.py tests/graph/test_naming.py
git commit -m "feat(codegen): add naming.py — deterministic identifier derivation (bare namebook)"
```

---

## Task 2: derive_contract 노드

**Files:**
- Modify: `backend/app/llm/graph/nodes.py` (append node + helpers)
- Test: `backend/tests/graph/test_derive_contract.py`

설계 참조: planner 직후, 코드만으로 contract에 operations/dtos 병합. op 세트 = 화면 type 고정세트 ∪ api_signatures 보정. planner 파일목록에 없는 op 스킵. 파생 실패 시 빈 채 진행.

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_derive_contract.py`:

```python
import pytest

from app.llm.graph import nodes

pytestmark = pytest.mark.asyncio

_CONTRACT = {
    "screen": {"id": "CPMSEDURSLTLST", "name": "교육이수현황", "type": "list-detail"},
    "fields": [
        {"vue_field": "employeeName", "db_column": "EMP_NM", "type": "string"},
        {"vue_field": "score", "db_column": "SCORE", "type": "number"},
    ],
    "api_signatures": [],
}
_PLAN = {"files": [
    {"file_path": "x/CpmsEduRsltLstReqDto.java", "file_type": "dto_request"},
    {"file_path": "x/CpmsEduRsltLstResDto.java", "file_type": "dto_response"},
    {"file_path": "x/CpmsEduRsltLstDaoImpl.java", "file_type": "dao_impl"},
    {"file_path": "x/CpmsEduRsltLstMapper.xml", "file_type": "mapper_xml"},
    {"file_path": "x/CpmsEduRsltLstServiceImpl.java", "file_type": "service_impl"},
]}


async def test_derive_contract_builds_operations():
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": _PLAN})
    ops = out["contract"]["operations"]
    ids = {o["statement_id"] for o in ops}
    # list-detail standard set, bare ids
    assert {"selectList", "selectCount", "select", "insert", "update", "delete"} <= ids
    one = next(o for o in ops if o["op"] == "selectList")
    assert one["dao_method"] == "selectList"
    assert one["mybatis_tag"] == "select"
    assert one["param_type"] == "CpmsEduRsltLstReqDto"


async def test_derive_contract_builds_dtos():
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": _PLAN})
    dtos = {d["name"]: d for d in out["contract"]["dtos"]}
    assert "CpmsEduRsltLstReqDto" in dtos and "CpmsEduRsltLstResDto" in dtos
    res_fields = {f["name"]: f for f in dtos["CpmsEduRsltLstResDto"]["fields"]}
    assert res_fields["employeeName"]["java_type"] == "String"
    assert res_fields["score"]["java_type"] == "Integer"


async def test_derive_contract_skips_op_without_dao_file():
    # plan has no dao_impl/mapper → dao/mapper-bound ops are skipped
    plan = {"files": [{"file_path": "x/CpmsEduRsltLstResDto.java", "file_type": "dto_response"}]}
    out = await nodes.derive_contract({"contract": _CONTRACT, "plan": plan})
    assert out["contract"]["operations"] == []


async def test_derive_contract_empty_fields_no_crash():
    contract = {"screen": {"id": "X", "type": "list"}, "fields": [], "api_signatures": []}
    out = await nodes.derive_contract({"contract": contract, "plan": _PLAN})
    # operations may exist but dtos have empty fields; must not raise
    assert "dtos" in out["contract"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_derive_contract.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'derive_contract'`

- [ ] **Step 3: Implement (append to nodes.py)**

nodes.py 상단 import에 추가:

```python
from app.llm.graph import naming
```

파일 끝에 추가:

```python
def _pascal_screen_code(screen_id: str) -> str:
    """'CPMSEDURSLTLST' → 'CpmsEduRsltLst' is not reversible; use the id as-is if it
    already looks PascalCase, else title-case the lowercased id. The DTO/file names
    in the plan are the authority — extract the screen code from a planned DTO."""
    return screen_id  # placeholder; overridden below by plan-derived code


def _screen_code_from_plan(plan: dict, fallback: str) -> str:
    """Derive the ScreenCode (e.g. 'CpmsEduRsltLst') from a planned DTO class name."""
    for f in plan.get("files", []):
        name = f["file_path"].split("/")[-1]
        for suffix in ("ReqDto.java", "ResDto.java", "DaoImpl.java", "Mapper.xml"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
    return fallback


# op → required file_type for that op to be generated (skip op if file absent)
_OP_REQUIRES = {
    "selectList": "dao_impl", "selectOne": "dao_impl", "count": "dao_impl",
    "insert": "dao_impl", "update": "dao_impl", "delete": "dao_impl",
}


def _api_signature_ops(api_signatures: list) -> list[str]:
    """Map api_signatures to standard ops (best-effort). POST .../list → selectList etc."""
    ops: list[str] = []
    for sig in api_signatures or []:
        path = (sig.get("path") or "").lower()
        if "count" in path:
            ops.append("count")
        elif "list" in path:
            ops.append("selectList")
        elif "save" in path or "insert" in path:
            ops.append("insert")
        elif "update" in path:
            ops.append("update")
        elif "delete" in path:
            ops.append("delete")
    return ops


async def derive_contract(state: dict) -> dict:
    """Augment contract with code-level identifiers (operations + dtos). Code only."""
    contract = dict(state.get("contract") or {})
    plan = state.get("plan") or {}
    screen = contract.get("screen") or {}
    try:
        screen_code = _screen_code_from_plan(plan, screen.get("id", "Screen"))
        req_dto = naming.dto_class(screen_code, "request")
        res_dto = naming.dto_class(screen_code, "response")

        planned_types = {f["file_type"] for f in plan.get("files", [])}
        ops = naming.ops_for_screen_type(screen.get("type", "list"))
        for extra in _api_signature_ops(contract.get("api_signatures", [])):
            if extra not in ops:
                ops.append(extra)

        operations = []
        for op in ops:
            required = _OP_REQUIRES.get(op)
            if required and required not in planned_types:
                continue  # planner did not plan this file → skip op
            is_list = op == "selectList"
            param = req_dto
            ret = (f"List<{res_dto}>" if is_list
                   else "int" if op == "count"
                   else res_dto)
            operations.append({
                "op": op,
                "statement_id": naming.statement_id(op),
                "dao_method": naming.dao_method(op),
                "param_type": param,
                "return_type": ret,
                "mybatis_tag": naming.mybatis_tag(op),
            })

        def _fields(kind):
            return [{"name": f["vue_field"], "java_type": naming.java_type(f.get("type", "string")),
                     "db_column": f.get("db_column", "")}
                    for f in contract.get("fields", [])]

        dtos = [
            {"name": req_dto, "kind": "request", "fields": _fields("request")},
            {"name": res_dto, "kind": "response", "fields": _fields("response")},
        ]
        contract["operations"] = operations
        contract["dtos"] = dtos
    except Exception as e:
        return {"events": [{"type": "log", "line": f"[CONTRACT] derive failed: {e}"}]}

    return {"contract": contract,
            "events": [{"type": "log",
                        "line": f"[CONTRACT] derived {len(contract.get('operations', []))} ops, "
                                f"{len(contract.get('dtos', []))} dtos"}]}
```

(주: `_pascal_screen_code`는 사용하지 않으므로 추가하지 말 것 — 위 코드는 `_screen_code_from_plan`만 사용. 플랜 작성 편의상 남긴 설명이며, 실제로는 `_screen_code_from_plan`만 구현한다.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_derive_contract.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/nodes.py tests/graph/test_derive_contract.py
git commit -m "feat(codegen): add derive_contract node (operations + dtos from contract)"
```

---

## Task 3: 그래프 라우팅 — planner → derive_contract → waves

**Files:**
- Modify: `backend/app/llm/graph/build.py`
- Modify: `backend/app/llm/graph/sse_adapter.py`
- Test: `backend/tests/graph/test_build.py::test_build_graph_compiles` (기존)

- [ ] **Step 1: build.py에 노드 등록 + 라우팅 변경**

`build_graph` 안에서 노드 등록 추가 (planner 등록 근처):

```python
    g.add_node("derive_contract", nodes.derive_contract)
```

엣지 변경: 기존 `planner`의 conditional edge를 derive_contract 경유로. 기존:
```python
    g.add_edge("contract_extract", "planner")
    g.add_conditional_edges("planner", _route_waves,
                            ["generate_file", "wave_gate", "mybatis_fix"])
```
변경:
```python
    g.add_edge("contract_extract", "planner")
    g.add_edge("planner", "derive_contract")
    g.add_conditional_edges("derive_contract", _route_waves,
                            ["generate_file", "wave_gate", "mybatis_fix"])
```

(주: `_route_waves`는 current_wave를 보는데, planner가 `current_wave=1`을 설정하고 derive_contract는 contract만 바꾸므로 current_wave가 보존되어 라우팅 정상. derive_contract가 current_wave를 안 건드림.)

- [ ] **Step 2: sse_adapter.py _EMITTING_NODES에 추가**

`_EMITTING_NODES`에 `"derive_contract"` 추가:

```python
_EMITTING_NODES = {"contract_extract", "planner", "derive_contract", "generate_file",
                   "wave_gate", "mybatis_fix", "reviewer"}
```

- [ ] **Step 3: 그래프 컴파일 확인**

Run: `cd backend && .venv/bin/python -c "from app.llm.graph import build; build.build_graph(checkpointer=None); print('ok')"`
Expected: `ok`

- [ ] **Step 4: 오프라인 compile 테스트**

Run: `cd backend && .venv/bin/pytest tests/graph/test_build.py::test_build_graph_compiles -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/build.py app/llm/graph/sse_adapter.py
git commit -m "feat(codegen): route planner → derive_contract → waves"
```

---

## Task 4: generate_file 프롬프트 주입 (_contract_section_for)

**Files:**
- Modify: `backend/app/llm/graph/nodes.py`
- Modify: `backend/app/llm/graph/prompts.py`
- Test: `backend/tests/graph/test_contract_injection.py`

설계 참조: 파일타입별로 operations/dtos에서 관련 식별자만 "REQUIRED IDENTIFIERS" 섹션으로 포맷. operations 없으면 빈 문자열(기존 동작).

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_contract_injection.py`:

```python
from app.llm.graph.nodes import _contract_section_for

_CONTRACT = {
    "operations": [
        {"op": "selectList", "statement_id": "selectList", "dao_method": "selectList",
         "param_type": "FooReqDto", "return_type": "List<FooResDto>", "mybatis_tag": "select"},
        {"op": "insert", "statement_id": "insert", "dao_method": "insert",
         "param_type": "FooReqDto", "return_type": "int", "mybatis_tag": "insert"},
    ],
    "dtos": [
        {"name": "FooReqDto", "kind": "request",
         "fields": [{"name": "employeeName", "java_type": "String"}]},
        {"name": "FooResDto", "kind": "response",
         "fields": [{"name": "score", "java_type": "Integer"}]},
    ],
}


def test_section_for_dao_lists_operations():
    s = _contract_section_for("dao_impl", _CONTRACT)
    assert "selectList" in s and "insert" in s
    assert "FooReqDto" in s


def test_section_for_mapper_lists_statement_ids_and_tags():
    s = _contract_section_for("mapper_xml", _CONTRACT)
    assert "selectList" in s and "select" in s  # tag


def test_section_for_dto_request_lists_only_that_dto_fields():
    s = _contract_section_for("dto_request", _CONTRACT)
    assert "employeeName" in s and "String" in s
    assert "score" not in s  # response field not in request section


def test_section_for_unrelated_filetype_empty():
    assert _contract_section_for("db_init_sql", _CONTRACT) == ""
    assert _contract_section_for("vue_page", _CONTRACT) == ""


def test_section_for_no_operations_empty():
    assert _contract_section_for("dao_impl", {}) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_contract_injection.py -q`
Expected: FAIL — `ImportError: cannot import name '_contract_section_for'`

- [ ] **Step 3: Implement _contract_section_for in nodes.py**

nodes.py에 추가 (generate_file 위):

```python
def _contract_section_for(file_type: str, contract: dict) -> str:
    """Build a 'REQUIRED IDENTIFIERS' prompt section for a file type. '' if N/A."""
    ops = (contract or {}).get("operations") or []
    dtos = {d["name"]: d for d in (contract or {}).get("dtos") or []}

    def _op_lines():
        return "\n".join(
            f"- {o['op']}: dao_method={o['dao_method']}, statement_id={o['statement_id']}, "
            f"param={o['param_type']}, return={o['return_type']}, tag={o['mybatis_tag']}"
            for o in ops)

    def _dto_block(name):
        d = dtos.get(name)
        if not d:
            return ""
        flds = "\n".join(f"  - {f['name']}: {f['java_type']}" for f in d["fields"])
        return f"{name} fields:\n{flds}"

    if file_type == "dao_impl":
        if not ops:
            return ""
        return "DAO methods (implement EXACTLY):\n" + _op_lines()
    if file_type == "mapper_xml":
        if not ops:
            return ""
        return ("Mapper statements (use these EXACT ids/tags; namespace = DaoImpl FQCN):\n"
                + _op_lines())
    if file_type == "service_impl":
        if not ops:
            return ""
        return "Call these DAO methods:\n" + _op_lines()
    if file_type == "dto_request":
        return _dto_block(next((n for n in dtos if n.endswith("ReqDto")), ""))
    if file_type == "dto_response":
        return _dto_block(next((n for n in dtos if n.endswith("ResDto")), ""))
    if file_type == "vue_types":
        blocks = [_dto_block(n) for n in dtos]
        return "\n\n".join(b for b in blocks if b)
    return ""
```

generate_file 안의 base_user 조립을 수정 (CONTRACT 섹션 다음에 REQUIRED IDENTIFIERS 삽입):

기존:
```python
    base_user = (
        f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n\n"
        f"=== GUIDE ===\n{guide}\n"
        f"{_dep_context(state, spec)}\n\n"
        f"Generate file: {spec['file_path']} (type={spec['file_type']}, "
        f"class={spec.get('class_name', '')})\n{spec.get('description', '')}"
    )
```
변경:
```python
    req_ids = _contract_section_for(spec["file_type"], state["contract"])
    base_user = (
        f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n\n"
        + (f"=== REQUIRED IDENTIFIERS (use EXACTLY, do not rename) ===\n{req_ids}\n\n"
           if req_ids else "")
        + f"=== GUIDE ===\n{guide}\n"
        + f"{_dep_context(state, spec)}\n\n"
        + f"Generate file: {spec['file_path']} (type={spec['file_type']}, "
        + f"class={spec.get('class_name', '')})\n{spec.get('description', '')}"
    )
```

- [ ] **Step 4: prompts.py GENERATOR_SYSTEM 보강**

`GENERATOR_SYSTEM` 끝에 한 문장 추가:

기존 끝: `...Output ONLY the file content, no markdown fences, no explanation."""`
변경:
```python
GENERATOR_SYSTEM = """\
You are a senior engineer generating ONE CPMS file. Follow the provided guide \
sections exactly. Use the contract as the source of truth for field names and \
types. When REQUIRED IDENTIFIERS are given, use those exact statement ids, \
method names and DTO field names — never invent or rename them. \
Output ONLY the file content, no markdown fences, no explanation."""
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_contract_injection.py -q`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/llm/graph/nodes.py app/llm/graph/prompts.py tests/graph/test_contract_injection.py
git commit -m "feat(codegen): inject REQUIRED IDENTIFIERS into generator prompts (prevention)"
```

---

## Task 5: mybatis_check — contract 기준 바인딩 교정

**Files:**
- Modify: `backend/app/llm/graph/mybatis_check.py`
- Test: `backend/tests/graph/test_mybatis_check.py` (append, 기존 9개 유지)

설계 참조: check_binding/autofix_binding에 contract 인자 추가. contract.operations 있으면 그 statement_id 집합이 진실 — DAO·Mapper 둘 다 거기 맞춤. bare id라 op→id 정확 매핑 가능. contract=None이면 Phase 1 동작(하위호환).

- [ ] **Step 1: Append the failing test**

`backend/tests/graph/test_mybatis_check.py`에 추가:

```python
_CONTRACT_OPS = {
    "operations": [
        {"op": "selectList", "statement_id": "selectList", "dao_method": "selectList",
         "mybatis_tag": "select"},
        {"op": "count", "statement_id": "selectCount", "dao_method": "selectCount",
         "mybatis_tag": "select"},
    ]
}


def test_check_binding_backward_compatible_without_contract():
    # Phase 1 behavior unchanged when contract=None (DAO super call is truth)
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", _DAO),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    issues = check_binding(files)  # no contract arg
    assert any("namespace" in i["issue"].lower() for i in issues)


def test_autofix_with_contract_fixes_both_dao_and_mapper():
    # DAO calls "selectFooList", Mapper has "selFooLst" — BOTH wrong vs contract "selectList"
    dao = """package p; public class FooDaoImpl extends B {
        public int a(X q){ return super.selectList("selectFooList", q); }
        public int c(X q){ Integer n=super.selectOne("cnt", q); return n; } }"""
    mapper = ('<mapper namespace="p.FooDaoImpl">'
              '<select id="selFooLst">S</select>'
              '<select id="cntStmt">C</select></mapper>')
    files = {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", dao),
        "b/FooMapper.xml": _gf("b/FooMapper.xml", "mapper_xml", mapper),
    }
    fixed, logs = autofix_binding(files, _CONTRACT_OPS)
    dao_c = fixed["a/FooDaoImpl.java"]["content"]
    mapper_c = fixed["b/FooMapper.xml"]["content"]
    # both DAO call and Mapper id aligned to contract bare ids
    assert '"selectList"' in dao_c
    assert 'id="selectList"' in mapper_c
    after = [i for i in check_binding(files, _CONTRACT_OPS)]  # note: re-derive below
```

(주: 마지막 줄은 fixed 기준으로 재검증해야 한다 — Step 3 구현 후 아래로 교체.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -k contract -q`
Expected: FAIL — `TypeError: check_binding() takes 1 positional argument but 2 were given` 또는 autofix 미반영

- [ ] **Step 3: Implement contract-aware check/autofix**

`mybatis_check.py`의 `check_binding` 시그니처/로직 변경:

```python
def _contract_ids(contract) -> set[str]:
    ops = (contract or {}).get("operations") or []
    return {o["statement_id"] for o in ops}


def check_binding(files: dict, contract: dict | None = None) -> list[dict]:
    """Detect namespace/id mismatches. If contract has operations, that id set is
    the source of truth; otherwise the DAO super(...) calls are (Phase 1)."""
    pairs, issues = match_pairs(files)
    issues = list(issues)
    truth_ids = _contract_ids(contract)

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])

        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            issues.append({"file_path": mapper_gf["file_path"],
                           "issue": (f"Mapper namespace '{mapper['namespace']}' != DaoImpl FQCN "
                                     f"'{dao['expected_namespace']}'"), "severity": "error"})

        if truth_ids:
            # contract is truth: both DAO and Mapper ids must be within truth_ids
            for sid in sorted(dao["statement_ids"] - truth_ids):
                issues.append({"file_path": dao_gf["file_path"],
                               "issue": f"DAO statement '{sid}' is not in contract operations",
                               "severity": "error"})
            for sid in sorted(mapper["ids"] - truth_ids):
                issues.append({"file_path": mapper_gf["file_path"],
                               "issue": f"Mapper statement '{sid}' is not in contract operations",
                               "severity": "error"})
            # also: every contract id should be present in both
            for sid in sorted(truth_ids - dao["statement_ids"]):
                issues.append({"file_path": dao_gf["file_path"],
                               "issue": f"DAO missing contract statement '{sid}'",
                               "severity": "error"})
            for sid in sorted(truth_ids - mapper["ids"]):
                issues.append({"file_path": mapper_gf["file_path"],
                               "issue": f"Mapper missing contract statement '{sid}'",
                               "severity": "error"})
        else:
            # Phase 1: DAO super calls are truth
            for sid in sorted(dao["statement_ids"] - mapper["ids"]):
                issues.append({"file_path": mapper_gf["file_path"],
                               "issue": (f"DAO calls statement '{sid}' but Mapper has no matching "
                                         f"<statement id=\"{sid}\">"), "severity": "error"})
            for sid in sorted(mapper["ids"] - dao["statement_ids"]):
                issues.append({"file_path": mapper_gf["file_path"],
                               "issue": f"Mapper statement '{sid}' is not called by any DAO method",
                               "severity": "warning"})
    return issues
```

`autofix_binding` 시그니처/로직 변경 (contract 있으면 그 id로 양쪽 rename):

```python
def autofix_binding(files: dict, contract: dict | None = None) -> tuple[dict, list[str]]:
    """Apply deterministic fixes. With contract, both DAO and Mapper ids are aligned
    to contract bare ids; without, DAO super calls are truth (Phase 1)."""
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs: list[str] = []
    pairs, _ = match_pairs(fixed)
    truth_ids = sorted(_contract_ids(contract))

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])
        dao_content = dao_gf["content"]
        mapper_content = mapper_gf["content"]

        # namespace → DaoImpl FQCN
        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            mapper_content = re.sub(
                r'(<mapper\b[^>]*\bnamespace\s*=\s*")[^"]+(")',
                lambda m: m.group(1) + dao["expected_namespace"] + m.group(2),
                mapper_content, count=1)
            logs.append(f"{mapper_gf['file_path']}: namespace → {dao['expected_namespace']}")

        if truth_ids:
            # align Mapper ids to nearest contract id (greedy), then DAO calls likewise
            mapper_content, mlogs = _align_ids_to_truth(
                mapper_content, sorted(mapper["ids"]), truth_ids,
                rf'(\bid\s*=\s*"){{have}}(")', mapper_gf["file_path"])
            logs += mlogs
            dao_content, dlogs = _align_ids_to_truth(
                dao_content, sorted(dao["statement_ids"]), truth_ids,
                r'(super\s*\.\s*\w+\s*\(\s*"){have}(")', dao_gf["file_path"])
            logs += dlogs
        else:
            # Phase 1: align Mapper to DAO super-call ids
            missing = sorted(set(dao["statement_ids"]) - set(mapper["ids"]))
            unused = sorted(set(mapper["ids"]) - set(dao["statement_ids"]))
            used_have: set[str] = set()
            for want in missing:
                best, best_d = None, 1.0
                for have in unused:
                    if have in used_have:
                        continue
                    d = _normalized_distance(want, have)
                    if d < best_d:
                        best, best_d = have, d
                if best is not None and best_d <= _EDIT_DISTANCE_THRESHOLD:
                    used_have.add(best)
                    mapper_content = re.sub(
                        rf'(\bid\s*=\s*"){re.escape(best)}(")',
                        lambda m, w=want: m.group(1) + w + m.group(2),
                        mapper_content, count=1)
                    logs.append(f"{mapper_gf['file_path']}: statement id '{best}' → '{want}'")

        fixed[dao_gf["file_path"]] = {**dao_gf, "content": dao_content}
        fixed[mapper_gf["file_path"]] = {**mapper_gf, "content": mapper_content}

    return fixed, logs


def _align_ids_to_truth(content, current_ids, truth_ids, pattern_tmpl, file_path):
    """Rename each current id that's not in truth_ids to its nearest truth id
    (≤ threshold, 1:1 greedy). pattern_tmpl uses {have} placeholder for the id."""
    logs = []
    wrong = [i for i in current_ids if i not in truth_ids]
    available = [t for t in truth_ids if t not in current_ids]
    used = set()
    for have in wrong:
        best, best_d = None, 1.0
        for want in available:
            if want in used:
                continue
            d = _normalized_distance(have, want)
            if d < best_d:
                best, best_d = want, d
        if best is not None and best_d <= _EDIT_DISTANCE_THRESHOLD:
            used.add(best)
            pat = pattern_tmpl.replace("{have}", re.escape(have))
            content = re.sub(pat, lambda m, w=best: m.group(1) + w + m.group(2),
                             content, count=1)
            logs.append(f"{file_path}: id '{have}' → '{best}' (contract)")
    return content, logs
```

- [ ] **Step 3b: 테스트 마지막 줄 교체 (fixed 기준 재검증)**

Step 1 테스트의 마지막 줄을 다음으로 교체:

```python
    after_errors = [i for i in check_binding(fixed, _CONTRACT_OPS)
                    if i.get("severity") != "warning"]
    assert after_errors == []
```

- [ ] **Step 4: Run test to verify it passes (하위호환 포함)**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: PASS (기존 9 + 신규 2 = 11). **기존 9개 그대로 통과 = 하위호환 확인.**

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/mybatis_check.py tests/graph/test_mybatis_check.py
git commit -m "feat(codegen): mybatis_check contract-aware (truth=contract, fixes DAO too)"
```

---

## Task 6: DTO 필드 검증 + autofix

**Files:**
- Modify: `backend/app/llm/graph/mybatis_check.py` (append)
- Test: `backend/tests/graph/test_mybatis_check.py` (append)

설계 참조: contract.dtos[].fields 기준, 생성 DTO에 누락 필드 → autofix로 `private <java_type> <name>;` 추가. java_type 없으면 스킵+경고.

- [ ] **Step 1: Append the failing test**

```python
from app.llm.graph.mybatis_check import check_dto_fields, autofix_dto_fields

_CONTRACT_DTOS = {
    "dtos": [
        {"name": "FooResDto", "kind": "response",
         "fields": [{"name": "employeeName", "java_type": "String"},
                    {"name": "score", "java_type": "Integer"}]},
    ]
}


def test_check_dto_fields_flags_missing():
    files = {"a/FooResDto.java": _gf("a/FooResDto.java", "dto_response",
             "public class FooResDto { private String employeeName; }")}
    issues = check_dto_fields(files, _CONTRACT_DTOS)
    assert any("score" in i["issue"] for i in issues)


def test_autofix_dto_fields_adds_missing():
    files = {"a/FooResDto.java": _gf("a/FooResDto.java", "dto_response",
             "public class FooResDto {\n    private String employeeName;\n}")}
    fixed, logs = autofix_dto_fields(files, _CONTRACT_DTOS)
    content = fixed["a/FooResDto.java"]["content"]
    assert "private Integer score;" in content
    assert check_dto_fields(fixed, _CONTRACT_DTOS) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -k dto_fields -q`
Expected: FAIL — `ImportError: cannot import name 'check_dto_fields'`

- [ ] **Step 3: Implement (append to mybatis_check.py)**

```python
_FIELD_DECL_RE = re.compile(r'\bprivate\s+\S[\w<>,.\[\]]*\s+(\w+)\s*(?:=[^;]*)?;')


def _dto_files_by_class(files: dict) -> dict[str, dict]:
    out = {}
    for gf in files.values():
        if gf["file_path"].endswith(".java") and "Dto" in gf["file_path"]:
            cls = gf["file_path"].split("/")[-1].replace(".java", "")
            out[cls] = gf
    return out


def check_dto_fields(files: dict, contract: dict | None = None) -> list[dict]:
    """Flag contract-required DTO fields missing from the generated DTO."""
    dtos = (contract or {}).get("dtos") or []
    by_class = _dto_files_by_class(files)
    issues = []
    for d in dtos:
        gf = by_class.get(d["name"])
        if not gf:
            continue
        present = set(_FIELD_DECL_RE.findall(gf["content"]))
        for f in d["fields"]:
            if f["name"] not in present:
                issues.append({"file_path": gf["file_path"],
                               "issue": f"DTO {d['name']} missing contract field '{f['name']}'",
                               "severity": "error"})
    return issues


def autofix_dto_fields(files: dict, contract: dict | None = None) -> tuple[dict, list[str]]:
    """Insert missing contract fields as `private <java_type> <name>;` before the
    final closing brace of the class."""
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs = []
    dtos = (contract or {}).get("dtos") or []
    by_class = _dto_files_by_class(fixed)
    for d in dtos:
        gf = by_class.get(d["name"])
        if not gf:
            continue
        content = gf["content"]
        present = set(_FIELD_DECL_RE.findall(content))
        additions = []
        for f in d["fields"]:
            if f["name"] in present:
                continue
            jt = f.get("java_type")
            if not jt:
                logs.append(f"{gf['file_path']}: skip field '{f['name']}' (no java_type)")
                continue
            additions.append(f"    private {jt} {f['name']};")
        if additions:
            idx = content.rfind("}")
            if idx != -1:
                content = content[:idx] + "\n".join(additions) + "\n" + content[idx:]
                logs.append(f"{gf['file_path']}: added {len(additions)} contract field(s)")
                fixed[gf["file_path"]] = {**gf, "content": content}
    return fixed, logs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: PASS (11 + 2 = 13)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/mybatis_check.py tests/graph/test_mybatis_check.py
git commit -m "feat(codegen): add contract DTO-field check + autofix (cross_check promotion)"
```

---

## Task 7: mybatis_fix 노드 — contract 전달

**Files:**
- Modify: `backend/app/llm/graph/build.py`
- Test: `backend/tests/graph/test_mybatis_node.py` (append)

- [ ] **Step 1: Append the failing test**

`backend/tests/graph/test_mybatis_node.py`에 추가:

```python
def test_mybatis_fix_uses_contract_when_present():
    dao = """package p; public class FooDaoImpl extends B {
        public int a(X q){ return super.selectList("selFooLst", q); } }"""
    mapper = '<mapper namespace="p.FooDaoImpl"><select id="selFooLst">S</select></mapper>'
    contract = {"operations": [
        {"op": "selectList", "statement_id": "selectList", "dao_method": "selectList",
         "mybatis_tag": "select"}]}
    state = {"files": {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", dao),
        "b/FooMapper.xml": _gf("b/FooMapper.xml", "mapper_xml", mapper),
    }, "contract": contract}
    out = mybatis_fix(state)
    dao_c = out["files"]["a/FooDaoImpl.java"]["content"]
    mapper_c = out["files"]["b/FooMapper.xml"]["content"]
    assert '"selectList"' in dao_c       # DAO aligned to contract
    assert 'id="selectList"' in mapper_c  # Mapper aligned to contract
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_node.py -k contract -q`
Expected: FAIL — DAO not aligned (mybatis_fix doesn't pass contract yet)

- [ ] **Step 3: Update mybatis_fix in build.py**

`mybatis_fix` 함수를 교체:

```python
def mybatis_fix(state: dict) -> dict:
    """Deterministic DAO↔Mapper + DTO-field autofix before the reviewer (no LLM).

    Uses contract.operations/dtos as the source of truth when present; otherwise
    falls back to Phase 1 behavior (DAO super calls).
    """
    files = dict(state.get("files", {}))
    contract = state.get("contract")
    try:
        fixed_files, fix_logs = autofix_binding(files, contract)
        if contract:
            fixed_files, dto_logs = autofix_dto_fields(fixed_files, contract)
            fix_logs = fix_logs + dto_logs
        remaining = check_binding(fixed_files, contract)
        if contract:
            remaining = remaining + check_dto_fields(fixed_files, contract)
    except Exception as e:
        return {"events": [{"type": "log", "line": f"[MYBATIS] error: {e}"}]}
    events = [{"type": "log", "line": f"[MYBATIS-FIX] {log}"} for log in fix_logs]
    errors = [i for i in remaining if i.get("severity") != "warning"]
    if errors:
        events.append({"type": "log",
                       "line": f"[MYBATIS] {len(errors)} binding issue(s) left for reviewer"})
    return {"files": fixed_files, "events": events, "open_issues": remaining}
```

build.py 상단 import에 추가:

```python
from app.llm.graph.mybatis_check import (
    autofix_binding, check_binding, autofix_dto_fields, check_dto_fields,
)
```
(기존 `from app.llm.graph.mybatis_check import autofix_binding, check_binding` 줄을 위로 교체.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_node.py -q`
Expected: PASS (기존 2 + 신규 1 = 3)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/build.py tests/graph/test_mybatis_node.py
git commit -m "feat(codegen): mybatis_fix passes contract (truth) + DTO-field autofix"
```

---

## Task 8: 회귀 + 실 LLM e2e

**Files:** (없음 — 검증만)

- [ ] **Step 1: graph 비-LLM 전체 (하위호환 포함)**

Run: `cd backend && .venv/bin/pytest tests/graph/ -m "not llm" -q`
Expected: PASS — Phase 1 mybatis 9개 + 신규(naming 6 / derive 4 / injection 5 / mybatis contract 4 / node 1) 전부. 기존 graph 테스트 무손상.

- [ ] **Step 2: 그래프 빌드 + import**

Run: `cd backend && .venv/bin/python -c "from app.llm.graph import build, naming, nodes, mybatis_check; build.build_graph(checkpointer=None); print('ok')"`
Expected: `ok`

- [ ] **Step 3: outputs/code 회귀 (contract 없이 Phase 1 경로 여전히 작동)**

Run:
```bash
cd backend && .venv/bin/python -c "
from app.llm.graph.mybatis_check import check_binding, autofix_binding
import pathlib
b=pathlib.Path('../outputs/code')
dao=(b/'backend/src/main/java/com/example/cpms/dao/CpmsEduRsltLstDaoImpl.java').read_text()
mp=(b/'backend/src/main/resources/mapper/cpms/CpmsEduRsltLstMapper.xml').read_text()
f={'d/CpmsEduRsltLstDaoImpl.java':{'file_path':'d/CpmsEduRsltLstDaoImpl.java','file_type':'dao_impl','layer':'backend','wave':2,'status':'ok','status_log':[],'content':dao},
   'm/CpmsEduRsltLstMapper.xml':{'file_path':'m/CpmsEduRsltLstMapper.xml','file_type':'mapper_xml','layer':'backend','wave':2,'status':'ok','status_log':[],'content':mp}}
fx,_=autofix_binding(f)  # no contract → Phase 1
err=[i for i in check_binding(fx) if i.get('severity')!='warning']
print('Phase1 path errors after fix:', len(err))
"
```
Expected: `Phase1 path errors after fix: 0` (하위호환 — contract 없이도 여전히 작동)

- [ ] **Step 4: 실 LLM e2e (derive_contract 삽입 후 정상 종료)**

Run: `cd backend && .venv/bin/pytest tests/graph/test_build.py::test_end_to_end_real_llm -q`
Expected: PASS (키 있을 때; 없으면 skip). derive_contract 노드 삽입 + REQUIRED IDENTIFIERS 주입 후에도 complete까지 도달.

- [ ] **Step 5: 기존 회귀 무손상**

Run: `cd backend && .venv/bin/pytest tests/ --ignore=tests/graph -m "not llm" -q 2>&1 | tail -3`
Expected: 사전-실패(mockup 12개) 외 신규 실패 없음.

---

## Self-Review

**1. Spec coverage (설계 7개 섹션 대비):**
- 확장 스키마(operations bare + dtos) → Task 2 derive_contract ✅
- naming.py 결정론 파생 → Task 1 ✅
- derive_contract 노드(고정세트 ∪ api 보정, 파일목록 우선, 빈입력 폴백) → Task 2 ✅
- 그래프 라우팅(planner→derive_contract→waves) + sse 노드 → Task 3 ✅
- 프롬프트 주입(REQUIRED IDENTIFIERS, 파일타입별) + GENERATOR_SYSTEM → Task 4 ✅
- 검증 승격(contract 기준, DAO도 교정, 폴백, 하위호환) → Task 5 ✅
- DTO 필드 검증+autofix → Task 6 ✅
- mybatis_fix contract 전달 → Task 7 ✅
- 테스트 전략 + 하위호환 + 회귀 + e2e → Task 8 ✅

**2. Placeholder scan:** "TBD/TODO" 없음. Task 2의 `_pascal_screen_code`는 "추가하지 말 것"으로 명시(미사용 함수 혼선 방지). 모든 코드 스텝에 실제 코드. ✅

**3. Type consistency:**
- naming: statement_id(op)/dao_method(op)/mybatis_tag(op)/dto_class(code,kind)/java_type(t)/ops_for_screen_type(t) — Task 1 정의가 Task 2·4·5 사용과 일치 ✅
- operation dict 키(op/statement_id/dao_method/param_type/return_type/mybatis_tag) — Task 2 생성, Task 4 주입, Task 5 검증에서 일치 ✅
- dto dict 키(name/kind/fields[name,java_type,db_column]) — Task 2·4·6 일치 ✅
- check_binding(files, contract=None)/autofix_binding(files, contract=None)/check_dto_fields/autofix_dto_fields 시그니처 — Task 5·6·7 일치 ✅
- mybatis_fix가 state["contract"] 읽어 전달 — Task 7, Task 3의 derive_contract가 채운 contract와 연결 ✅
- _EMITTING_NODES에 derive_contract 추가 → events 드레인 (Task 3) ✅

**알려진 메모:** Task 5의 contract-기준 autofix는 bare id라 편집거리 매칭이 Phase 1보다 정확(예: `selFooLst`→`selectList` 거리 작음). 거리 큰 경우(완전 무관 id)는 교정 안 하고 issue로 reviewer에 남김 — 보수 원칙 유지.
