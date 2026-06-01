# LangGraph Codegen — Plan 1: Foundation Modules

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LangGraph 기반 코드 생성의 토대 모듈(상태 스키마, gpt-5.5 클라이언트, 가이드 mtime 로더, 7개 도구)을 LLM 없이 단위 테스트 가능하게 구현한다.

**Architecture:** `backend/app/llm/graph/` 신규 패키지에 의존성이 없는 leaf 모듈부터 만든다. 노드/그래프 조립은 Plan 2에서 이 모듈들을 사용한다. 결정론적 로직(reducer, 정규식 검증, 가이드 로딩, SQL 검증)만 다루므로 전부 mock 없이 실제 테스트한다.

**Tech Stack:** Python 3.12, FastAPI, LangGraph, openai SDK(Azure Responses API), pytest

**참조 설계:** `docs/superpowers/specs/2026-06-01-langgraph-agentic-codegen-design.md` (섹션 3·4)

**명칭 정정 주의:** 기존 `codex_client`/`CodexLLMClient`/`CODEX_AZURE_OPENAI_*`는 실제 gpt-5.5의 오기다. 신규 코드는 `gpt55_client` / `Gpt55Client`로 명명한다. 기존 `CODEX_AZURE_OPENAI_*` env 변수는 이번 플랜에서 건드리지 않고 그대로 읽어 재사용한다(rename은 후속).

---

## File Structure

### 신규 생성
- `backend/app/llm/graph/__init__.py` — 패키지 초기화 (빈 파일)
- `backend/app/llm/graph/state.py` — `CodeGenState` TypedDict + `GeneratedFile` + `merge_files` reducer
- `backend/app/llm/graph/llm.py` — `Gpt55Client` (Azure Responses API, tool-calling, 재시도)
- `backend/app/llm/graph/guides.py` — 가이드 md mtime-fresh 로더 + file_type→가이드 매핑
- `backend/app/llm/graph/tools.py` — 7개 도구의 결정론적 코어 함수 + @tool 래퍼

### 테스트
- `backend/tests/graph/__init__.py`
- `backend/tests/graph/test_state.py`
- `backend/tests/graph/test_guides.py`
- `backend/tests/graph/test_tools.py`
- `backend/tests/graph/test_llm.py`

### 수정
- `backend/pyproject.toml` — langgraph 의존성 추가

---

## Task 1: 의존성 추가 + 패키지 스캐폴드

**Files:**
- Modify: `backend/pyproject.toml:5-15` (dependencies 리스트)
- Create: `backend/app/llm/graph/__init__.py`
- Create: `backend/tests/graph/__init__.py`

- [ ] **Step 1: pyproject.toml dependencies에 langgraph 추가**

`backend/pyproject.toml`의 `dependencies` 리스트(현재 `aiofiles` 다음)에 두 줄 추가:

```toml
dependencies = [
    "fastapi",
    "uvicorn[standard]",
    "httpx",
    "python-multipart",
    "anthropic",
    "openai",
    "pydantic-settings",
    "sse-starlette",
    "aiofiles",
    "langgraph>=0.2.0",
    "langgraph-checkpoint-sqlite>=2.0.0",
]
```

- [ ] **Step 2: 설치**

Run: `cd backend && .venv/bin/pip install -e ".[dev]"`
Expected: `Successfully installed langgraph-... langgraph-checkpoint-sqlite-...`

- [ ] **Step 3: 설치 확인**

Run: `cd backend && .venv/bin/python -c "import langgraph; from langgraph.graph import StateGraph; from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver; print('ok')"`
Expected: `ok`

- [ ] **Step 4: 패키지 디렉터리 생성**

Run: `cd backend && mkdir -p app/llm/graph tests/graph && touch app/llm/graph/__init__.py tests/graph/__init__.py`
Expected: (no output)

- [ ] **Step 5: Commit**

```bash
cd backend
git add pyproject.toml app/llm/graph/__init__.py tests/graph/__init__.py
git commit -m "chore(codegen): add langgraph deps + graph package scaffold"
```

---

## Task 2: 상태 스키마 (state.py)

**Files:**
- Create: `backend/app/llm/graph/state.py`
- Test: `backend/tests/graph/test_state.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_state.py`:

```python
from app.llm.graph.state import merge_files, GeneratedFile


def test_merge_files_combines_disjoint_keys():
    left = {"a.java": {"file_path": "a.java", "file_type": "dto_request",
                       "layer": "backend", "wave": 1, "content": "A",
                       "status": "ok", "status_log": []}}
    right = {"b.java": {"file_path": "b.java", "file_type": "dao_impl",
                        "layer": "backend", "wave": 2, "content": "B",
                        "status": "ok", "status_log": []}}
    merged = merge_files(left, right)
    assert set(merged.keys()) == {"a.java", "b.java"}


def test_merge_files_right_wins_on_same_key():
    left = {"a.java": {"file_path": "a.java", "content": "OLD", "file_type": "x",
                       "layer": "backend", "wave": 1, "status": "ok", "status_log": []}}
    right = {"a.java": {"file_path": "a.java", "content": "NEW", "file_type": "x",
                        "layer": "backend", "wave": 1, "status": "ok", "status_log": []}}
    merged = merge_files(left, right)
    assert merged["a.java"]["content"] == "NEW"


def test_merge_files_handles_none_left():
    right = {"a.java": {"file_path": "a.java", "content": "A", "file_type": "x",
                        "layer": "backend", "wave": 1, "status": "ok", "status_log": []}}
    assert merge_files(None, right) == right


def test_generated_file_keys():
    gf: GeneratedFile = {"file_path": "x", "file_type": "dto_request",
                         "layer": "backend", "wave": 1, "content": "",
                         "status": "ok", "status_log": []}
    assert gf["wave"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.state'`

- [ ] **Step 3: Write state.py**

`backend/app/llm/graph/state.py`:

```python
"""LangGraph state schema for code generation."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class GeneratedFile(TypedDict):
    file_path: str
    file_type: str        # dto_request | dao_impl | vue_page | ...
    layer: str            # backend | frontend
    wave: int             # 1 | 2 | 3
    content: str
    status: str           # ok | failed
    status_log: list[str]


def merge_files(
    left: dict[str, GeneratedFile] | None,
    right: dict[str, GeneratedFile] | None,
) -> dict[str, GeneratedFile]:
    """Reducer for parallel file writes. file_path-keyed; right wins on conflict."""
    return {**(left or {}), **(right or {})}


class CodeGenState(TypedDict, total=False):
    # ── 입력 (불변) ──
    session_id: str
    spec_markdown: str
    confirmed_vue: str
    table_info: str
    # ── Contract Extractor 산출 ──
    contract: dict | None
    # ── Planner 산출 ──
    plan: dict | None
    # ── 병렬 생성 결과 ──
    files: Annotated[dict[str, GeneratedFile], merge_files]
    # ── Reviewer ──
    review_iterations: int
    open_issues: list[dict]
    # ── 진행/관찰 ──
    current_wave: int
    events: Annotated[list[dict], add]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_state.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/state.py tests/graph/test_state.py
git commit -m "feat(codegen): add CodeGenState schema + merge_files reducer"
```

---

## Task 3: 가이드 mtime-fresh 로더 (guides.py)

**Files:**
- Create: `backend/app/llm/graph/guides.py`
- Test: `backend/tests/graph/test_guides.py`

설계 참조: 매 호출 mtime 확인 → 변경 시 자동 재로드(죽은 `invalidate_cache` 대체). `PROMPT_REFERENCE_DIR`(`settings`)에서 BackendGuide/FrontendGuide md를 읽는다.

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_guides.py`:

```python
import time
from pathlib import Path

import pytest

from app.llm.graph import guides


@pytest.fixture
def guide_dir(tmp_path, monkeypatch):
    base = tmp_path / "pfy_prompt"
    (base / "BackendGuide").mkdir(parents=True)
    (base / "FrontendGuide").mkdir(parents=True)
    (base / "BackendGuide" / "표준.md").write_text(
        "## DTO 표준\n원본 DTO 규칙\n## Service 표준\nsvc\n", encoding="utf-8"
    )
    (base / "FrontendGuide" / "03_SearchForm_구현.md").write_text(
        "## SearchForm\n검색폼 규칙\n", encoding="utf-8"
    )
    (base / "테이블정보.md" if False else base / "BackendGuide" / "테이블정보.md").write_text(
        "## 테이블\nTB_X\n", encoding="utf-8"
    )
    monkeypatch.setattr(guides.settings, "PROMPT_REFERENCE_DIR", str(base))
    guides._reset_cache_for_test()
    return base


def test_load_backend_guide_returns_content(guide_dir):
    text = guides.load_guide_for_file_type("dto_request")
    assert "DTO 표준" in text
    assert "원본 DTO 규칙" in text


def test_load_frontend_guide_for_vue_page(guide_dir):
    text = guides.load_guide_for_file_type("vue_page")
    assert "SearchForm" in text or "검색폼" in text


def test_mtime_change_triggers_reload(guide_dir):
    first = guides.load_guide_for_file_type("dto_request")
    assert "원본 DTO 규칙" in first
    time.sleep(0.01)
    (guide_dir / "BackendGuide" / "표준.md").write_text(
        "## DTO 표준\n변경된 DTO 규칙\n", encoding="utf-8"
    )
    second = guides.load_guide_for_file_type("dto_request")
    assert "변경된 DTO 규칙" in second
    assert "원본 DTO 규칙" not in second


def test_lookup_guide_by_topic(guide_dir):
    text = guides.lookup_guide("backend", "Service 표준")
    assert "svc" in text


def test_load_table_info(guide_dir):
    text = guides.load_table_info()
    assert "TB_X" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_guides.py -v`
Expected: FAIL — `ModuleNotFoundError` 또는 `AttributeError: _reset_cache_for_test`

- [ ] **Step 3: Write guides.py**

`backend/app/llm/graph/guides.py`:

```python
"""Guide markdown loader with mtime-based freshness.

Reads BackendGuide/FrontendGuide md from PROMPT_REFERENCE_DIR. Re-reads a file
whenever its mtime changes, so editing a guide is reflected on the next codegen
run without a server restart.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import settings

# path -> (mtime, text). Per-file cache keyed by absolute path.
_FILE_CACHE: dict[str, tuple[float, str]] = {}


def _reset_cache_for_test() -> None:
    _FILE_CACHE.clear()


def _read_fresh(path: Path) -> str:
    """Return file text, re-reading only if mtime changed since last read."""
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        _FILE_CACHE.pop(key, None)
        return ""
    cached = _FILE_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    text = path.read_text(encoding="utf-8")
    _FILE_CACHE[key] = (mtime, text)
    return text


def _split_by_headings(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "_preamble"
    parts: list[str] = []
    for line in text.splitlines(keepends=True):
        m = re.match(r"^#{2,3}\s+(.+)", line)
        if m:
            sections[current] = "".join(parts)
            current = m.group(1).strip()
            parts = [line]
        else:
            parts.append(line)
    sections[current] = "".join(parts)
    return sections


# file_type -> [(guide filename prefix, layer)]; 개선3: 넉넉히 주입(매핑 누락 위험↓)
_FILE_TYPE_GUIDES: dict[str, list[tuple[str, str]]] = {
    "dto_request":   [("표준", "backend")],
    "dto_response":  [("표준", "backend")],
    "dao":           [("표준", "backend")],
    "dao_impl":      [("표준", "backend")],
    "service":       [("표준", "backend")],
    "service_impl":  [("표준", "backend")],
    "mapper_xml":    [("표준", "backend")],
    "db_init_sql":   [("표준", "backend"), ("02-", "backend")],
    "vue_page":      [("00_", "frontend"), ("02_", "frontend"), ("03_", "frontend"),
                      ("04_", "frontend"), ("07_", "frontend")],
    "vue_types":     [("06_", "frontend")],
}

_LAYER_DIR = {"backend": "BackendGuide", "frontend": "FrontendGuide"}


def _guide_files(layer: str, prefix: str) -> list[Path]:
    base = Path(settings.PROMPT_REFERENCE_DIR) / _LAYER_DIR[layer]
    if not base.exists():
        return []
    return [f for f in sorted(base.glob("*.md")) if f.name.startswith(prefix)]


def load_guide_for_file_type(file_type: str) -> str:
    """Concatenate all guide sections relevant to a file type (fresh)."""
    entries = _FILE_TYPE_GUIDES.get(file_type, [])
    parts: list[str] = []
    for prefix, layer in entries:
        for f in _guide_files(layer, prefix):
            parts.append(f"=== {f.name} ===\n{_read_fresh(f)}")
    return "\n\n".join(parts)


def lookup_guide(layer: str, topic: str) -> str:
    """Return guide sections whose heading contains `topic` (fresh). Tool #5."""
    base = Path(settings.PROMPT_REFERENCE_DIR) / _LAYER_DIR.get(layer, "BackendGuide")
    if not base.exists():
        return ""
    out: list[str] = []
    for f in sorted(base.glob("*.md")):
        sections = _split_by_headings(_read_fresh(f))
        for heading, body in sections.items():
            if topic.lower() in heading.lower():
                out.append(body)
    return "\n".join(out)


def load_table_info() -> str:
    """Load 테이블정보.md (real DB columns/types) fresh."""
    base = Path(settings.PROMPT_REFERENCE_DIR)
    for candidate in (base / "BackendGuide" / "테이블정보.md", base / "테이블정보.md"):
        if candidate.exists():
            return _read_fresh(candidate)
    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_guides.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/guides.py tests/graph/test_guides.py
git commit -m "feat(codegen): add mtime-fresh guide loader (replaces dead invalidate_cache)"
```

---

## Task 4: 검증 도구 코어 — static_check + validate_sql (tools.py 1부)

**Files:**
- Create: `backend/app/llm/graph/tools.py`
- Test: `backend/tests/graph/test_tools.py`

설계 참조: 도구는 결정론적 코어 함수(`_*_impl`) + @tool 래퍼의 2용도. 이 태스크는 코어 함수만(래퍼는 Task 6). `static_check`는 기존 정규식 룰의 핵심 일부를 이식한다.

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_tools.py`:

```python
from app.llm.graph.tools import static_check_impl, validate_sql_impl


def test_static_check_flags_uuid_import():
    issues = static_check_impl("Foo.java", "import java.util.UUID;\nclass Foo {}", "dto_request", "backend")
    assert any("UUID" in i["issue"] for i in issues)


def test_static_check_flags_scrollheight_flex():
    issues = static_check_impl("Foo.vue", '<DataTable scrollHeight="flex" />', "vue_page", "frontend")
    assert any("scrollHeight" in i["issue"] for i in issues)


def test_static_check_clean_backend_returns_empty():
    issues = static_check_impl("Foo.java", "class Foo { private String id; }", "dto_request", "backend")
    assert issues == []


def test_static_check_only_checks_matching_layer():
    # frontend rule must not fire on backend file
    issues = static_check_impl("Foo.java", 'scrollHeight="flex"', "dto_request", "backend")
    assert issues == []


def test_validate_sql_flags_missing_semicolon_statements():
    issues = validate_sql_impl("CREATE TABLE x (id INT)\nCREATE TABLE y (id INT)")
    assert any("semicolon" in i["issue"].lower() or "세미콜론" in i["issue"] for i in issues)


def test_validate_sql_clean_returns_empty():
    issues = validate_sql_impl("CREATE TABLE x (id INT);")
    assert issues == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.tools'`

- [ ] **Step 3: Write tools.py (코어 함수 1부)**

`backend/app/llm/graph/tools.py`:

```python
"""Code-generation tools: deterministic core functions + @tool wrappers.

Core functions (_impl) are called directly by graph nodes (no LLM).
@tool wrappers (Task 6) expose the same logic to the Reviewer's tool-calling loop.
"""

from __future__ import annotations

import re

# ── static_check rules (layer-scoped) ──
_BACKEND_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"import\s+java\.util\.UUID"),
     "java.util.UUID import found — use String for ID fields"),
    (re.compile(r"@Service\s*\(\s*\"[^\"]+\"\s*\)"),
     "@Service with bean name — use bare @Service"),
    (re.compile(r"UUID\s*\.\s*randomUUID\s*\("),
     "UUID.randomUUID() found — IDs come from DB sequence or DTO"),
    (re.compile(r"LoggerFactory\.getLogger\s*\("),
     "LoggerFactory.getLogger() — use @Slf4j (lombok) instead"),
]

_FRONTEND_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"scrollHeight\s*=\s*[\"']flex[\"']"),
     'scrollHeight="flex" — use scrollHeight="540px" + virtualScrollerOptions'),
    (re.compile(r"<script(?!\s+setup)[\s>]"),
     '<script> without setup — use <script setup lang="ts">'),
    (re.compile(r"\balert\s*\("), "alert() found — use Toast component"),
    (re.compile(r"\bconfirm\s*\("), "confirm() found — use ConfirmDialog"),
]


def static_check_impl(file_path: str, content: str, file_type: str, layer: str) -> list[dict]:
    """Single-file regex validation, scoped to the file's layer."""
    rules = _BACKEND_RULES if layer == "backend" else _FRONTEND_RULES
    issues: list[dict] = []
    for pattern, msg in rules:
        if pattern.search(content):
            issues.append({"file_path": file_path, "issue": msg})
    return issues


def validate_sql_impl(sql: str) -> list[dict]:
    """Validate db_init_sql: each non-empty statement line group must end with ';'."""
    issues: list[dict] = []
    # crude: count CREATE/INSERT/ALTER statements vs semicolons
    statements = re.findall(r"\b(CREATE|INSERT|ALTER|UPDATE|DELETE)\b", sql, re.IGNORECASE)
    semicolons = sql.count(";")
    if statements and semicolons < len(statements):
        issues.append({
            "file_path": "db_init.sql",
            "issue": f"SQL missing semicolon: {len(statements)} statement(s) but {semicolons} ';'",
        })
    return issues
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_tools.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/tools.py tests/graph/test_tools.py
git commit -m "feat(codegen): add static_check + validate_sql core functions"
```

---

## Task 5: 조회 도구 코어 — cross_check / lookup_class / get_dto_fields / list_generated_files (tools.py 2부)

**Files:**
- Modify: `backend/app/llm/graph/tools.py` (append)
- Test: `backend/tests/graph/test_tools.py` (append)

설계 참조: `cross_check`는 contract 대조 + 파일 간 정합성. `lookup_class`/`get_dto_fields`는 **생성된 파일만** 본다.

- [ ] **Step 1: Write the failing test (append)**

`backend/tests/graph/test_tools.py`에 추가:

```python
from app.llm.graph.tools import (
    cross_check_impl, lookup_class_impl, get_dto_fields_impl, list_generated_files_impl,
)

_DTO = {
    "file_path": "CpmsEduResDto.java", "file_type": "dto_response", "layer": "backend",
    "wave": 1, "status": "ok", "status_log": "",
    "content": "public class CpmsEduResDto { private String eduPgmNm; private Integer cnt; }",
}
_SVC = {
    "file_path": "CpmsEduServiceImpl.java", "file_type": "service_impl", "layer": "backend",
    "wave": 3, "status": "ok", "status_log": "",
    "content": "CpmsEduResDto d; d.getEduPgmNm(); d.getMissingField();",
}


def test_get_dto_fields_returns_fields():
    fields = get_dto_fields_impl("CpmsEduResDto", {"CpmsEduResDto.java": _DTO})
    names = {f["name"] for f in fields}
    assert names == {"eduPgmNm", "cnt"}


def test_lookup_class_returns_none_for_unknown():
    assert lookup_class_impl("NoSuch", {"CpmsEduResDto.java": _DTO}) is None


def test_lookup_class_returns_fields_for_known():
    info = lookup_class_impl("CpmsEduResDto", {"CpmsEduResDto.java": _DTO})
    assert info is not None
    assert "eduPgmNm" in {f["name"] for f in info["fields"]}


def test_cross_check_flags_missing_getter_field():
    files = {"CpmsEduResDto.java": _DTO, "CpmsEduServiceImpl.java": _SVC}
    issues = cross_check_impl(files, contract={})
    assert any("getMissingField" in i["issue"] or "MissingField" in i["issue"] for i in issues)


def test_cross_check_clean_when_all_getters_exist():
    svc_ok = {**_SVC, "content": "CpmsEduResDto d; d.getEduPgmNm();"}
    files = {"CpmsEduResDto.java": _DTO, "CpmsEduServiceImpl.java": svc_ok}
    issues = cross_check_impl(files, contract={})
    assert issues == []


def test_list_generated_files_summary():
    out = list_generated_files_impl({"CpmsEduResDto.java": _DTO})
    assert out == [{"file_path": "CpmsEduResDto.java", "file_type": "dto_response",
                    "layer": "backend", "status": "ok"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_tools.py -v`
Expected: FAIL — `ImportError: cannot import name 'cross_check_impl'`

- [ ] **Step 3: Implement (append to tools.py)**

`backend/app/llm/graph/tools.py` 끝에 추가:

```python
# ── DTO field parsing (generated files only) ──
_FIELD_RE = re.compile(r"private\s+\S+(?:<[^>]+>)?\s+(\w+)\s*(?:=[^;]+)?;")
_GETTER_RE = re.compile(r"(\w+)\.get([A-Z]\w*)\s*\(")


def _dto_field_names(content: str) -> list[dict]:
    out = []
    for m in re.finditer(r"private\s+(\S+(?:<[^>]+>)?)\s+(\w+)\s*(?:=[^;]+)?;", content):
        out.append({"name": m.group(2), "type": m.group(1)})
    return out


def get_dto_fields_impl(dto_name: str, files: dict) -> list[dict]:
    """Tool #4: fields of a generated DTO (name+type)."""
    for gf in files.values():
        cls = gf["file_path"].split("/")[-1].replace(".java", "")
        if cls == dto_name:
            return _dto_field_names(gf["content"])
    return []


def lookup_class_impl(class_name: str, files: dict) -> dict | None:
    """Tool #3: lookup a class in generated files only."""
    for gf in files.values():
        cls = gf["file_path"].split("/")[-1].replace(".java", "")
        if cls == class_name:
            methods = re.findall(r"public\s+\S+\s+(\w+)\s*\(", gf["content"])
            return {"class_name": class_name, "file_path": gf["file_path"],
                    "fields": _dto_field_names(gf["content"]), "methods": methods}
    return None


def cross_check_impl(files: dict, contract: dict) -> list[dict]:
    """Tool #2: cross-file consistency. getter calls must reference real DTO fields."""
    # build dto -> set(field names)
    dto_fields: dict[str, set[str]] = {}
    for gf in files.values():
        cls = gf["file_path"].split("/")[-1].replace(".java", "")
        if "Dto" in cls:
            dto_fields[cls] = {f["name"] for f in _dto_field_names(gf["content"])}

    issues: list[dict] = []
    for gf in files.values():
        if not gf["file_path"].endswith(".java") or "Dto" in gf["file_path"]:
            continue
        # map: var name -> dto type   (e.g. "CpmsEduResDto d;")
        var_types: dict[str, str] = {}
        for m in re.finditer(r"(\w+(?:Dto\w*))\s+(\w+)\s*[;=:)]", gf["content"]):
            if m.group(1) in dto_fields:
                var_types[m.group(2)] = m.group(1)
        for m in _GETTER_RE.finditer(gf["content"]):
            var, prop = m.group(1), m.group(2)
            dto = var_types.get(var)
            if not dto:
                continue
            field = prop[0].lower() + prop[1:]
            if field not in dto_fields.get(dto, set()):
                issues.append({
                    "file_path": gf["file_path"],
                    "issue": f"{gf['file_path']} calls get{prop}() but {dto} has no field '{field}'",
                })
    return issues


def list_generated_files_impl(files: dict) -> list[dict]:
    """Tool #7: current generation status summary."""
    return [{"file_path": gf["file_path"], "file_type": gf["file_type"],
             "layer": gf["layer"], "status": gf["status"]} for gf in files.values()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_tools.py -v`
Expected: PASS (12 passed total)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/tools.py tests/graph/test_tools.py
git commit -m "feat(codegen): add cross_check/lookup_class/get_dto_fields/list_files cores"
```

---

## Task 6: @tool 래퍼 + gpt-5.5 클라이언트 (llm.py + tools.py 3부)

**Files:**
- Create: `backend/app/llm/graph/llm.py`
- Modify: `backend/app/llm/graph/tools.py` (append @tool wrappers + TOOL_SPECS)
- Test: `backend/tests/graph/test_llm.py`

설계 참조: gpt-5.5는 Azure Responses API, tool-calling 지원(검증 완료). LangChain ChatModel 미사용 — Responses API `tools` 파라미터에 넘길 JSON 스펙을 만든다. 기존 `_with_retry` 패턴 계승. env는 기존 `CODEX_AZURE_OPENAI_*`를 그대로 읽음(명칭만 코드에서 gpt55).

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_llm.py`:

```python
from app.llm.graph.tools import TOOL_SPECS


def test_tool_specs_has_seven_tools():
    names = {t["name"] for t in TOOL_SPECS}
    assert names == {
        "static_check", "cross_check", "lookup_class",
        "get_dto_fields", "lookup_guide", "validate_sql", "list_generated_files",
    }


def test_tool_specs_responses_api_shape():
    for t in TOOL_SPECS:
        assert t["type"] == "function"
        assert "name" in t and "description" in t and "parameters" in t
        assert t["parameters"]["type"] == "object"


def test_gpt55_client_importable():
    from app.llm.graph.llm import gpt55_client, Gpt55Client
    assert isinstance(gpt55_client, Gpt55Client)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_llm.py -v`
Expected: FAIL — `ImportError: cannot import name 'TOOL_SPECS'`

- [ ] **Step 3a: Append @tool wrappers + TOOL_SPECS to tools.py**

`backend/app/llm/graph/tools.py` 끝에 추가:

```python
# ── Responses API tool specs (gpt-5.5 tool-calling) ──
TOOL_SPECS: list[dict] = [
    {"type": "function", "name": "static_check",
     "description": "Validate a single file against CPMS regex rules. Returns issues.",
     "parameters": {"type": "object",
                    "properties": {"file_path": {"type": "string"},
                                   "content": {"type": "string"},
                                   "file_type": {"type": "string"},
                                   "layer": {"type": "string"}},
                    "required": ["file_path", "content", "file_type", "layer"]}},
    {"type": "function", "name": "cross_check",
     "description": "Cross-file consistency check against contract. Returns mismatches.",
     "parameters": {"type": "object", "properties": {}, "required": []}},
    {"type": "function", "name": "lookup_class",
     "description": "Look up a class in generated files (fields, methods).",
     "parameters": {"type": "object",
                    "properties": {"class_name": {"type": "string"}},
                    "required": ["class_name"]}},
    {"type": "function", "name": "get_dto_fields",
     "description": "Get fields (name+type) of a generated DTO.",
     "parameters": {"type": "object",
                    "properties": {"dto_name": {"type": "string"}},
                    "required": ["dto_name"]}},
    {"type": "function", "name": "lookup_guide",
     "description": "Fetch the latest standard guide sections by topic.",
     "parameters": {"type": "object",
                    "properties": {"layer": {"type": "string"},
                                   "topic": {"type": "string"}},
                    "required": ["layer", "topic"]}},
    {"type": "function", "name": "validate_sql",
     "description": "Validate db_init SQL syntax/rules.",
     "parameters": {"type": "object",
                    "properties": {"sql": {"type": "string"}},
                    "required": ["sql"]}},
    {"type": "function", "name": "list_generated_files",
     "description": "List current generated files (path/type/layer/status).",
     "parameters": {"type": "object", "properties": {}, "required": []}},
]


def dispatch_tool(name: str, args: dict, files: dict, contract: dict) -> object:
    """Execute a tool call by name. Used by the Reviewer ReAct loop (Plan 2)."""
    from app.llm.graph import guides
    if name == "static_check":
        return static_check_impl(args["file_path"], args["content"],
                                 args["file_type"], args["layer"])
    if name == "cross_check":
        return cross_check_impl(files, contract)
    if name == "lookup_class":
        return lookup_class_impl(args["class_name"], files)
    if name == "get_dto_fields":
        return get_dto_fields_impl(args["dto_name"], files)
    if name == "lookup_guide":
        return guides.lookup_guide(args["layer"], args["topic"])
    if name == "validate_sql":
        return validate_sql_impl(args["sql"])
    if name == "list_generated_files":
        return list_generated_files_impl(files)
    raise ValueError(f"unknown tool: {name}")
```

- [ ] **Step 3b: Write llm.py**

`backend/app/llm/graph/llm.py`:

```python
"""gpt-5.5 client (Azure Responses API, tool-calling). Renamed from misnamed 'codex'."""

from __future__ import annotations

import asyncio
import logging

import httpx
import openai

from app.config import settings

logger = logging.getLogger(__name__)

_HTTP_CLIENT = httpx.AsyncClient(verify=False, timeout=httpx.Timeout(timeout=None, connect=30.0))
_RETRYABLE = (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.TimeoutException)
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0


async def _with_retry(coro_factory, label: str):
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY * attempt)
            else:
                logger.error("[gpt55] %s failed after %d: %s", label, _MAX_RETRIES, exc)
    raise last_exc


class Gpt55Client:
    """gpt-5.5 via Azure Responses API. (env still named CODEX_* — read as-is for now.)"""

    def __init__(self) -> None:
        self._available = bool(
            settings.CODEX_AZURE_OPENAI_API_KEY and settings.CODEX_AZURE_OPENAI_ENDPOINT
        )
        if self._available:
            self._client = openai.AsyncAzureOpenAI(
                azure_endpoint=settings.CODEX_AZURE_OPENAI_ENDPOINT,
                api_version=settings.CODEX_AZURE_OPENAI_API_VERSION,
                api_key=settings.CODEX_AZURE_OPENAI_API_KEY,
                http_client=_HTTP_CLIENT,
            )
            self._model = settings.CODEX_AZURE_OPENAI_MODEL_NAME

    async def complete(self, system: str, user: str, max_tokens: int = 16384) -> str:
        resp = await _with_retry(
            lambda: self._client.responses.create(
                model=self._model, instructions=system, input=user,
                max_output_tokens=max_tokens),
            "responses.create")
        return resp.output_text

    async def complete_with_tools(self, system: str, user: str, tools: list[dict],
                                  max_tokens: int = 16384):
        """Single Responses API turn with tools. Returns the raw response (output items)."""
        return await _with_retry(
            lambda: self._client.responses.create(
                model=self._model, instructions=system, input=user,
                tools=tools, max_output_tokens=max_tokens),
            "responses.create+tools")


gpt55_client = Gpt55Client()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_llm.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/llm.py app/llm/graph/tools.py tests/graph/test_llm.py
git commit -m "feat(codegen): add gpt-5.5 client + tool specs + dispatch (rename from codex)"
```

---

## Task 7: 전체 토대 회귀 확인

**Files:** (없음 — 검증만)

- [ ] **Step 1: graph 패키지 전체 테스트**

Run: `cd backend && .venv/bin/pytest tests/graph/ -v`
Expected: PASS (전체 통과 — state 4 + guides 5 + tools 12 + llm 3 = 24)

- [ ] **Step 2: 기존 테스트 회귀 확인 (graph 추가가 기존을 깨지 않았는지)**

Run: `cd backend && .venv/bin/pytest -q`
Expected: 기존 37 + 신규 24 = 61 passed (기존 테스트 무손상)

- [ ] **Step 3: import 사이클 없음 확인**

Run: `cd backend && .venv/bin/python -c "from app.llm.graph import state, guides, tools, llm; print('no import cycle')"`
Expected: `no import cycle`

- [ ] **Step 4: Commit (있을 경우)**

토대 모듈이 모두 통과하면 Plan 1 완료. 추가 변경 없으면 커밋 생략.

---

## Self-Review

**1. Spec coverage (설계 섹션 3·4 대비):**
- CodeGenState + merge_files reducer → Task 2 ✅
- table_info 포함 → guides.load_table_info (Task 3) + state 필드(Task 2) ✅
- 가이드 mtime-fresh + 개선3 매핑 → Task 3 ✅
- 7개 도구 코어 → Task 4(static_check, validate_sql) + Task 5(cross_check, lookup_class, get_dto_fields, list_generated_files) + Task 6(lookup_guide via guides) ✅
- @tool 래퍼/TOOL_SPECS(Responses API shape) + dispatch → Task 6 ✅
- gpt-5.5 클라이언트(명칭정정, tool-calling, 재시도) → Task 6 ✅
- 노드/그래프/SSE/체크포인팅 → **Plan 2~4** (이 플랜 범위 밖, 명시됨)

**2. Placeholder scan:** "TBD/TODO/implement later" 없음. 모든 코드 스텝에 실제 코드 포함. ✅

**3. Type consistency:** `GeneratedFile` 키(file_path/file_type/layer/wave/content/status/status_log)가 state.py 정의와 tools 테스트 fixture에서 일치. `dispatch_tool` 인자(files, contract)가 Plan 2 reviewer가 넘길 시그니처와 일치. `TOOL_SPECS` 이름 7개가 dispatch_tool 분기와 일치. ✅

**참고:** Task 5의 `cross_check_impl`/정규식은 기존 `agents.py`의 방대한 룰 중 핵심만 이식한 최소판이다. 실제 CPMS 룰 전수 이식은 Plan 2 노드 통합 시 점진 확장한다(설계의 "정규식 검증 룰을 도구로 재작성" 계승).
