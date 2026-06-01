# LangGraph Codegen — Plan 2: Nodes + Graph Assembly

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plan 1의 토대 모듈(state/llm/guides/tools) 위에 코드 생성 노드들(contract_extract, planner, generate_file, wave_gate, reviewer ReAct)과 LangGraph StateGraph 조립 + AsyncSqliteSaver 체크포인팅을 구현한다.

**Architecture:** 노드는 순수 async 함수 `async def node(state) -> dict`. LLM 호출은 Plan 1의 `gpt55_client` 직접 호출(Responses API). 병렬 wave는 `Send` map-reduce로 fan-out, `current_wave` + 조건부 엣지로 배리어. Reviewer만 도구를 쥐고 ReAct 루프(수렴 또는 하드캡 종료). LLM은 테스트에서 전부 mock한다.

**Tech Stack:** Python 3.12, LangGraph 1.2.2, openai SDK(Azure Responses API), pytest, pytest-asyncio

**참조 설계:** `docs/superpowers/specs/2026-06-01-langgraph-agentic-codegen-design.md` (섹션 2·5)
**선행:** Plan 1 (`backend/app/llm/graph/{state,llm,guides,tools}.py` 존재)

**명칭 주의:** gpt-5.5는 `gpt55_client` (Plan 1). "codex" 명칭 사용 금지.

---

## File Structure

### 신규 생성
- `backend/app/llm/graph/prompts.py` — 노드별 시스템 프롬프트 (contract/planner/generator)
- `backend/app/llm/graph/waves.py` — wave 고정 배정 규칙 (file_type → wave)
- `backend/app/llm/graph/nodes.py` — contract_extract / planner / generate_file / wave_gate 노드
- `backend/app/llm/graph/react.py` — Reviewer ReAct 루프 (tool-calling 연속 호출 + 수렴/하드캡)
- `backend/app/llm/graph/build.py` — StateGraph 조립 + Send fan-out + checkpointer
- `backend/app/llm/graph/config.py` — 상수 (REVIEWER_HARD_CAP 등)

### 테스트
- `backend/tests/graph/test_waves.py`
- `backend/tests/graph/test_nodes.py`
- `backend/tests/graph/test_react.py`
- `backend/tests/graph/test_build.py`
- `backend/tests/graph/test_checkpoint.py`
- `backend/tests/graph/conftest.py` — mock gpt55_client fixture

---

## Task 1: 상수 + wave 배정 규칙

**Files:**
- Create: `backend/app/llm/graph/config.py`
- Create: `backend/app/llm/graph/waves.py`
- Test: `backend/tests/graph/test_waves.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_waves.py`:

```python
import pytest

from app.llm.graph.waves import wave_for_file_type, files_in_wave, MAX_WAVE


def test_wave_assignment_is_fixed():
    assert wave_for_file_type("db_init_sql") == 1
    assert wave_for_file_type("dto_request") == 1
    assert wave_for_file_type("dto_response") == 1
    assert wave_for_file_type("vue_types") == 1
    assert wave_for_file_type("dao_impl") == 2
    assert wave_for_file_type("mapper_xml") == 2
    assert wave_for_file_type("vue_page") == 2
    assert wave_for_file_type("service_impl") == 3


def test_max_wave_is_three():
    assert MAX_WAVE == 3


def test_unknown_file_type_defaults_to_last_wave():
    # safest: unknown types run last so they can see everything
    assert wave_for_file_type("mystery") == 3


def test_files_in_wave_filters_plan():
    plan = {"files": [
        {"file_path": "A.java", "file_type": "dto_request"},
        {"file_path": "B.java", "file_type": "dao_impl"},
        {"file_path": "C.java", "file_type": "service_impl"},
    ]}
    wave1 = files_in_wave(plan, 1)
    assert [f["file_path"] for f in wave1] == ["A.java"]
    wave3 = files_in_wave(plan, 3)
    assert [f["file_path"] for f in wave3] == ["C.java"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_waves.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.waves'`

- [ ] **Step 3: Write config.py**

`backend/app/llm/graph/config.py`:

```python
"""Graph execution constants."""

# Reviewer ReAct loop: hard-cap backstop (convergence is primary exit).
REVIEWER_HARD_CAP = 6

# Per-file static_check gate: regenerate at most this many times.
GATE_MAX_REGEN = 1

# Max tool calls the reviewer may issue in a single ReAct turn batch.
REVIEWER_MAX_TOOLS_PER_TURN = 8
```

- [ ] **Step 4: Write waves.py**

`backend/app/llm/graph/waves.py`:

```python
"""Fixed wave assignment for file types (deterministic, not LLM-decided).

Wave 1: leaf files derivable directly from contract (no inter-dependency).
Wave 2: files depending on wave-1 DTO/types.
Wave 3: files depending on wave-2 DAO method names.
"""

from __future__ import annotations

MAX_WAVE = 3

_WAVE_MAP: dict[str, int] = {
    # wave 1 — leaf
    "db_init_sql": 1,
    "dto_request": 1,
    "dto_response": 1,
    "vue_types": 1,
    # wave 2 — depend on DTO/types
    "dao": 2,
    "dao_impl": 2,
    "mapper_xml": 2,
    "vue_page": 2,
    # wave 3 — depend on DAO method names
    "service": 3,
    "service_impl": 3,
}


def wave_for_file_type(file_type: str) -> int:
    """Return the fixed wave for a file type. Unknown types run last (see everything)."""
    return _WAVE_MAP.get(file_type, MAX_WAVE)


def files_in_wave(plan: dict, wave: int) -> list[dict]:
    """Return plan file specs assigned to the given wave."""
    return [f for f in plan.get("files", [])
            if wave_for_file_type(f["file_type"]) == wave]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_waves.py -q`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
cd backend
git add app/llm/graph/config.py app/llm/graph/waves.py tests/graph/test_waves.py
git commit -m "feat(codegen): add graph constants + fixed wave assignment rules"
```

---

## Task 2: 노드 프롬프트 + mock LLM fixture

**Files:**
- Create: `backend/app/llm/graph/prompts.py`
- Create: `backend/tests/graph/conftest.py`
- Test: (conftest 자체는 다음 태스크들이 사용)

- [ ] **Step 1: Write prompts.py**

`backend/app/llm/graph/prompts.py`:

```python
"""System prompts for code-generation nodes."""

CONTRACT_SYSTEM = """\
You are a requirements analyst. Given a spec, a confirmed Vue SFC, and real DB \
table info, extract a STRUCTURED CONTRACT as JSON. DO NOT generate code.

Output ONLY a JSON object with keys:
  screen: {id, name, type}
  tables: [{name, columns: [{col, type, pk}]}]
  fields: [{vue_field, db_column, type, label}]
  search_conditions: [...]
  table_columns: [...]
  api_signatures: [{method, path, req_dto, res_dto}]

Map every Vue field to its real DB column using the table info. The contract is \
the single source of truth for all downstream code generation."""

PLANNER_SYSTEM = """\
You are a build planner. Given a contract, list the files to generate. \
Output ONLY a JSON object: {files: [{file_path, file_type, layer, class_name, \
description}]}. Do NOT assign wave numbers — that is done by code. \
file_type must be one of: db_init_sql, dto_request, dto_response, dao_impl, \
mapper_xml, service_impl, vue_types, vue_page."""

GENERATOR_SYSTEM = """\
You are a senior engineer generating ONE CPMS file. Follow the provided guide \
sections exactly. Use the contract as the source of truth for field names and \
types. Output ONLY the file content, no markdown fences, no explanation."""

REVIEWER_SYSTEM = """\
You are a code reviewer with tools. Inspect the generated files for cross-file \
inconsistencies and guide violations. Use cross_check and lookup_guide to find \
problems, then FIX the offending files by returning corrected content. \
When no issues remain, respond with the single word DONE."""
```

- [ ] **Step 2: Write conftest.py (mock gpt55_client)**

`backend/tests/graph/conftest.py`:

```python
import json
import pytest


class FakeResponse:
    """Mimics openai Responses API result: .output_text and .output items."""
    def __init__(self, text="", output_items=None):
        self.output_text = text
        self.output = output_items or []


class FakeFunctionCall:
    type = "function_call"
    def __init__(self, name, arguments, call_id="c1"):
        self.name = name
        self.arguments = json.dumps(arguments) if isinstance(arguments, dict) else arguments
        self.call_id = call_id


@pytest.fixture
def fake_gpt55(monkeypatch):
    """Patch gpt55_client.complete / complete_with_tools with scripted responses.

    Usage:
        fake_gpt55.complete_returns = ["text1", "text2"]
        fake_gpt55.tools_returns = [FakeResponse(...), ...]
    """
    from app.llm.graph import llm

    class Fake:
        def __init__(self):
            self.complete_returns = []
            self.tools_returns = []
            self._c = 0
            self._t = 0

        async def complete(self, system, user, max_tokens=16384):
            r = self.complete_returns[self._c]
            self._c += 1
            return r

        async def complete_with_tools(self, system, user, tools, max_tokens=16384):
            r = self.tools_returns[self._t]
            self._t += 1
            return r

    fake = Fake()
    monkeypatch.setattr(llm, "gpt55_client", fake)
    # also patch the reference imported into nodes/react modules if already bound
    import app.llm.graph.nodes as nodes_mod
    import app.llm.graph.react as react_mod
    monkeypatch.setattr(nodes_mod, "gpt55_client", fake, raising=False)
    monkeypatch.setattr(react_mod, "gpt55_client", fake, raising=False)
    return fake
```

- [ ] **Step 3: Verify prompts import**

Run: `cd backend && .venv/bin/python -c "from app.llm.graph import prompts; print(bool(prompts.CONTRACT_SYSTEM))"`
Expected: `True`

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/llm/graph/prompts.py tests/graph/conftest.py
git commit -m "feat(codegen): add node system prompts + mock gpt55 test fixture"
```

---

## Task 3: contract_extract + planner 노드

**Files:**
- Create: `backend/app/llm/graph/nodes.py`
- Test: `backend/tests/graph/test_nodes.py`

설계 참조: contract_extract는 spec+vue+table_info → 계약 JSON (single-shot, 스키마 검증 시 1회 재생성). planner는 계약 → 파일 목록(JSON). wave 번호는 코드(waves.py)가 부여.

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_nodes.py`:

```python
import json
import pytest

from app.llm.graph import nodes

pytestmark = pytest.mark.asyncio


async def test_contract_extract_parses_json(fake_gpt55):
    contract = {"screen": {"id": "EDU001", "name": "교육", "type": "list"},
                "tables": [], "fields": [], "search_conditions": [],
                "table_columns": [], "api_signatures": []}
    fake_gpt55.complete_returns = [json.dumps(contract)]
    state = {"spec_markdown": "spec", "confirmed_vue": "<template/>", "table_info": "TB"}
    out = await nodes.contract_extract(state)
    assert out["contract"]["screen"]["id"] == "EDU001"


async def test_contract_extract_strips_fences(fake_gpt55):
    contract = {"screen": {"id": "X", "name": "n", "type": "list"}, "tables": [],
                "fields": [], "search_conditions": [], "table_columns": [],
                "api_signatures": []}
    fenced = "```json\n" + json.dumps(contract) + "\n```"
    fake_gpt55.complete_returns = [fenced]
    out = await nodes.contract_extract({"spec_markdown": "s", "confirmed_vue": "v", "table_info": "t"})
    assert out["contract"]["screen"]["id"] == "X"


async def test_planner_assigns_waves_via_code(fake_gpt55):
    plan = {"files": [
        {"file_path": "A.java", "file_type": "dto_request", "layer": "backend",
         "class_name": "A", "description": "d"},
        {"file_path": "B.java", "file_type": "service_impl", "layer": "backend",
         "class_name": "B", "description": "d"},
    ]}
    fake_gpt55.complete_returns = [json.dumps(plan)]
    out = await nodes.planner({"contract": {"screen": {}}})
    waves = {f["file_path"]: f["wave"] for f in out["plan"]["files"]}
    assert waves == {"A.java": 1, "B.java": 3}
    assert out["current_wave"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_nodes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.nodes'`

- [ ] **Step 3: Write nodes.py (contract + planner)**

`backend/app/llm/graph/nodes.py`:

```python
"""Code-generation graph nodes (pure async functions)."""

from __future__ import annotations

import json

from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import CONTRACT_SYSTEM, GENERATOR_SYSTEM, PLANNER_SYSTEM
from app.llm.graph.waves import wave_for_file_type


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        nl = text.index("\n") if "\n" in text else 3
        text = text[nl + 1:]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3].rstrip()
    return text


def _parse_json(text: str) -> dict:
    return json.loads(_strip_fences(text))


async def contract_extract(state: dict) -> dict:
    """Extract structured contract from spec + confirmed Vue + table info."""
    user = (
        f"=== SPEC ===\n{state['spec_markdown']}\n\n"
        f"=== CONFIRMED VUE ===\n{state['confirmed_vue']}\n\n"
        f"=== TABLE INFO ===\n{state.get('table_info', '')}\n"
    )
    raw = await gpt55_client.complete(CONTRACT_SYSTEM, user)
    try:
        contract = _parse_json(raw)
    except (ValueError, json.JSONDecodeError):
        # one retry with explicit instruction
        raw = await gpt55_client.complete(
            CONTRACT_SYSTEM, user + "\n\nReturn ONLY valid JSON.")
        contract = _parse_json(raw)
    return {"contract": contract,
            "events": [{"type": "contract", "contract": contract}]}


async def planner(state: dict) -> dict:
    """Plan files from contract; wave numbers assigned by code (not LLM)."""
    user = f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n"
    raw = await gpt55_client.complete(PLANNER_SYSTEM, user)
    plan = _parse_json(raw)
    for f in plan.get("files", []):
        f["wave"] = wave_for_file_type(f["file_type"])
    return {"plan": plan, "current_wave": 1,
            "events": [{"type": "plan", "files": plan.get("files", [])}]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_nodes.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/nodes.py tests/graph/test_nodes.py
git commit -m "feat(codegen): add contract_extract + planner nodes"
```

---

## Task 4: generate_file 노드 (single-shot + static_check 게이트)

**Files:**
- Modify: `backend/app/llm/graph/nodes.py` (append)
- Test: `backend/tests/graph/test_nodes.py` (append)

설계 참조: 파일 1개 생성 → static_check (db_init_sql은 validate_sql) → 위반 시 위반목록을 프롬프트에 넣어 1회 재생성. 가이드는 grace3 매핑 주입. wave 의존 파일 컨텍스트 주입.

- [ ] **Step 1: Append the failing test**

`backend/tests/graph/test_nodes.py`에 추가:

```python
async def test_generate_file_clean_single_shot(fake_gpt55, monkeypatch):
    fake_gpt55.complete_returns = ["class A { private String id; }"]
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "GUIDE")
    spec = {"file_path": "A.java", "file_type": "dto_request",
            "layer": "backend", "class_name": "A", "description": "d", "wave": 1}
    out = await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    gf = out["files"]["A.java"]
    assert gf["status"] == "ok"
    assert gf["wave"] == 1
    assert "private String id" in gf["content"]


async def test_generate_file_regenerates_once_on_violation(fake_gpt55, monkeypatch):
    # first output violates (UUID), second is clean
    fake_gpt55.complete_returns = [
        "import java.util.UUID; class A {}",
        "class A { private String id; }",
    ]
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "GUIDE")
    spec = {"file_path": "A.java", "file_type": "dto_request",
            "layer": "backend", "class_name": "A", "description": "d", "wave": 1}
    out = await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    gf = out["files"]["A.java"]
    assert "UUID" not in gf["content"]
    assert gf["status"] == "ok"


async def test_generate_file_keeps_violation_after_one_regen(fake_gpt55, monkeypatch):
    # both outputs violate -> pass through but record open issue
    fake_gpt55.complete_returns = [
        "import java.util.UUID; class A {}",
        "import java.util.UUID; class A {}",
    ]
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "GUIDE")
    spec = {"file_path": "A.java", "file_type": "dto_request",
            "layer": "backend", "class_name": "A", "description": "d", "wave": 1}
    out = await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    gf = out["files"]["A.java"]
    assert gf["status"] == "ok"  # passes through
    assert any("UUID" in i["issue"] for i in out["open_issues"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_nodes.py -k generate_file -q`
Expected: FAIL — `AttributeError: module 'app.llm.graph.nodes' has no attribute 'generate_file'`

- [ ] **Step 3: Implement (append to nodes.py)**

먼저 nodes.py 상단 import에 guides 추가 — `import json` 아래에:

```python
from app.llm.graph import guides
```

또한 static/sql 검증 import — `from app.llm.graph.waves import wave_for_file_type` 아래에:

```python
from app.llm.graph.tools import static_check_impl, validate_sql_impl
from app.llm.graph.config import GATE_MAX_REGEN
```

그리고 파일 끝에 추가:

```python
def _gate_check(spec: dict, content: str) -> list[dict]:
    """Run the deterministic gate for a file (static_check, or validate_sql for SQL)."""
    if spec["file_type"] == "db_init_sql":
        return validate_sql_impl(content)
    return static_check_impl(spec["file_path"], content, spec["file_type"], spec["layer"])


def _dep_context(state: dict, spec: dict) -> str:
    """Inject already-generated files from earlier waves as dependency context."""
    my_wave = spec["wave"]
    deps = [gf for gf in state.get("files", {}).values() if gf["wave"] < my_wave]
    if not deps:
        return ""
    parts = [f"--- {gf['file_path']} ---\n{gf['content']}" for gf in deps]
    return "\n\n=== DEPENDENCY FILES ===\n" + "\n\n".join(parts)


async def generate_file(state: dict) -> dict:
    """Generate ONE file (single-shot) + static_check gate (1 regen). For Send fan-out."""
    spec = state["_file_spec"]
    guide = guides.load_guide_for_file_type(spec["file_type"])
    base_user = (
        f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n\n"
        f"=== GUIDE ===\n{guide}\n"
        f"{_dep_context(state, spec)}\n\n"
        f"Generate file: {spec['file_path']} (type={spec['file_type']}, "
        f"class={spec.get('class_name', '')})\n{spec.get('description', '')}"
    )
    content = _strip_fences(await gpt55_client.complete(GENERATOR_SYSTEM, base_user))
    issues = _gate_check(spec, content)

    regen = 0
    while issues and regen < GATE_MAX_REGEN:
        fix_user = (base_user + "\n\n=== FIX THESE VIOLATIONS ===\n"
                    + "\n".join(f"- {i['issue']}" for i in issues))
        content = _strip_fences(await gpt55_client.complete(GENERATOR_SYSTEM, fix_user))
        issues = _gate_check(spec, content)
        regen += 1

    gf = {"file_path": spec["file_path"], "file_type": spec["file_type"],
          "layer": spec["layer"], "wave": spec["wave"], "content": content,
          "status": "ok", "status_log": [f"gate regen={regen}"]}
    result = {"files": {spec["file_path"]: gf},
              "events": [{"type": "file_complete", "path": spec["file_path"],
                          "layer": spec["layer"]}]}
    if issues:
        result["open_issues"] = issues  # passed through; reviewer will handle
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_nodes.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/nodes.py tests/graph/test_nodes.py
git commit -m "feat(codegen): add generate_file node with static_check gate (1 regen)"
```

---

## Task 5: Reviewer ReAct 루프 (tool-calling 연속 호출)

**Files:**
- Create: `backend/app/llm/graph/react.py`
- Test: `backend/tests/graph/test_react.py`

설계 참조: gpt-5.5가 도구 자율 호출 → dispatch_tool 실행 → 결과 되돌림 → 위반 발견 시 파일 직접 수정 → 수렴(DONE 또는 0 이슈) 또는 하드캡 종료. Responses API tool 연속 호출은 `previous_response_id`로 잇는다(라이브 검증된 패턴). **이 태스크의 LLM 호출은 mock**이므로 응답 시퀀스를 conftest로 스크립트한다.

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_react.py`:

```python
import pytest

from app.llm.graph import react
from tests.graph.conftest import FakeResponse, FakeFunctionCall

pytestmark = pytest.mark.asyncio

_DTO = {"file_path": "D.java", "file_type": "dto_response", "layer": "backend",
        "wave": 1, "status": "ok", "status_log": [],
        "content": "class D { private String nm; }"}


async def test_reviewer_converges_when_no_issues(fake_gpt55):
    # model immediately says DONE (no tool calls)
    fake_gpt55.tools_returns = [FakeResponse(text="DONE", output_items=[])]
    out = await react.reviewer({"files": {"D.java": _DTO}, "contract": {},
                                "review_iterations": 0, "open_issues": []})
    assert out["open_issues"] == []
    assert out["review_iterations"] >= 1


async def test_reviewer_runs_tool_then_done(fake_gpt55):
    # turn 1: call cross_check ; turn 2: DONE
    fake_gpt55.tools_returns = [
        FakeResponse(output_items=[FakeFunctionCall("cross_check", {})]),
        FakeResponse(text="DONE", output_items=[]),
    ]
    out = await react.reviewer({"files": {"D.java": _DTO}, "contract": {},
                                "review_iterations": 0, "open_issues": []})
    assert out["review_iterations"] >= 2
    assert any(e["type"] == "tool_call" for e in out["events"])


async def test_reviewer_stops_at_hard_cap(fake_gpt55, monkeypatch):
    monkeypatch.setattr(react, "REVIEWER_HARD_CAP", 2)
    # model never says DONE — always calls a tool
    fake_gpt55.tools_returns = [
        FakeResponse(output_items=[FakeFunctionCall("list_generated_files", {})])
        for _ in range(10)
    ]
    out = await react.reviewer({"files": {"D.java": _DTO}, "contract": {},
                                "review_iterations": 0, "open_issues": []})
    assert out["review_iterations"] == 2  # capped
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_react.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.react'`

- [ ] **Step 3: Write react.py**

`backend/app/llm/graph/react.py`:

```python
"""Reviewer ReAct loop: tool-calling until convergence or hard cap."""

from __future__ import annotations

import json

from app.llm.graph.config import REVIEWER_HARD_CAP
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import REVIEWER_SYSTEM
from app.llm.graph.tools import TOOL_SPECS, dispatch_tool


def _extract_function_calls(resp) -> list:
    return [item for item in getattr(resp, "output", [])
            if getattr(item, "type", "") == "function_call"]


async def reviewer(state: dict) -> dict:
    """Run the reviewer ReAct loop over all generated files."""
    files = dict(state.get("files", {}))
    contract = state.get("contract", {})
    iterations = state.get("review_iterations", 0)
    events: list[dict] = []

    user = (
        "Review all generated files for cross-file consistency and guide "
        "violations. Files:\n"
        + "\n".join(f"- {p} ({gf['file_type']})" for p, gf in files.items())
    )

    while iterations < REVIEWER_HARD_CAP:
        iterations += 1
        resp = await gpt55_client.complete_with_tools(REVIEWER_SYSTEM, user, TOOL_SPECS)
        calls = _extract_function_calls(resp)

        if not calls:
            # no tool calls -> model is done (text like "DONE")
            events.append({"type": "react_converged", "iterations": iterations})
            break

        # execute each tool call, feed results back into next turn's prompt
        observations: list[str] = []
        for call in calls:
            args = json.loads(call.arguments) if isinstance(call.arguments, str) else call.arguments
            events.append({"type": "tool_call", "tool": call.name, "args": args})
            try:
                result = dispatch_tool(call.name, args, files, contract)
            except Exception as exc:  # tool error becomes observation (self-recovery)
                result = {"error": str(exc)}
            events.append({"type": "tool_result", "tool": call.name})
            observations.append(f"{call.name} -> {json.dumps(result, ensure_ascii=False)[:1000]}")

        user = (user + "\n\n=== TOOL RESULTS ===\n" + "\n".join(observations)
                + "\n\nFix any offending files, or respond DONE if clean.")

    # recompute open issues via cross_check as the convergence signal
    from app.llm.graph.tools import cross_check_impl
    open_issues = cross_check_impl(files, contract)
    return {"files": files, "review_iterations": iterations,
            "open_issues": open_issues, "events": events}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_react.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/react.py tests/graph/test_react.py
git commit -m "feat(codegen): add reviewer ReAct loop (tool-calling, converge/hard-cap)"
```

---

## Task 6: 그래프 조립 (build.py) + wave fan-out

**Files:**
- Create: `backend/app/llm/graph/build.py`
- Test: `backend/tests/graph/test_build.py`

설계 참조: START → contract_extract → planner → wave fan-out(Send) → wave_gate(배리어/증가) → reviewer → END. wave_gate가 `current_wave`를 올리고 다음 wave로 Send, 마지막이면 reviewer로.

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_build.py`:

```python
import json
import pytest

from app.llm.graph import build
from tests.graph.conftest import FakeResponse

pytestmark = pytest.mark.asyncio


async def test_build_graph_compiles():
    graph = build.build_graph(checkpointer=None)
    assert graph is not None


async def test_end_to_end_with_mock_llm(fake_gpt55, monkeypatch):
    # scripted: contract, plan, then one file per generate_file call, then reviewer DONE
    contract = {"screen": {"id": "X", "name": "n", "type": "list"}, "tables": [],
                "fields": [], "search_conditions": [], "table_columns": [],
                "api_signatures": []}
    plan = {"files": [
        {"file_path": "A.java", "file_type": "dto_request", "layer": "backend",
         "class_name": "A", "description": "d"},
        {"file_path": "ASvc.java", "file_type": "service_impl", "layer": "backend",
         "class_name": "ASvc", "description": "d"},
    ]}
    fake_gpt55.complete_returns = [
        json.dumps(contract),           # contract_extract
        json.dumps(plan),               # planner
        "class A { private String id; }",      # generate A.java (wave1)
        "class ASvc { void run(){} }",         # generate ASvc.java (wave3)
    ]
    fake_gpt55.tools_returns = [FakeResponse(text="DONE", output_items=[])]
    monkeypatch.setattr("app.llm.graph.nodes.guides.load_guide_for_file_type",
                        lambda ft: "GUIDE")

    graph = build.build_graph(checkpointer=None)
    state = {"session_id": "s1", "spec_markdown": "spec",
             "confirmed_vue": "<template/>", "table_info": "TB", "files": {}}
    final = await graph.ainvoke(state, {"configurable": {"thread_id": "s1"},
                                        "recursion_limit": 50})
    assert set(final["files"].keys()) == {"A.java", "ASvc.java"}
    assert final["review_iterations"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_build.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.build'`

- [ ] **Step 3: Write build.py**

`backend/app/llm/graph/build.py`:

```python
"""Assemble the code-generation StateGraph."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.llm.graph.state import CodeGenState
from app.llm.graph.waves import MAX_WAVE, files_in_wave
from app.llm.graph import nodes, react


def _fan_out_current_wave(state: dict):
    """Conditional edge: Send one generate_file per file in the current wave."""
    wave = state.get("current_wave", 1)
    specs = files_in_wave(state["plan"], wave)
    if not specs:
        # empty wave -> go straight to gate to advance
        return ["wave_gate"]
    return [Send("generate_file", {**state, "_file_spec": spec}) for spec in specs]


def _wave_gate(state: dict) -> dict:
    """Barrier: increment wave after a wave's files fan in."""
    return {"current_wave": state.get("current_wave", 1) + 1}


def _route_after_gate(state: dict):
    """After gate: next wave fan-out, or reviewer when waves exhausted."""
    if state.get("current_wave", 1) > MAX_WAVE:
        return "reviewer"
    return "fan_out"


def build_graph(checkpointer=None):
    g = StateGraph(CodeGenState)
    g.add_node("contract_extract", nodes.contract_extract)
    g.add_node("planner", nodes.planner)
    g.add_node("generate_file", nodes.generate_file)
    g.add_node("wave_gate", _wave_gate)
    g.add_node("reviewer", react.reviewer)

    g.add_edge(START, "contract_extract")
    g.add_edge("contract_extract", "planner")

    # planner -> fan_out (virtual): use conditional edges keyed off current_wave
    g.add_conditional_edges("planner", _fan_out_current_wave,
                            ["generate_file", "wave_gate"])
    # all generate_file results fan in to wave_gate
    g.add_edge("generate_file", "wave_gate")
    g.add_conditional_edges("wave_gate", _route_after_gate,
                            {"fan_out": "generate_file", "reviewer": "reviewer"})
    g.add_edge("reviewer", END)

    return g.compile(checkpointer=checkpointer)
```

**주의:** `_route_after_gate`가 "fan_out"을 반환할 때 generate_file로 직접 가면 file_spec이 없다. LangGraph 조건부 엣지에서 Send를 쓰려면 라우터가 Send 리스트를 반환해야 한다. 아래 Step 3b로 수정한다.

- [ ] **Step 3b: build.py 라우팅을 Send 기반으로 수정**

`_route_after_gate`와 conditional edges를 다음으로 교체:

```python
def _route_after_gate(state: dict):
    """After gate: Send next wave's files, or go to reviewer when exhausted."""
    wave = state.get("current_wave", 1)
    if wave > MAX_WAVE:
        return "reviewer"
    specs = files_in_wave(state["plan"], wave)
    if not specs:
        # skip empty wave by bumping again via a no-op Send to wave_gate
        return [Send("wave_gate", state)]
    return [Send("generate_file", {**state, "_file_spec": spec}) for spec in specs]
```

그리고 planner 라우팅도 동일 함수로 통일 — `build_graph` 내 엣지 정의를 다음으로 교체:

```python
    g.add_edge(START, "contract_extract")
    g.add_edge("contract_extract", "planner")
    g.add_conditional_edges("planner", _route_after_gate,
                            ["generate_file", "wave_gate", "reviewer"])
    g.add_edge("generate_file", "wave_gate")
    g.add_conditional_edges("wave_gate", _route_after_gate,
                            ["generate_file", "wave_gate", "reviewer"])
    g.add_edge("reviewer", END)
```

(planner는 current_wave=1로 진입하므로 _route_after_gate가 wave1 파일을 Send한다. `_fan_out_current_wave`는 삭제.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_build.py -q`
Expected: PASS (2 passed)

만약 라우팅 사이클 관련 에러가 나면, `_route_after_gate`가 `current_wave > MAX_WAVE`까지 정확히 증가하는지 확인(wave_gate가 매번 +1). recursion_limit=50으로 충분.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/build.py tests/graph/test_build.py
git commit -m "feat(codegen): assemble StateGraph with wave fan-out + barriers"
```

---

## Task 7: 체크포인팅 (AsyncSqliteSaver) + 재개

**Files:**
- Modify: `backend/app/llm/graph/build.py` (add checkpointer factory)
- Test: `backend/tests/graph/test_checkpoint.py`

설계 참조: thread_id=session_id, 중단 후 재개 시 완료 노드 캐시. 테스트는 in-memory sqlite로 한 번 실행 후 상태가 체크포인트에 저장됐는지 확인.

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_checkpoint.py`:

```python
import json
import pytest

from app.llm.graph import build
from tests.graph.conftest import FakeResponse

pytestmark = pytest.mark.asyncio


async def test_checkpoint_persists_state(fake_gpt55, monkeypatch, tmp_path):
    contract = {"screen": {"id": "X", "name": "n", "type": "list"}, "tables": [],
                "fields": [], "search_conditions": [], "table_columns": [],
                "api_signatures": []}
    plan = {"files": [{"file_path": "A.java", "file_type": "dto_request",
                       "layer": "backend", "class_name": "A", "description": "d"}]}
    fake_gpt55.complete_returns = [json.dumps(contract), json.dumps(plan),
                                   "class A { private String id; }"]
    fake_gpt55.tools_returns = [FakeResponse(text="DONE", output_items=[])]
    monkeypatch.setattr("app.llm.graph.nodes.guides.load_guide_for_file_type",
                        lambda ft: "G")

    db = str(tmp_path / "ckpt.db")
    async with build.make_checkpointer(db) as cp:
        graph = build.build_graph(checkpointer=cp)
        cfg = {"configurable": {"thread_id": "sess-X"}, "recursion_limit": 50}
        await graph.ainvoke({"session_id": "sess-X", "spec_markdown": "s",
                             "confirmed_vue": "v", "table_info": "t", "files": {}}, cfg)
        # state retrievable from checkpoint
        snapshot = await graph.aget_state(cfg)
        assert "A.java" in snapshot.values["files"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_checkpoint.py -q`
Expected: FAIL — `AttributeError: module 'app.llm.graph.build' has no attribute 'make_checkpointer'`

- [ ] **Step 3: Add make_checkpointer to build.py**

`backend/app/llm/graph/build.py` 상단 import에 추가:

```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
```

파일 끝에 추가:

```python
def make_checkpointer(db_path: str = ".sessions/codegen_graph.db"):
    """Async context manager yielding an AsyncSqliteSaver (thread_id=session_id)."""
    return AsyncSqliteSaver.from_conn_string(db_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_checkpoint.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/build.py tests/graph/test_checkpoint.py
git commit -m "feat(codegen): add AsyncSqliteSaver checkpointer factory"
```

---

## Task 8: Plan 2 회귀 확인

**Files:** (없음 — 검증만)

- [ ] **Step 1: graph 패키지 전체 테스트**

Run: `cd backend && .venv/bin/pytest tests/graph/ -q`
Expected: PASS (Plan 1의 24 + Plan 2의 waves 4 + nodes 6 + react 3 + build 2 + checkpoint 1 = 40)

- [ ] **Step 2: import 사이클 없음 확인**

Run: `cd backend && .venv/bin/python -c "from app.llm.graph import build; build.build_graph(checkpointer=None); print('graph builds')"`
Expected: `graph builds`

- [ ] **Step 3: 기존 테스트 회귀 (Plan 2가 기존을 안 깼는지)**

Run: `cd backend && .venv/bin/pytest tests/ -q 2>&1 | tail -3`
Expected: 기존 사전-실패(13개, Plan 1 때 확인됨) 외에 신규 실패 없음. graph 테스트 전부 통과.

---

## Self-Review

**1. Spec coverage (설계 섹션 2·5 대비):**
- contract_extract (Vue+spec+table → 계약) → Task 3 ✅
- planner (계약 → 파일, wave 코드 배정) → Task 3 ✅
- generate_file (single-shot + static_check 게이트 1회) → Task 4 ✅
- 3-wave 고정 배정 → Task 1 ✅
- wave fan-out/배리어 (Send + wave_gate) → Task 6 ✅
- reviewer ReAct (도구 자율호출, 수렴/하드캡, 직접수정) → Task 5 ✅
- AsyncSqliteSaver 체크포인팅 (thread_id=session_id, 재개) → Task 7 ✅
- SSE 어댑터 + 라우터 → **Plan 3** (범위 밖, 명시)
- 프론트엔드 → **Plan 4** (범위 밖, 명시)

**2. Placeholder scan:** "TBD/TODO" 없음. 모든 코드 스텝에 실제 코드. Task 6에 Step 3b로 Send 라우팅 수정을 명시(LangGraph 조건부 엣지+Send 정확성). ✅

**3. Type consistency:**
- `gpt55_client.complete(system, user)` / `complete_with_tools(system, user, tools)` 시그니처가 Plan 1 llm.py와 일치 ✅
- GeneratedFile 키(file_path/file_type/layer/wave/content/status/status_log)가 Plan 1 state.py + generate_file 생성과 일치 ✅
- `dispatch_tool(name, args, files, contract)` 호출이 Plan 1 정의와 일치 ✅
- `_file_spec`에 wave 키 포함(planner가 부여) → generate_file의 `spec["wave"]` 참조 일치 ✅
- `FakeResponse(text, output_items)` / `FakeFunctionCall(name, arguments)` conftest 정의와 test 사용 일치 ✅

**알려진 리스크:** Task 5의 reviewer는 Responses API tool 연속 호출을 `complete_with_tools` 단발 + 관찰값을 다음 user 프롬프트에 붙이는 방식으로 단순화했다(previous_response_id 미사용). 실제 gpt-5.5 연동 시 멀티턴 tool 컨텍스트 유지가 필요하면 Plan 3 통합 단계에서 previous_response_id 방식으로 보강한다. mock 테스트는 이 단순화 기준으로 통과한다.
