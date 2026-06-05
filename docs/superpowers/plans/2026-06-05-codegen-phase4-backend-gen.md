# Codegen Rewrite — Phase 4: Backend Generators + Static Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`). Python tasks are TDD with scripted fake LLM (no real creds); one skeleton task verifies via Docker.

**Goal:** Build the backend code generators that consume the Phase-2 Contract+bindings — DTOs, Mapper XML, Service (LLM via gpt-5.5) and DAO (deterministic template) — plus a guide-driven static validation over the generated set. Additive nodes (not wired into the live graph; wiring + the Docker compile-in-the-loop are Phase 6).

**Architecture:** `gen_backend.py` holds: deterministic `render_dao()` (per BackendGuide §4.4.3, no LLM) and LLM generators `gen_dtos`/`gen_mapper`/`gen_service` that build a prompt from (contract, bindings, dependency file contents, the whole BackendGuide via `guides.load_guide_for_file_type`, 테이블정보) and call `gpt55_client`. `backend_validate.py` reuses `tools.static_check_impl` (§11.5/§11.6 regexes) + a cross-file binding check (DAO method ↔ Mapper statement-id ↔ namespace). A tiny skeleton task adds the batch DAO base method the template needs.

**Tech Stack:** Python 3.11+, pytest, `gpt55_client`, reused `naming`/`guides`/`tools`/`_text`/`prompts.GENERATOR_SYSTEM`. Docker (one skeleton compile check).

---

## Test harness (reuse)
```bash
export DUMMY_ENV='AZURE_OPENAI_API_KEY=dummy AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com GPT55_AZURE_OPENAI_API_KEY=dummy GPT55_AZURE_OPENAI_ENDPOINT=https://dummy.openai.azure.com AOAI_API_KEY=dummy AOAI_ENDPOINT=https://dummy.openai.azure.com OPENAI_API_KEY=dummy ANTHROPIC_API_KEY=dummy'
```
Run from `backend`: `source .venv/bin/activate && env $DUMMY_ENV pytest <file> -v`.

## Reusable building blocks (verified)
- `naming._OP_TABLE`: `{selectList:(select,List,select), selectOne:(select,'',select), count:(select,Count,select), insert:(insert,'',insert), update:(update,'',update), delete:(delete,'',delete)}`. `naming.statement_id(op, screen)`, `naming.java_type(t)` (`number→Integer`, `string/date→String`).
- Vendored `AbstractSqlSessionDaoSupport` (skeleton): has `selectList/selectOne/insert/update/delete(statementId, param)`. **Lacks** `batchUpdateReturnSumAffectedRows` → added in Task 0.
- `guides.load_guide_for_file_type(file_type)` → whole BackendGuide for backend types. `guides.load_table_info()` → 테이블정보.md.
- `tools.static_check_impl(path, content, file_type, layer)` (backend §11.5/§11.6 regexes), `tools.cross_check_impl(files, contract)`.
- `prompts.GENERATOR_SYSTEM`, `_text.strip_fences`.
- Contract/bindings shape: `contract["bindings"]` has `paths`, `statement_ids`, `dao_methods`, `namespace`, `packages`; `contract["fields"].{request,response}`, `contract["table"].columns`, `contract["identity"].class_name`, `contract["ops"]`.

---

## Task 0: Add batch DAO base method to the skeleton (Docker-verified)

**File:** `skeleton/backend/src/main/java/aondev/framework/dao/mybatis/support/AbstractSqlSessionDaoSupport.java`

- [ ] **Step 1:** Add a protected batch method the DAO template (Task 1) calls for batch update/delete (guide §4.4.3). Insert alongside the existing methods:
```java
    protected int batchUpdateReturnSumAffectedRows(String statementId, java.util.List<?> parameter) {
        int sum = 0;
        if (parameter != null) {
            for (Object item : parameter) {
                sum += sqlSession.update(statementId, item);
            }
        }
        return sum;
    }
```
(Place it after the `delete` method, before the closing brace. Keep style consistent with the file.)
- [ ] **Step 2:** Verify the skeleton still compiles (Docker, no local JVM), from repo root:
```bash
docker run --rm -v "$PWD/skeleton/backend":/app -w /app maven:3.9-eclipse-temurin-21 mvn -B -DskipTests compile
```
Expected `BUILD SUCCESS`.
- [ ] **Step 3:** Commit:
```bash
git add skeleton/backend/src/main/java/aondev/framework/dao/mybatis/support/AbstractSqlSessionDaoSupport.java
git commit -m "$(printf 'feat(skeleton): add batchUpdateReturnSumAffectedRows to DAO base (guide §4.4.3)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 1: Deterministic DAO template (`gen_backend.py` :: render_dao)

**Files:** Create `backend/app/llm/graph/gen_backend.py`, `backend/tests/graph/test_gen_dao.py`.

Per the locked decision, DAO is pure-deterministic from bindings (no LLM). §4.4.3 op→(super method, return type, param type):

| op | super call | return | param |
|----|-----------|--------|-------|
| selectList | `super.selectList(id, p)` | `List<{Res}>` | `{Req} p` |
| count | `super.selectOne(id, p)` | `int` | `{Req} p` |
| selectOne | `super.selectOne(id, p)` | `{Res}` | `{Req} p` |
| insert | `super.insert(id, p)` | `int` | `{Req} p` |
| update | `super.batchUpdateReturnSumAffectedRows(id, p)` | `int` | `List<{Req}> p` |
| delete | `super.batchUpdateReturnSumAffectedRows(id, p)` | `int` | `List<{Req}> p` |

- [ ] **Step 1: Write failing tests** — create `backend/tests/graph/test_gen_dao.py`:
```python
from app.llm.graph.gen_backend import render_dao

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
    "bindings": {
        "statement_ids": ["selectCpmsEduPondgLstList", "selectCpmsEduPondgLstCount",
                          "selectCpmsEduPondgLst", "insertCpmsEduPondgLst",
                          "updateCpmsEduPondgLst", "deleteCpmsEduPondgLst"],
        "packages": {"dao_impl": "biz.edu.dao",
                     "dto_request": "biz.edu.dto.request",
                     "dto_response": "biz.edu.dto.response"},
        "paths": {"dao_impl": "src/main/java/biz/edu/dao/CpmsEduPondgLstDaoImpl.java"},
    },
}


def test_render_dao_header_and_class():
    src = render_dao(_CONTRACT)
    assert "package biz.edu.dao;" in src
    assert "import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;" in src
    assert "import biz.edu.dto.request.CpmsEduPondgLstReqDto;" in src
    assert "import biz.edu.dto.response.CpmsEduPondgLstResDto;" in src
    assert "@Repository" in src
    assert "public class CpmsEduPondgLstDaoImpl extends AbstractSqlSessionDaoSupport {" in src


def test_render_dao_methods_per_op():
    src = render_dao(_CONTRACT)
    # list -> List<Res>, super.selectList
    assert ("public java.util.List<CpmsEduPondgLstResDto> selectCpmsEduPondgLstList("
            "CpmsEduPondgLstReqDto param)") in src
    assert 'return super.selectList("selectCpmsEduPondgLstList", param);' in src
    # count -> int, super.selectOne
    assert "public int selectCpmsEduPondgLstCount(CpmsEduPondgLstReqDto param)" in src
    assert 'return super.selectOne("selectCpmsEduPondgLstCount", param);' in src
    # selectOne -> Res, super.selectOne
    assert "public CpmsEduPondgLstResDto selectCpmsEduPondgLst(CpmsEduPondgLstReqDto param)" in src
    # insert -> int, super.insert
    assert 'return super.insert("insertCpmsEduPondgLst", param);' in src
    # update/delete -> batch, List param
    assert ("public int updateCpmsEduPondgLst("
            "java.util.List<CpmsEduPondgLstReqDto> param)") in src
    assert 'return super.batchUpdateReturnSumAffectedRows("updateCpmsEduPondgLst", param);' in src
    assert 'return super.batchUpdateReturnSumAffectedRows("deleteCpmsEduPondgLst", param);' in src


def test_render_dao_no_bare_crud_calls():
    # must never emit bare super.insert/update with a non-domain statement id, and
    # method names must be the domain-suffixed statement ids (static_check compliance)
    src = render_dao(_CONTRACT)
    import re
    # every public method name is a statement id
    methods = re.findall(r"public [^\n]+ (\w+)\(", src)
    assert set(methods) == set(_CONTRACT["bindings"]["statement_ids"])
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement `render_dao`** in a new `backend/app/llm/graph/gen_backend.py`:
```python
"""Backend code generators (DAO deterministic; DTO/Mapper/Service via gpt-5.5).

Consumes the Phase-2 Contract + bindings. DAO is a pure template (BackendGuide
§4.4.3) — no LLM. The LLM generators build a prompt from the contract, bindings,
the whole BackendGuide, 테이블정보, and the already-generated dependency files,
then call gpt55_client.
"""

from __future__ import annotations

import json

from app.llm.graph import guides, naming
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import GENERATOR_SYSTEM
from app.llm.graph._text import strip_fences as _strip_fences

# op -> (super method, return type template, param type template)
# {Res}/{Req} are substituted with the DTO class names. List ops take a List param.
_DAO_OP = {
    "selectList": ("selectList", "java.util.List<{Res}>", "{Req} param"),
    "count":      ("selectOne", "int", "{Req} param"),
    "selectOne":  ("selectOne", "{Res}", "{Req} param"),
    "insert":     ("insert", "int", "{Req} param"),
    "update":     ("batchUpdateReturnSumAffectedRows", "int", "java.util.List<{Req}> param"),
    "delete":     ("batchUpdateReturnSumAffectedRows", "int", "java.util.List<{Req}> param"),
}


def render_dao(contract: dict) -> str:
    """Deterministic DaoImpl source from the contract + bindings (§4.4.3)."""
    ident = contract["identity"]
    screen = ident["class_name"]
    b = contract["bindings"]
    pkgs = b["packages"]
    dao_pkg = pkgs.get("dao_impl", f"biz.{ident['module']}.dao")
    req_pkg = pkgs.get("dto_request", f"biz.{ident['module']}.dto.request")
    res_pkg = pkgs.get("dto_response", f"biz.{ident['module']}.dto.response")
    req, res = f"{screen}ReqDto", f"{screen}ResDto"

    methods = []
    for op in (contract.get("ops") or naming.ops_for_screen_type(contract.get("archetype", "list"))):
        spec = _DAO_OP.get(op)
        if not spec:
            continue
        super_m, ret_t, param_t = spec
        sid = naming.statement_id(op, screen)
        ret = ret_t.replace("{Res}", res).replace("{Req}", req)
        param = param_t.replace("{Res}", res).replace("{Req}", req)
        methods.append(
            f"    public {ret} {sid}({param}) {{\n"
            f'        return super.{super_m}("{sid}", param);\n'
            f"    }}")

    return (
        f"package {dao_pkg};\n\n"
        f"import org.springframework.stereotype.Repository;\n"
        f"import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;\n"
        f"import {req_pkg}.{req};\n"
        f"import {res_pkg}.{res};\n\n"
        f"@Repository\n"
        f"public class {screen}DaoImpl extends AbstractSqlSessionDaoSupport {{\n\n"
        + "\n\n".join(methods)
        + "\n}\n"
    )
```

- [ ] **Step 4: Run → PASS (3 passed).**
- [ ] **Step 5: Commit** (`git add backend/app/llm/graph/gen_backend.py backend/tests/graph/test_gen_dao.py` + the standard trailer; message `feat(codegen): deterministic DAO template (§4.4.3)`).

---

## Task 2: LLM generators — DTO, Mapper, Service (`gen_backend.py`)

**Files:** extend `gen_backend.py`; create `backend/tests/graph/test_gen_backend_llm.py`.

Each generator builds a prompt and calls `gpt55_client.complete`. Tests use a scripted fake client and assert (a) the prompt contains the required grounding (bindings identifiers, guide, deps) and (b) the returned file dict has the right path + fence-stripped content.

- [ ] **Step 1: Write failing tests** — `backend/tests/graph/test_gen_backend_llm.py`:
```python
import pytest
from app.llm.graph import gen_backend as gb

pytestmark = pytest.mark.asyncio

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm", "db_type": "varchar(100)",
                           "java_type": "String", "searchable": True}]},
    "fields": {"request": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String",
                            "filter": "ILIKE"}],
               "response": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String"}]},
    "bindings": {
        "statement_ids": ["selectCpmsEduPondgLstList", "selectCpmsEduPondgLstCount",
                          "selectCpmsEduPondgLst", "insertCpmsEduPondgLst",
                          "updateCpmsEduPondgLst", "deleteCpmsEduPondgLst"],
        "namespace": "biz.edu.dao.CpmsEduPondgLstDaoImpl",
        "packages": {"dao_impl": "biz.edu.dao", "dto_request": "biz.edu.dto.request",
                     "dto_response": "biz.edu.dto.response"},
        "paths": {"dto_request": "src/main/java/biz/edu/dto/request/CpmsEduPondgLstReqDto.java",
                  "dto_response": "src/main/java/biz/edu/dto/response/CpmsEduPondgLstResDto.java",
                  "mapper_xml": "src/main/resources/biz/edu/mybatis/mappers/CpmsEduPondgLstMapper.xml",
                  "service_impl": "src/main/java/biz/edu/service/CpmsEduPondgLstServiceImpl.java"},
    },
}


class _Scripted:
    def __init__(self, reply):
        self.reply = reply
        self.last_user = None
    async def complete(self, system, user, max_tokens=16384):
        self.last_user = user
        return self.reply


async def test_gen_dtos_returns_two_files(monkeypatch):
    c = _Scripted("```java\npackage x;\nclass X {}\n```")
    monkeypatch.setattr(gb, "gpt55_client", c)
    out = await gb.gen_dtos(_CONTRACT, guide="GUIDE")
    paths = set(out)
    assert _CONTRACT["bindings"]["paths"]["dto_request"] in paths
    assert _CONTRACT["bindings"]["paths"]["dto_response"] in paths
    # fences stripped
    assert all("```" not in v for v in out.values())


async def test_gen_mapper_prompt_grounds_in_bindings_and_columns(monkeypatch):
    c = _Scripted("<mapper/>")
    monkeypatch.setattr(gb, "gpt55_client", c)
    out = await gb.gen_mapper(_CONTRACT, guide="GUIDE", dtos={"a": "class ReqDto{}"})
    # the mapper file is produced at the bound path
    assert _CONTRACT["bindings"]["paths"]["mapper_xml"] in out
    # prompt grounded in namespace + statement ids + real column + dep DTO
    u = c.last_user
    assert "biz.edu.dao.CpmsEduPondgLstDaoImpl" in u          # namespace
    assert "selectCpmsEduPondgLstList" in u                    # statement id
    assert "emp_nm" in u                                       # real DB column
    assert "GUIDE" in u                                        # guide injected


async def test_gen_service_prompt_grounds_in_dao_methods(monkeypatch):
    c = _Scripted("class S {}")
    monkeypatch.setattr(gb, "gpt55_client", c)
    dao_src = "class CpmsEduPondgLstDaoImpl { public int insertCpmsEduPondgLst(){} }"
    out = await gb.gen_service(_CONTRACT, guide="GUIDE", dao=dao_src,
                               dtos={"a": "class ReqDto{}"})
    assert _CONTRACT["bindings"]["paths"]["service_impl"] in out
    u = c.last_user
    assert "insertCpmsEduPondgLst" in u           # service must call real dao methods
    assert "CpmsEduPondgLst/" in u or "@ServiceId" in u   # ServiceId grounding
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** `gen_dtos`, `gen_mapper`, `gen_service` in `gen_backend.py`. Each: build a `user` prompt that includes the guide, `json.dumps(contract)` (or the relevant slices), the bindings identifiers (paths, statement_ids, namespace, packages), the dependency file contents passed in, and an explicit "Generate file: <path>" instruction; call `gpt55_client.complete(GENERATOR_SYSTEM, user)`; `_strip_fences`; return `{bound_path: content}`. `gen_dtos` makes TWO calls (request, response) or one call returning both — the test only requires both bound paths present with stripped content; implement as two calls returning a 2-entry dict. The prompt MUST literally contain: the namespace, the statement ids, real DB column names (from `contract["table"]["columns"]` / 테이블정보), the passed guide text, and (for service) the dao method names + a ServiceId hint `{class_name}/{method}`. Keep prompts concise but grounded.
- [ ] **Step 4: Run → PASS (3 passed).**
- [ ] **Step 5: Commit** (`feat(codegen): DTO/Mapper/Service LLM generators (bindings-grounded)`).

---

## Task 3: Backend static validation (`backend_validate.py`)

**Files:** Create `backend/app/llm/graph/backend_validate.py`, `backend/tests/graph/test_backend_validate.py`.

Reuse `tools.static_check_impl` per file + a cross-file binding check (every Mapper statement-id in bindings appears in the DAO and the Mapper; DAO method names == statement_ids; Mapper namespace == bindings.namespace).

- [ ] **Step 1: Write failing tests** asserting: (a) a DAO that calls a bare `super.insert("x", p)` via a method NOT named per statement-id is flagged (reuse static_check_impl backend rule for bare DAO base call — note: the deterministic render_dao is clean, but LLM Mapper/Service may drift); (b) a generated file importing `java.util.UUID` is flagged; (c) a Mapper whose `<mapper namespace>` ≠ bindings.namespace is flagged; (d) a clean generated set returns no issues. Write concrete fixtures + asserts (use small inline Java/XML strings).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** `validate_backend(files: dict, contract: dict) -> list[dict]`:
  - for each backend file: `issues += tools.static_check_impl(path, content, file_type, "backend")`.
  - cross-file: parse Mapper `namespace="..."`; if present and != `contract["bindings"]["namespace"]` → issue. For each `statement_ids`: ensure a `<... id="sid">` exists in the mapper content and a `sid(` method exists in the dao content; missing → issue.
  - return list of `{file_path, issue, severity}`.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** (`feat(codegen): backend static + cross-file binding validation`).

---

## Task 4: Regression + integration smoke

- [ ] **Step 1:** `env $DUMMY_ENV pytest -m "not llm" -q` → all green (no regression; new tests added).
- [ ] **Step 2:** Additive check: `git diff --name-only <phase4-base>..HEAD -- backend/app/llm/graph` shows only `gen_backend.py` + `backend_validate.py` new (no edits to `nodes.py`/`build.py`/`naming.py`/`guides.py`/`tools.py`). (Skeleton base method from Task 0 is the only skeleton change.)
- [ ] **Step 3:** Integration smoke `backend/tests/graph/test_phase4_backend.py`: build a contract via `parse_contract` → `plan_and_bind` → `render_dao` → assert the DAO compiles-shaped (package matches bindings, all statement-ids present as methods) and `validate_backend({dao_path: dao_src}, contract)` returns no DAO issues. Commit.

---

## Self-Review
- Spec coverage: spec §5.1 backend staged generation (DTO→Mapper→DAO→Service) → Tasks 1-2; DAO deterministic template (§5.1, decision) → Task 1; backend static-check guide-driven (§6 [4]) → Task 3; batch base method gap → Task 0. Deferred-by-design: backend compile-in-the-loop (§6 [5]) + graph wiring → Phase 6 (noted). `bindings.audit_map` still Phase-6/Mapper-time (the Mapper generator gets audit mapping from the injected BackendGuide §4.7 text for now).
- No placeholders: deterministic DAO fully coded; LLM generators specified by prompt-grounding contract + scripted tests (exact prompt wording is impl detail bounded by tests).
- Type consistency: contract/bindings dict keys match Phase-2 output (`statement_ids`, `namespace`, `packages`, `paths`); `render_dao`/`gen_*` signatures consistent across tasks and tests; `_DAO_OP` ops match `naming._OP_TABLE` keys.
