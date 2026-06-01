# MyBatis Binding Verification (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DAO↔Mapper statement id 불일치 + namespace 오류를 결정론적 파서로 검증·자동교정하는 `mybatis_check` 모듈 + 그래프 노드 + Reviewer 도구를 추가한다.

**Architecture:** 순수 파서 모듈(`mybatis_check.py`, LLM 없음)이 DAO(.java)/Mapper(.xml)를 파싱해 id·namespace를 대조하고, 명백한 1:1 불일치는 결정론적으로 자동교정(DAO가 진실)한다. 그래프는 reviewer 직전 단일 노드 `mybatis_fix`로 자동교정을 적용하고, 잔여 불일치는 Reviewer 도구 `validate_mybatis_binding`으로 LLM에 위임한다.

**Tech Stack:** Python 3.12, LangGraph, pytest (검증 로직은 결정론이라 LLM mock 불필요)

**참조 설계:** `docs/superpowers/specs/2026-06-02-mybatis-binding-verification-design.md`
**선행:** LangGraph 그래프 패키지 존재 (`backend/app/llm/graph/{state,tools,nodes,build,react}.py`)

---

## File Structure

### 신규 생성
- `backend/app/llm/graph/mybatis_check.py` — 순수 파서·검증·자동교정 (parse_dao, parse_mapper, match_pairs, check_binding, autofix_binding)
- `backend/tests/graph/test_mybatis_check.py` — 검증·교정 단위 테스트 + outputs/code 회귀 픽스처
- `backend/tests/graph/test_mybatis_node.py` — mybatis_fix 노드 테스트

### 수정
- `backend/app/llm/graph/build.py` — `mybatis_fix` 노드 추가 + reviewer 라우팅 변경
- `backend/app/llm/graph/tools.py` — `validate_mybatis_binding` 도구(REVIEWER_TOOL_SPECS + dispatch_tool)
- `backend/tests/graph/test_llm.py` — 도구 등록 검증 추가

---

## Task 1: 파서 — parse_dao / parse_mapper

**Files:**
- Create: `backend/app/llm/graph/mybatis_check.py`
- Test: `backend/tests/graph/test_mybatis_check.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_mybatis_check.py`:

```python
from app.llm.graph.mybatis_check import parse_dao, parse_mapper

_DAO = """package com.example.cpms.dao;
import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;
public class CpmsEduRsltLstDaoImpl extends AbstractSqlSessionDaoSupport {
    public java.util.List<X> selectCpmsEduRsltList(X p) {
        return super.selectList("selectCpmsEduRsltList", p);
    }
    public int selectCpmsEduRsltCount(X p) {
        Integer c = super.selectOne("selectCpmsEduRsltCount", p);
        return c == null ? 0 : c;
    }
    public int insertCpmsEduRslt(X p) { return super.insert("insertCpmsEduRslt", p); }
}
"""

_MAPPER = """<?xml version="1.0" encoding="UTF-8" ?>
<mapper namespace="com.example.cpms.mapper.CpmsEduRsltLstMapper">
    <select id="selectCpmsEduRsltLstList" resultType="X">SELECT 1</select>
    <select id="selectCpmsEduRsltCount" resultType="int">SELECT 2</select>
    <insert id="insertCpmsEduRslt">INSERT 3</insert>
</mapper>
"""


def test_parse_dao_extracts_statement_ids_and_namespace():
    info = parse_dao(_DAO)
    assert info["statement_ids"] == {
        "selectCpmsEduRsltList", "selectCpmsEduRsltCount", "insertCpmsEduRslt"}
    assert info["expected_namespace"] == "com.example.cpms.dao.CpmsEduRsltLstDaoImpl"


def test_parse_mapper_extracts_ids_and_namespace():
    info = parse_mapper(_MAPPER)
    assert info["namespace"] == "com.example.cpms.mapper.CpmsEduRsltLstMapper"
    assert info["ids"] == {
        "selectCpmsEduRsltLstList", "selectCpmsEduRsltCount", "insertCpmsEduRslt"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.llm.graph.mybatis_check'`

- [ ] **Step 3: Write mybatis_check.py (parsers)**

`backend/app/llm/graph/mybatis_check.py`:

```python
"""Deterministic MyBatis binding verification (no LLM).

Parses DAO (.java) and Mapper (.xml) to cross-check that every DAO
`super.xxx("id")` call resolves to a Mapper <statement id="id"> and that the
Mapper namespace equals the DaoImpl FQCN. The DAO call string is the source of
truth; obvious 1:1 mismatches are auto-fixed, ambiguous ones are reported.
"""

from __future__ import annotations

import re

# super.{method}("statementId" ...)
_SUPER_CALL_RE = re.compile(
    r'super\s*\.\s*(?:select|selectOne|selectList|insert|update|delete|'
    r'batchUpdate\w*)\s*\(\s*"([A-Za-z0-9_]+)"'
)
_PACKAGE_RE = re.compile(r'\bpackage\s+([a-zA-Z0-9_.]+)\s*;')
_DAO_CLASS_RE = re.compile(r'\bclass\s+(\w*DaoImpl)\b')

_MAPPER_NS_RE = re.compile(r'<mapper\b[^>]*\bnamespace\s*=\s*"([^"]+)"')
_MAPPER_STMT_RE = re.compile(
    r'<(?:select|insert|update|delete)\b[^>]*\bid\s*=\s*"([^"]+)"'
)


def parse_dao(content: str) -> dict:
    """Return {statement_ids: set[str], expected_namespace: str|None}."""
    ids = set(_SUPER_CALL_RE.findall(content))
    pkg_m = _PACKAGE_RE.search(content)
    cls_m = _DAO_CLASS_RE.search(content)
    ns = f"{pkg_m.group(1)}.{cls_m.group(1)}" if pkg_m and cls_m else None
    return {"statement_ids": ids, "expected_namespace": ns}


def parse_mapper(content: str) -> dict:
    """Return {ids: set[str], namespace: str|None}."""
    ns_m = _MAPPER_NS_RE.search(content)
    ids = set(_MAPPER_STMT_RE.findall(content))
    return {"ids": ids, "namespace": ns_m.group(1) if ns_m else None}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/mybatis_check.py tests/graph/test_mybatis_check.py
git commit -m "feat(codegen): add DAO/Mapper parsers for mybatis binding check"
```

---

## Task 2: 파일 매칭 (이름 규칙)

**Files:**
- Modify: `backend/app/llm/graph/mybatis_check.py` (append)
- Test: `backend/tests/graph/test_mybatis_check.py` (append)

- [ ] **Step 1: Append the failing test**

`backend/tests/graph/test_mybatis_check.py`에 추가:

```python
from app.llm.graph.mybatis_check import match_pairs


def _gf(path, ftype, content):
    return {"file_path": path, "file_type": ftype, "layer": "backend",
            "wave": 2, "status": "ok", "status_log": [], "content": content}


def test_match_pairs_by_name_rule():
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", _DAO),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    pairs, unpaired = match_pairs(files)
    assert len(pairs) == 1
    dao_gf, mapper_gf = pairs[0]
    assert dao_gf["file_path"].endswith("DaoImpl.java")
    assert mapper_gf["file_path"].endswith("Mapper.xml")
    assert unpaired == []


def test_match_pairs_reports_unpaired_dao():
    files = {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", _DAO),
    }
    pairs, unpaired = match_pairs(files)
    assert pairs == []
    assert any("FooDaoImpl" in u["issue"] for u in unpaired)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -k match_pairs -q`
Expected: FAIL — `ImportError: cannot import name 'match_pairs'`

- [ ] **Step 3: Implement (append to mybatis_check.py)**

```python
def _basename(file_path: str, suffix: str) -> str | None:
    """'.../CpmsEduRsltLstDaoImpl.java' + 'DaoImpl' -> 'CpmsEduRsltLst'."""
    fname = file_path.replace("\\", "/").split("/")[-1]
    stem = fname.rsplit(".", 1)[0]  # drop extension
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return None


def match_pairs(files: dict) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """Pair DaoImpl ↔ Mapper by name rule. Returns (pairs, unpaired_issues)."""
    daos: dict[str, dict] = {}
    mappers: dict[str, dict] = {}
    for gf in files.values():
        fp = gf["file_path"]
        if fp.endswith("DaoImpl.java"):
            base = _basename(fp, "DaoImpl")
            if base:
                daos[base] = gf
        elif fp.endswith("Mapper.xml"):
            base = _basename(fp, "Mapper")
            if base:
                mappers[base] = gf

    pairs: list[tuple[dict, dict]] = []
    unpaired: list[dict] = []
    for base, dao_gf in daos.items():
        if base in mappers:
            pairs.append((dao_gf, mappers[base]))
        else:
            unpaired.append({"file_path": dao_gf["file_path"],
                             "issue": f"{base}DaoImpl has no matching Mapper xml",
                             "severity": "error"})
    for base, mapper_gf in mappers.items():
        if base not in daos:
            unpaired.append({"file_path": mapper_gf["file_path"],
                             "issue": f"{base}Mapper xml has no matching DaoImpl",
                             "severity": "warning"})
    return pairs, unpaired
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/mybatis_check.py tests/graph/test_mybatis_check.py
git commit -m "feat(codegen): add name-rule pairing for dao/mapper"
```

---

## Task 3: check_binding (3종 issue 탐지)

**Files:**
- Modify: `backend/app/llm/graph/mybatis_check.py` (append)
- Test: `backend/tests/graph/test_mybatis_check.py` (append)

- [ ] **Step 1: Append the failing test**

```python
from app.llm.graph.mybatis_check import check_binding


def test_check_binding_flags_namespace_and_missing_id():
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", _DAO),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    issues = check_binding(files)
    kinds = " ".join(i["issue"] for i in issues)
    # namespace mismatch (mapper says ...mapper.X, dao FQCN is ...dao.XDaoImpl)
    assert "namespace" in kinds.lower()
    # DAO calls selectCpmsEduRsltList but mapper only has selectCpmsEduRsltLstList
    assert "selectCpmsEduRsltList" in kinds
    # warning for unused mapper id
    assert any(i.get("severity") == "warning" for i in issues)


def test_check_binding_clean_when_aligned():
    dao = _DAO.replace('"selectCpmsEduRsltList"', '"selectCpmsEduRsltLstList"')
    mapper = _MAPPER.replace(
        'namespace="com.example.cpms.mapper.CpmsEduRsltLstMapper"',
        'namespace="com.example.cpms.dao.CpmsEduRsltLstDaoImpl"')
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", dao),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", mapper),
    }
    errors = [i for i in check_binding(files) if i.get("severity") != "warning"]
    assert errors == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -k check_binding -q`
Expected: FAIL — `ImportError: cannot import name 'check_binding'`

- [ ] **Step 3: Implement (append to mybatis_check.py)**

```python
def check_binding(files: dict) -> list[dict]:
    """Detect namespace mismatch, missing statements, unused statements."""
    pairs, issues = match_pairs(files)
    issues = list(issues)  # copy unpaired issues

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])

        # 1. namespace must equal DaoImpl FQCN
        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            issues.append({
                "file_path": mapper_gf["file_path"],
                "issue": (f"Mapper namespace '{mapper['namespace']}' != DaoImpl FQCN "
                          f"'{dao['expected_namespace']}'"),
                "severity": "error",
            })

        # 2. DAO calls an id the Mapper does not define (runtime binding failure)
        for sid in sorted(dao["statement_ids"] - mapper["ids"]):
            issues.append({
                "file_path": mapper_gf["file_path"],
                "issue": (f"DAO calls statement '{sid}' but Mapper has no matching "
                          f"<statement id=\"{sid}\">"),
                "severity": "error",
            })

        # 3. Mapper defines an id no DAO calls (warning only)
        for sid in sorted(mapper["ids"] - dao["statement_ids"]):
            issues.append({
                "file_path": mapper_gf["file_path"],
                "issue": f"Mapper statement '{sid}' is not called by any DAO method",
                "severity": "warning",
            })
    return issues
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/mybatis_check.py tests/graph/test_mybatis_check.py
git commit -m "feat(codegen): add check_binding (namespace + id mismatch detection)"
```

---

## Task 4: autofix_binding (보수적 자동교정)

**Files:**
- Modify: `backend/app/llm/graph/mybatis_check.py` (append)
- Test: `backend/tests/graph/test_mybatis_check.py` (append)

설계 참조: namespace 오류는 항상 자동교정. id 불일치는 미사용 1개 ∧ 누락 1개 ∧ 정규화 편집거리 ≤ 0.3일 때만 Mapper id를 DAO 기준으로 rename. 그 외는 교정 안 함.

- [ ] **Step 1: Append the failing test**

```python
from app.llm.graph.mybatis_check import autofix_binding


def test_autofix_fixes_namespace_and_close_id():
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", _DAO),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", _MAPPER),
    }
    fixed, logs = autofix_binding(files)
    mapper_content = fixed["b/CpmsEduRsltLstMapper.xml"]["content"]
    # namespace corrected to DaoImpl FQCN
    assert 'namespace="com.example.cpms.dao.CpmsEduRsltLstDaoImpl"' in mapper_content
    # close id renamed to DAO's expected id
    assert 'id="selectCpmsEduRsltList"' in mapper_content
    assert 'id="selectCpmsEduRsltLstList"' not in mapper_content
    # after fix, no error-level issues remain
    errors = [i for i in check_binding(fixed) if i.get("severity") != "warning"]
    assert errors == []
    assert len(logs) >= 2


def test_autofix_skips_ambiguous_id():
    # DAO needs 'selectFoo' but mapper has TWO unused ids → ambiguous → no rename
    dao = _DAO.replace('"selectCpmsEduRsltList"', '"selectFoo"').replace(
        '"selectCpmsEduRsltCount"', '"selectFoo2"')
    mapper = _MAPPER  # has selectCpmsEduRsltLstList + selectCpmsEduRsltCount + insert...
    files = {
        "a/CpmsEduRsltLstDaoImpl.java": _gf("a/CpmsEduRsltLstDaoImpl.java", "dao_impl", dao),
        "b/CpmsEduRsltLstMapper.xml": _gf("b/CpmsEduRsltLstMapper.xml", "mapper_xml", mapper),
    }
    fixed, logs = autofix_binding(files)
    # 'selectFoo' is far from any mapper id → left for reviewer
    remaining = check_binding(fixed)
    assert any("selectFoo" in i["issue"] for i in remaining)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -k autofix -q`
Expected: FAIL — `ImportError: cannot import name 'autofix_binding'`

- [ ] **Step 3: Implement (append to mybatis_check.py)**

```python
_EDIT_DISTANCE_THRESHOLD = 0.3  # normalized; ≤ this is "obvious variant"


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _normalized_distance(a: str, b: str) -> float:
    m = max(len(a), len(b))
    return _edit_distance(a, b) / m if m else 0.0


def autofix_binding(files: dict) -> tuple[dict, list[str]]:
    """Apply deterministic fixes for obvious 1:1 mismatches. DAO is source of truth.

    Returns (fixed_files_copy, log_lines). Ambiguous mismatches are left untouched
    for the reviewer.
    """
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs: list[str] = []
    pairs, _ = match_pairs(fixed)

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])
        content = mapper_gf["content"]

        # (a) namespace → DaoImpl FQCN (always obvious)
        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            content = re.sub(
                r'(<mapper\b[^>]*\bnamespace\s*=\s*")[^"]+(")',
                lambda m: m.group(1) + dao["expected_namespace"] + m.group(2),
                content, count=1,
            )
            logs.append(f"{mapper_gf['file_path']}: namespace → {dao['expected_namespace']}")

        # (b) 1:1 close-variant id rename (mapper id → dao id)
        missing = sorted(dao["statement_ids"] - mapper["ids"])      # dao wants, mapper lacks
        unused = sorted(mapper["ids"] - dao["statement_ids"])       # mapper has, dao ignores
        if len(missing) == 1 and len(unused) == 1:
            want, have = missing[0], unused[0]
            if _normalized_distance(want, have) <= _EDIT_DISTANCE_THRESHOLD:
                content = re.sub(
                    rf'(\bid\s*=\s*"){re.escape(have)}(")',
                    lambda m: m.group(1) + want + m.group(2),
                    content, count=1,
                )
                logs.append(f"{mapper_gf['file_path']}: statement id '{have}' → '{want}'")

        fixed[mapper_gf["file_path"]] = {**mapper_gf, "content": content}

    return fixed, logs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/mybatis_check.py tests/graph/test_mybatis_check.py
git commit -m "feat(codegen): add conservative autofix_binding (namespace + close-id rename)"
```

---

## Task 5: 회귀 픽스처 — outputs/code 실결함 고정

**Files:**
- Modify: `backend/tests/graph/test_mybatis_check.py` (append)

설계 참조: 실제로 발견된 결함(`selectCpmsEduRsltList` ↔ `selectCpmsEduRsltLstList` + 틀린 namespace)을 픽스처로 박아 "다시는 안 통과"를 영구 보장.

- [ ] **Step 1: Append the regression test**

```python
# Real defect captured from outputs/code (DAO call vs Mapper id, wrong namespace).
_REAL_DAO = """package com.example.cpms.dao;
import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;
public class CpmsEduRsltLstDaoImpl extends AbstractSqlSessionDaoSupport {
    public java.util.List<X> selectCpmsEduRsltList(X p) {
        return super.selectList("selectCpmsEduRsltList", p);
    }
    public int selectCpmsEduRsltCount(X p) {
        Integer c = super.selectOne("selectCpmsEduRsltCount", p);
        return c == null ? 0 : c;
    }
}
"""

_REAL_MAPPER = """<?xml version="1.0" encoding="UTF-8" ?>
<mapper namespace="com.example.cpms.mapper.CpmsEduRsltLstMapper">
    <select id="selectCpmsEduRsltLstList" resultType="X">SELECT 1</select>
    <select id="selectCpmsEduRsltLstCount" resultType="int">SELECT 2</select>
</mapper>
"""


def test_regression_outputs_code_defect_is_fixed():
    files = {
        "x/CpmsEduRsltLstDaoImpl.java": _gf("x/CpmsEduRsltLstDaoImpl.java", "dao_impl", _REAL_DAO),
        "y/CpmsEduRsltLstMapper.xml": _gf("y/CpmsEduRsltLstMapper.xml", "mapper_xml", _REAL_MAPPER),
    }
    # before: errors present
    before = [i for i in check_binding(files) if i.get("severity") != "warning"]
    assert len(before) >= 2  # namespace + at least one missing id

    fixed, logs = autofix_binding(files)
    after = [i for i in check_binding(fixed) if i.get("severity") != "warning"]
    assert after == [], f"unresolved after autofix: {after}"
    mc = fixed["y/CpmsEduRsltLstMapper.xml"]["content"]
    assert 'namespace="com.example.cpms.dao.CpmsEduRsltLstDaoImpl"' in mc
    assert 'id="selectCpmsEduRsltList"' in mc
    assert 'id="selectCpmsEduRsltCount"' in mc
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -k regression -q`
Expected: PASS — autofix가 namespace + 두 id(Lst 철자 차이) 모두 교정

만약 두 id 동시 불일치가 "1:1" 조건(missing==1 & unused==1)에 안 걸려 실패하면: 이 케이스는 missing 2개·unused 2개라 현재 autofix가 건너뜀. 그 경우 Step 3로 다중 1:1 매칭을 보강.

- [ ] **Step 3: (필요 시) 다중 close-variant 매칭 보강**

`autofix_binding`의 id rename 블록을 "missing/unused를 1:1 그리디 매칭"으로 확장 — 각 missing에 대해 unused 중 정규화 거리 최소이고 ≤ threshold인 것을 유일 매칭으로 연결, 매칭이 충돌(같은 unused에 2개 missing)하면 건너뜀:

```python
        # (b') greedy 1:1 close-variant matching (handles multiple aligned renames)
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
                content = re.sub(
                    rf'(\bid\s*=\s*"){re.escape(best)}(")',
                    lambda m, w=want: m.group(1) + w + m.group(2),
                    content, count=1,
                )
                logs.append(f"{mapper_gf['file_path']}: statement id '{best}' → '{want}'")
```

(이 블록으로 Step 1의 단일 `len==1` 블록을 대체. 단일 케이스도 이 그리디가 포함하므로 Task 4 테스트도 계속 통과.)

- [ ] **Step 4: Run full module test**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_check.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/mybatis_check.py tests/graph/test_mybatis_check.py
git commit -m "test(codegen): pin outputs/code binding defect as regression + multi-rename autofix"
```

---

## Task 6: mybatis_fix 그래프 노드

**Files:**
- Modify: `backend/app/llm/graph/build.py`
- Test: `backend/tests/graph/test_mybatis_node.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/graph/test_mybatis_node.py`:

```python
from app.llm.graph.build import mybatis_fix

_DAO = """package com.example.cpms.dao;
public class FooDaoImpl extends Base {
    public int selectFooList(X p) { return super.selectList("selectFooList", p); }
}
"""
_MAPPER_BAD = """<mapper namespace="com.example.cpms.mapper.FooMapper">
    <select id="selectFooLst">SELECT 1</select>
</mapper>
"""


def _gf(path, ftype, content):
    return {"file_path": path, "file_type": ftype, "layer": "backend",
            "wave": 2, "status": "ok", "status_log": [], "content": content}


def test_mybatis_fix_node_corrects_and_reports():
    state = {"files": {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", _DAO),
        "b/FooMapper.xml": _gf("b/FooMapper.xml", "mapper_xml", _MAPPER_BAD),
    }}
    out = mybatis_fix(state)
    mc = out["files"]["b/FooMapper.xml"]["content"]
    assert 'namespace="com.example.cpms.dao.FooDaoImpl"' in mc
    assert 'id="selectFooList"' in mc
    # events include a MYBATIS-FIX log
    assert any("MYBATIS-FIX" in e.get("line", "") for e in out["events"])


def test_mybatis_fix_node_clean_input_noop():
    dao = """package p; public class FooDaoImpl extends B {
        public int x(X p){ return super.selectList("selectFoo", p); } }"""
    mapper = '<mapper namespace="p.FooDaoImpl"><select id="selectFoo">S</select></mapper>'
    state = {"files": {
        "a/FooDaoImpl.java": _gf("a/FooDaoImpl.java", "dao_impl", dao),
        "b/FooMapper.xml": _gf("b/FooMapper.xml", "mapper_xml", mapper),
    }}
    out = mybatis_fix(state)
    # no error-level open_issues
    errs = [i for i in out.get("open_issues", []) if i.get("severity") != "warning"]
    assert errs == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_node.py -q`
Expected: FAIL — `ImportError: cannot import name 'mybatis_fix'`

- [ ] **Step 3: Add mybatis_fix to build.py**

`backend/app/llm/graph/build.py` 상단 import에 추가:

```python
from app.llm.graph.mybatis_check import autofix_binding, check_binding
```

`make_checkpointer` 위(또는 `_wave_gate` 아래)에 추가:

```python
def mybatis_fix(state: dict) -> dict:
    """Deterministic DAO↔Mapper binding autofix before the reviewer (no LLM)."""
    files = dict(state.get("files", {}))
    try:
        fixed_files, fix_logs = autofix_binding(files)
        remaining = check_binding(fixed_files)
    except Exception as e:  # verification is a safety net, never a blocker
        return {"events": [{"type": "log", "line": f"[MYBATIS] error: {e}"}]}
    events = [{"type": "log", "line": f"[MYBATIS-FIX] {log}"} for log in fix_logs]
    errors = [i for i in remaining if i.get("severity") != "warning"]
    if errors:
        events.append({"type": "log",
                       "line": f"[MYBATIS] {len(errors)} binding issue(s) left for reviewer"})
    return {"files": fixed_files, "events": events, "open_issues": remaining}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_mybatis_node.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/build.py tests/graph/test_mybatis_node.py
git commit -m "feat(codegen): add mybatis_fix graph node (autofix before reviewer)"
```

---

## Task 7: 그래프 라우팅 — mybatis_fix를 reviewer 앞에 삽입

**Files:**
- Modify: `backend/app/llm/graph/build.py`
- Test: `backend/tests/graph/test_build.py` (기존, 컴파일 확인)

설계 참조: `_route_waves`가 waves 소진 시 "reviewer"를 반환하던 것을 "mybatis_fix"로 바꾸고, `mybatis_fix → reviewer` 엣지 추가.

- [ ] **Step 1: build.py 노드/엣지 등록**

`build_graph` 안에서 노드 등록 추가 (reviewer 등록 근처):

```python
    g.add_node("mybatis_fix", mybatis_fix)
```

그리고 `mybatis_fix → reviewer` 엣지 추가 (`g.add_edge("reviewer", END)` 위):

```python
    g.add_edge("mybatis_fix", "reviewer")
```

- [ ] **Step 2: _route_waves가 mybatis_fix로 가도록 변경**

`_route_waves`에서 `return "reviewer"`를 `return "mybatis_fix"`로 변경. 그리고 conditional edges의 목적지 목록에 "mybatis_fix" 추가:

기존:
```python
    if wave > MAX_WAVE:
        return "reviewer"
```
변경:
```python
    if wave > MAX_WAVE:
        return "mybatis_fix"
```

`add_conditional_edges` 두 곳의 목적지 리스트를 `["generate_file", "wave_gate", "reviewer"]` → `["generate_file", "wave_gate", "mybatis_fix"]`로 변경 (planner 라우팅과 wave_gate 라우팅 모두).

- [ ] **Step 3: 그래프 컴파일 확인**

Run: `cd backend && .venv/bin/python -c "from app.llm.graph import build; build.build_graph(checkpointer=None); print('ok')"`
Expected: `ok`

- [ ] **Step 4: 오프라인 compile 테스트**

Run: `cd backend && .venv/bin/pytest tests/graph/test_build.py::test_build_graph_compiles -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/build.py
git commit -m "feat(codegen): route waves → mybatis_fix → reviewer"
```

---

## Task 8: Reviewer 도구 validate_mybatis_binding

**Files:**
- Modify: `backend/app/llm/graph/tools.py`
- Test: `backend/tests/graph/test_llm.py` (append)

설계 참조: 잔여 불일치를 Reviewer가 도구로 탐지. 읽기 전용 → REVIEWER_TOOL_SPECS에만 추가(TOOL_SPECS 불변), dispatch_tool에 분기.

- [ ] **Step 1: Append the failing test**

`backend/tests/graph/test_llm.py`에 추가:

```python
def test_validate_mybatis_binding_reviewer_only():
    from app.llm.graph.tools import TOOL_SPECS, REVIEWER_TOOL_SPECS
    assert "validate_mybatis_binding" not in {t["name"] for t in TOOL_SPECS}
    assert "validate_mybatis_binding" in {t["name"] for t in REVIEWER_TOOL_SPECS}


def test_dispatch_validate_mybatis_binding():
    from app.llm.graph.tools import dispatch_tool
    dao = """package p; public class FooDaoImpl extends B {
        public int x(X q){ return super.selectList("selectFoo", q); } }"""
    mapper = '<mapper namespace="p.WrongNs"><select id="selectBar">S</select></mapper>'
    files = {
        "a/FooDaoImpl.java": {"file_path": "a/FooDaoImpl.java", "file_type": "dao_impl",
                              "layer": "backend", "wave": 2, "status": "ok",
                              "status_log": [], "content": dao},
        "b/FooMapper.xml": {"file_path": "b/FooMapper.xml", "file_type": "mapper_xml",
                            "layer": "backend", "wave": 2, "status": "ok",
                            "status_log": [], "content": mapper},
    }
    result = dispatch_tool("validate_mybatis_binding", {}, files, {})
    assert isinstance(result, list)
    assert any(i.get("severity") == "error" for i in result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/graph/test_llm.py -k mybatis -q`
Expected: FAIL — assertion (도구 미등록) 또는 dispatch ValueError

- [ ] **Step 3: tools.py에 도구 등록**

`tools.py`의 `_APPLY_FIX_SPEC` 정의 아래, `REVIEWER_TOOL_SPECS` 정의 위에 추가:

```python
_VALIDATE_MYBATIS_SPEC = {
    "type": "function", "name": "validate_mybatis_binding",
    "description": "Check DAO↔Mapper statement-id and namespace binding across all "
                   "generated files. Returns binding issues (run apply_fix to fix).",
    "parameters": {"type": "object", "properties": {}, "required": []},
}
```

`REVIEWER_TOOL_SPECS` 정의를 변경:

```python
REVIEWER_TOOL_SPECS: list[dict] = TOOL_SPECS + [_APPLY_FIX_SPEC, _VALIDATE_MYBATIS_SPEC]
```

`dispatch_tool` 안에 분기 추가 (`list_generated_files` 분기 아래, `raise` 위):

```python
    if name == "validate_mybatis_binding":
        from app.llm.graph.mybatis_check import check_binding
        return check_binding(files)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/graph/test_llm.py -q`
Expected: PASS (기존 + 신규 2개)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/llm/graph/tools.py tests/graph/test_llm.py
git commit -m "feat(codegen): expose validate_mybatis_binding as reviewer tool"
```

---

## Task 9: 회귀 + 실 LLM e2e

**Files:** (없음 — 검증만)

- [ ] **Step 1: graph 비-LLM 전체**

Run: `cd backend && .venv/bin/pytest tests/graph/ -m "not llm" -q`
Expected: PASS (기존 + mybatis_check 9 + mybatis_node 2 + llm 도구 2)

- [ ] **Step 2: import 사이클 / 그래프 빌드**

Run: `cd backend && .venv/bin/python -c "from app.llm.graph import build, mybatis_check, tools; build.build_graph(checkpointer=None); print('ok')"`
Expected: `ok`

- [ ] **Step 3: 실 LLM e2e (mybatis_fix 삽입 후 정상 종료)**

Run: `cd backend && .venv/bin/pytest tests/graph/test_build.py::test_end_to_end_real_llm -q`
Expected: PASS (키 있을 때; 없으면 skip). mybatis_fix 노드가 끼어도 그래프가 complete까지 도달.

- [ ] **Step 4: 기존 회귀 무손상**

Run: `cd backend && .venv/bin/pytest tests/ --ignore=tests/graph -m "not llm" -q 2>&1 | tail -3`
Expected: 사전-실패(mockup 12개) 외 신규 실패 없음.

---

## Self-Review

**1. Spec coverage (설계 6개 섹션 대비):**
- 컴포넌트(mybatis_check + node + tool) → Task 1~8 ✅
- 파싱 → Task 1 ✅ / 매칭 → Task 2 ✅ / 검증 3종 → Task 3 ✅ / 자동교정 보수적 → Task 4 ✅
- 진실=DAO, namespace=FQCN, 미사용=warning → Task 3·4 ✅
- 회귀 픽스처(outputs/code) → Task 5 ✅
- 그래프 통합(reviewer 직전 단일 노드) → Task 6·7 ✅
- Reviewer 도구(REVIEWER_TOOL_SPECS만) → Task 8 ✅
- 에러 처리(try/except, 보조 안전망) → Task 6 mybatis_fix ✅
- 테스트 전략 + e2e → Task 9 ✅

**2. Placeholder scan:** "TBD/TODO" 없음. Task 5 Step 3은 "필요 시 보강"이지만 실제 코드 제공(다중 그리디 매칭) — placeholder 아님. 모든 코드 스텝에 실제 코드. ✅

**3. Type consistency:**
- `parse_dao` → `{statement_ids, expected_namespace}`, `parse_mapper` → `{ids, namespace}` 키가 Task 1 정의와 Task 3·4 사용에서 일치 ✅
- `match_pairs` → `(pairs, unpaired)` 튜플, `check_binding` → `list[issue{file_path,issue,severity}]`, `autofix_binding` → `(fixed_files, logs)` 시그니처가 Task 2~6 전반 일치 ✅
- `mybatis_fix(state)` → `{files, events, open_issues}` 반환이 build.py reducer(merge_files/add)와 호환 ✅
- 도구명 `validate_mybatis_binding`이 Task 8 spec·dispatch·test에서 일치 ✅
- GeneratedFile 키(file_path/file_type/layer/wave/content/status/status_log)가 픽스처·노드에서 일치 ✅

**알려진 메모:** Task 5의 다중-rename 그리디 매칭이 Task 4의 단일 `len==1` 블록을 대체한다. Task 4는 단일 케이스로 먼저 구현하고 Task 5에서 다중으로 일반화하는 점진 순서 — 두 테스트 모두 최종 그리디 구현에서 통과한다.
