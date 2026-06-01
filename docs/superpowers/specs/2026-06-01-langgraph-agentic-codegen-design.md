# LangGraph Agentic Code Generation Design

> 코드 생성 파이프라인을 LangGraph `StateGraph`로 전면 재작성한다. 앞단 mockup이 확정한 `spec.md` + Vue SFC + 표준 가이드 md를 입력으로 받아, 계약(contract)을 단일 진실원으로 추출한 뒤 3-wave 병렬 생성 + 단일 Reviewer ReAct 루프로 백엔드/프론트 코드를 생성한다.

## Context

현재 `need-only-prd`의 코드 생성은 `orchestrator.py`(명령형 async generator) + `agents.py`(4913줄, 역할별 클래스)로 구성된 hand-rolled 멀티에이전트다. 에이전트 프레임워크(LangChain/LangGraph)는 쓰지 않으며, LLM tool-calling·MCP도 없다. 모델 호출만 자체 클라이언트(`LLMClient`/`CodexLLMClient`)로 직접 한다.

**리팩토링을 하는 진짜 이유는 "입력 구조가 바뀌었기 때문"이다.** 앞단 mockup 파이프라인이 이제 `spec.md`와 **확정된 Vue SFC(화면 코드)**를 산출한다. 코드 생성 에이전트는 이 둘을 받아 생성해야 하는데, 현재 `FrontendEngineerAgent`는 확정 Vue를 입력으로 받지 않고 spec만 보고 프론트를 처음부터 새로 생성한다 — 앞단에서 확정한 레이아웃/필드가 버려진다. 이 미스매치를 해소하는 것이 1차 목표이고, 그 과정에서 코드 생성 단을 LangGraph 기반 agentic 구조로 전면 재작성한다.

기존 자산은 보존하지 않는다(전면 재작성 허용). 단 검증된 메커니즘(재시도, 정규식 검증 룰, 가이드 로더)은 새 구조에 맞게 계승한다.

## 설계 결정 요약

| 영역 | 결정 |
|------|------|
| 입력 | `spec.md` + 확정 Vue SFC + 표준 가이드 md(동적) + 테이블정보.md |
| 범위 | 전면 재작성 (`orchestrator.py`, `agents.py` 폐기) |
| 오케스트레이션 | LangGraph `StateGraph` |
| LLM 호출 | gpt-5.5 클라이언트 **직접 호출** (LangChain ChatModel 미사용), Responses API tool-calling |
| 모델 | 전 노드 **gpt-5.5** 단일화 (Responses API, tool-calling 검증 완료) |
| Vue 역할 | 골격/참조 — 프론트 다듬기 + 백엔드 생성 양쪽 구동 |
| 흐름 | Contract Extractor → Planner → 3-wave 병렬 생성 → Reviewer(ReAct) |
| 병렬 | 3-wave (leaf → DTO의존 → DAO의존), 같은 wave 동시 실행 |
| wave 생성 | single-shot + `static_check` 정규식 게이트 1회 재생성 |
| Reviewer | **유일한 ReAct 루프** — `cross_check`로 문제 파일 직접 수정, 수렴 + 하드캡 백스톱 |
| 도구 | 7개 (@tool, Reviewer 자율 호출 + wave 그래프 주입 겸용) |
| 가이드 | 매 실행 mtime fresh 로드 / wave엔 매핑 주입(개선3) / Reviewer는 도구 전수검증 |
| SSE | 프론트까지 신규 이벤트 포맷 재설계 (병렬·ReAct 시각화) |
| 체크포인팅 | `AsyncSqliteSaver` 디스크 영속, thread_id = session_id, 실패 지점 재개 |
| 명칭 정정 | "codex" → "gpt-5.5" (현 명칭 오류 수정) |

### 사전 검증 완료 사항
- **gpt-5.5 (Azure Responses API, api_version `2025-04-01-preview`) tool-calling 지원 확인.** 라이브 프로브에서 모델이 `static_check` 함수를 올바른 인자(`{"file_path":"Foo.java"}`)로 호출함을 확인. → Reviewer ReAct 루프 및 도구 호출을 gpt-5.5 단일 경로로 구현 가능.

---

## 1. 전체 아키텍처

```
┌─ React Frontend ────────────────────────────────────────────┐
│  sessionStore.ts ─ 신규 이벤트 핸들러 (wave_start, file_token,│
│    react_step, tool_call, file_fixed ...)                    │
│  CodeGenPanel.tsx ─ wave 병렬 진행 바 + 파일별 토큰 스트리밍  │
│    + Reviewer ReAct 타임라인                                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ SSE (EventSourceResponse 유지)
┌─ FastAPI: routers/codegen.py ───────────────────────────────┐
│  graph.astream_events() → sse_adapter → yield 신규 이벤트    │
│  POST /api/codegen/generate, /api/codegen/resume             │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─ backend/app/llm/graph/ (신규 패키지) ──────────────────────┐
│  state.py        CodeGenState (TypedDict + reducer)          │
│  tools.py        7개 @tool + 결정론적 코어 함수              │
│  nodes.py        순수 async 함수 노드들                      │
│  react.py        Reviewer ReAct 루프 (수렴 + 하드캡)         │
│  build.py        StateGraph 조립 + AsyncSqliteSaver          │
│  sse_adapter.py  astream_events → 신규 SSE 이벤트 변환       │
│  llm.py          gpt-5.5 클라이언트 (Responses API, 명칭정정)│
│  guides.py       가이드 mtime-fresh 로더                     │
└──────────────────────────────────────────────────────────────┘
```

**핵심 원칙:**
1. **LangGraph는 그래프 오케스트레이션·체크포인팅·병렬만 담당.** LLM 호출은 우리 gpt-5.5 클라이언트가 직접(Responses API). LangChain ChatModel 추상화에 묶이지 않는다.
2. **계약(contract)이 단일 진실원.** Contract Extractor가 확정 Vue + spec + 테이블정보에서 추출한 구조화 계약을 이후 모든 노드가 공유 → 프론트-백 불일치를 구조적으로 차단.
3. **agentic은 Reviewer에 집중.** wave 생성은 빠른 single-shot, 자기수정 ReAct는 전체 파일이 모인 Reviewer에서만(cross_check가 fan-in 이후에만 의미 있으므로).

---

## 2. 그래프 토폴로지

```
START → contract_extract(gpt-5.5) → planner(gpt-5.5)
  → [WAVE1: db_init_sql ∥ dto_request ∥ dto_response ∥ vue_types]   (+static_check 게이트)
  → [WAVE2: dao/dao_impl ∥ mapper_xml ∥ vue_page]                   (+static_check 게이트)
  → [WAVE3: service/service_impl]                                   (+static_check 게이트)
  → reviewer(ReAct: 7개 도구, 직접수정, 수렴+하드캡)
  → END → SSE graph_complete
```

### wave 경계 (3-wave) 근거

| Wave | 파일 타입 | 의존성 | 근거 |
|------|----------|--------|------|
| 1 (leaf) | `db_init_sql`, `dto_request`, `dto_response`, `vue_types` | 없음 (계약에서 직접 도출) | 상호 무의존 → 100% 병렬 안전. 가장 빠른 wave. |
| 2 | `dao`/`dao_impl`, `mapper_xml`, `vue_page` | wave1의 DTO/types | DAO는 DTO 타입 참조, Mapper는 DTO 필드 참조, vue_page는 vue_types + 확정 Vue + API 계약. vue_page는 계약이 API 시그니처를 고정하므로 service를 기다릴 필요 없이 백엔드와 병렬. |
| 3 | `service`/`service_impl` | wave2의 DAO 메서드명 | DAO 메서드명이 확정돼야 ServiceImpl이 정확히 호출. DAO를 Service보다 먼저 고정 → "ServiceImpl이 추측한 DAO 메서드명 불일치"(구 코드의 핵심 에러원)를 구조적으로 제거. |

3-wave를 2-wave 대신 택한 이유: service/dao를 같은 wave에 두면 ServiceImpl이 아직 미확정인 DAO 메서드명을 추측하게 되어 불일치가 발생한다. DAO를 독립 wave로 먼저 고정하면 이 에러가 사라진다. service_impl은 어차피 가장 무거운 파일이라 단독 wave로 둬도 임계 경로 손해가 작다.

### fan-out / fan-in 메커니즘
- **동적 fan-out**: Planner가 만든 파일 목록을 LangGraph `Send("generate_file", {file_spec})` API로 펼친다. 파일 개수가 화면마다 가변이므로 정적 노드가 아닌 동적 분기.
- **wave 배리어**: wave N 노드 전체가 fan-in된 뒤에야 wave N+1 fan-out. LangGraph superstep 모델이 자연히 배리어 제공. `current_wave` 상태 + 조건부 엣지로 게이팅.
- **wave 배정은 고정 규칙**: file_type → wave 매핑은 결정론적 상수. Planner LLM은 "어떤 파일이 필요한가"(개수·이름)만 판단하고 wave 번호는 코드가 배정 → wave 경계가 LLM 변덕에 흔들리지 않음.

---

## 3. 상태 스키마 (CodeGenState)

```python
from typing import TypedDict, Annotated
from operator import add

class GeneratedFile(TypedDict):
    file_path: str
    file_type: str        # dto_request | dao_impl | vue_page | ...
    layer: str            # backend | frontend
    wave: int             # 1 | 2 | 3
    content: str
    status: str           # ok | failed
    status_log: list[str] # static_check 게이트 결과 등

def merge_files(left: dict, right: dict) -> dict:
    """병렬 노드가 각자 만든 파일을 file_path 키로 병합 (충돌 없음)."""
    return {**(left or {}), **(right or {})}

class CodeGenState(TypedDict):
    # ── 입력 (불변) ──
    session_id: str
    spec_markdown: str
    confirmed_vue: str              # 앞단 확정 Vue SFC
    table_info: str                 # 테이블정보.md fresh 로드 (실제 DB 컬럼/타입)
    # ── Contract Extractor 산출 ──
    contract: dict | None           # 단일 진실원 (아래 스키마)
    # ── Planner 산출 ──
    plan: dict | None               # {files: [{path, file_type, layer, wave, deps, class_name}]}
    # ── 병렬 생성 결과 (reducer로 안전 병합) ──
    files: Annotated[dict[str, GeneratedFile], merge_files]
    # ── Reviewer ──
    review_iterations: int          # 하드캡 카운터
    open_issues: list[dict]         # 미해결 이슈 (0이면 수렴)
    # ── 진행/관찰 ──
    current_wave: int               # 1|2|3, wave 게이팅용
    events: Annotated[list[dict], add]   # 도메인 이벤트 누적 (SSE 어댑터가 drain)
```

### contract 스키마
```python
contract = {
  "screen": {"id": "...", "name": "...", "type": "list-detail"},
  "tables": [{"name": "TB_EDU_PGM",
              "columns": [{"col": "EDU_PGM_ID", "type": "VARCHAR", "pk": true, ...}]}],
  "fields": [{"vue_field": "eduPgmNm", "db_column": "EDU_PGM_NM",
              "type": "string", "label": "...", ...}],
  "search_conditions": [...],
  "table_columns": [...],
  "api_signatures": [{"method": "POST", "path": "...",
                      "req_dto": "CpmsEduReqDto", "res_dto": "CpmsEduResDto"}],
}
```

**설계 포인트:**
1. **`files`에 reducer 필수** — wave1의 4개 노드가 동시에 `files`를 업데이트하면 `merge_files`가 충돌 없이 병합. 이게 없으면 병렬 쓰기가 서로 덮어쓴다(병렬 설계의 핵심 함정).
2. **`contract` 단일 진실원** — Extractor가 한 번 채우면 이후 read-only. `table_info` 포함으로 "Vue 필드 ↔ 실제 DB 컬럼" 매핑이 추측이 아닌 실존 스키마 기반.
3. **`current_wave` + 조건부 엣지**로 wave 게이팅.
4. **`review_iterations`/`open_issues`**로 수렴 + 하드캡 종료 판정.
5. **`events` append-only(`add` reducer)** — LangGraph가 모르는 도메인 이벤트 누적.
6. **체크포인팅 호환** — 전체 TypedDict가 매 superstep마다 SqliteSaver에 직렬화. 세션당 수십 파일 규모라 SQLite blob 크기 무난.

---

## 4. 도구 레이어 (7개)

LangGraph 노드 안에서 gpt-5.5 클라이언트가 Responses API `tools` 파라미터로 직접 바인딩한다(LangChain `bind_tools` 미사용). 각 도구는 **결정론적 코어 함수**(wave 노드가 그래프 주입용으로 직접 호출) + **도구 래퍼**(Reviewer LLM이 자율 호출)의 두 용도로 분리해 로직 중복을 없앤다.

| # | 도구 | 용도 | 호출 주체 |
|---|------|------|----------|
| 1 | `static_check(file_path, content) -> list[dict]` | 단일 파일 정규식 검증 (UUID import, scrollHeight=flex, @Service 오용, bare DAO call 등) | wave 게이트(코어) + Reviewer(도구) |
| 2 | `cross_check(files, contract) -> list[dict]` | 파일 간 정합성 + 계약 대조 (ServiceImpl 참조 DTO필드 존재? DAO메서드명 일치? 프론트 호출 API가 백엔드에 존재?) | Reviewer 전용 (fan-in 후에만 의미) |
| 3 | `lookup_class(class_name) -> dict\|None` | **생성된 파일 내** 클래스의 필드·메서드 조회 | Reviewer |
| 4 | `get_dto_fields(dto_name) -> list[dict]` | **생성된** 특정 DTO의 필드(이름+타입) 조회 | Reviewer |
| 5 | `lookup_guide(layer, topic) -> str` | 표준 가이드 md를 mtime-fresh로 조회 (최신본 보장) | Reviewer (전수검증) |
| 6 | `validate_sql(sql) -> list[dict]` | db_init_sql SQL 문법/규칙 검증 | wave 게이트(코어) + Reviewer |
| 7 | `list_generated_files() -> list[dict]` | 현재 생성 현황(path/type/layer/status) 조회 | Reviewer |

**설계 포인트:**
1. **코어 함수 / 도구 래퍼 분리** — `_static_check_impl`, `_load_guide_impl` 등 결정론적 코어를 wave 노드가 LLM 없이 직접 호출. 동일 로직을 Reviewer는 도구로 호출.
2. **`cross_check`가 계약 대조** — 파일끼리만 보는 게 아니라 `contract`와 대조. "Vue가 기대한 API ↔ 생성된 Service"가 계약 기준으로 맞는지 검증(프론트-백 불일치 최종 방어선).
3. **`lookup_class`/`get_dto_fields`는 생성된 파일만** 조회 — 워크스페이스 부모 클래스는 보지 않음(범위 축소 결정).
4. **`lookup_guide` mtime-fresh** — 호출마다 파일 수정시각 확인 → 변경 시 자동 재로드. 진행 중인 Reviewer 루프 안에서도 최신 가이드로 검증. 죽은 `invalidate_cache()` 대체.
5. **도구 에러 = 관찰값** — 도구가 던지면 에러를 LLM에 관찰값으로 되돌려 ReAct 자가복구. 무한루프는 하드캡 차단.

---

## 5. 노드별 명세

모든 노드는 순수 async 함수 `async def node(state: CodeGenState) -> dict`. 반환은 상태 부분 업데이트(reducer 병합). LLM 호출은 전부 gpt-5.5 클라이언트 직접 호출(`_with_retry` 계승).

### ① contract_extract (단일, gpt-5.5, single-shot)
- **입력**: `spec_markdown`, `confirmed_vue`, `table_info`
- **작업**: Vue SFC 파싱(필드/컬럼/검색조건/이벤트) + spec + 실제 DB 테이블 → 구조화 계약 JSON. Vue필드 ↔ DB컬럼 매핑이 핵심 산출.
- **프롬프트 전략**: "코드 생성 금지, 구조 추출만". Responses API structured output으로 JSON 스키마 강제.
- **출력**: `{contract: {...}}`
- **검증**: 계약 JSON 스키마 유효성(필수 키, 빈 배열 아님) → 실패 시 1회 재생성.

### ② planner (단일, gpt-5.5, single-shot)
- **입력**: `contract`
- **작업**: 생성할 파일 목록 결정(개수·이름·class_name·layer·deps). wave 번호는 **고정 규칙**으로 코드가 배정.
- **출력**: `{plan: {files: [...]}}`

### ③ generate_file (병렬 fan-out, gpt-5.5, single-shot + static_check 게이트)
`Send("generate_file", {file_spec})`로 파일마다 동적 분기. 같은 wave 동시 실행.
- **입력**: 해당 `file_spec` + `contract` + (개선3) 매핑으로 선택된 최신 가이드 주입 + wave 의존 파일
  - wave1: contract만
  - wave2: + wave1 산출 DTO/types
  - wave3: + wave2 산출 DAO 메서드 시그니처
- **작업**: 파일 1개 생성 → `static_check_impl()`(또는 `validate_sql`) 즉시 실행 → 위반 있으면 위반 목록을 프롬프트에 넣어 **1회 재생성** → `files`에 기록. 1회 후에도 위반 남으면 통과시키되 `open_issues`로 Reviewer에 전달.
- **출력**: `{files: {path: GeneratedFile}}` (reducer 병합)

### ④ wave_gate (조건부 라우팅, LLM 없음)
- wave N 전체 fan-in 완료 → `current_wave` 증가 → 다음 wave fan-out, 마지막이면 reviewer로.

### ⑤ reviewer (ReAct 루프, gpt-5.5 + Responses API tools)
- **입력**: 전체 `files` + `contract` + 7개 도구
- **루프**: gpt-5.5가 `cross_check`/`static_check`/`lookup_guide` 등 자율 호출 → 위반 발견 → 문제 파일 **직접 수정**(files 업데이트) → 재검증 → `open_issues` 갱신. `thought`(추론)는 SSE로 노출.
- **종료**: `open_issues == []`(수렴) **또는** `review_iterations >= REVIEWER_HARD_CAP`(하드캡 백스톱)
- **출력**: 수정된 `files`, 최종 `open_issues`(남으면 경고 로그)

---

## 6. SSE 이벤트 재설계 + LangGraph 연동

### 신규 SSE 이벤트 타입
```typescript
// 그래프 레벨
{ type: "graph_start", session_id }
{ type: "node_start", node, label }
{ type: "node_end", node, duration_ms }
{ type: "graph_complete", total_files, open_issues }
{ type: "error", node, message }

// 계약/계획
{ type: "contract", contract }
{ type: "plan", files: [{path, file_type, wave}] }

// 병렬 wave
{ type: "wave_start", wave, file_count }
{ type: "file_start", path, file_type, wave }
{ type: "file_token", path, delta }          // 파일별 스트리밍 토큰
{ type: "file_gate", path, issues_found, regenerated }
{ type: "file_complete", path, layer, content }
{ type: "wave_complete", wave }

// Reviewer ReAct
{ type: "react_step", iteration, thought }   // LLM 추론 노출
{ type: "tool_call", tool, args }
{ type: "tool_result", tool, result_summary }
{ type: "file_fixed", path, reason }
{ type: "react_converged", iterations }
```

### LangGraph → SSE 변환 (sse_adapter.py)
```python
async def stream_codegen(state_input, session_id):
    config = {"configurable": {"thread_id": session_id},
              "recursion_limit": REVIEWER_HARD_CAP}
    async for ev in graph.astream_events(state_input, config, version="v2"):
        kind = ev["event"]
        if kind == "on_chain_start":           # 노드 진입
            yield sse("node_start", node=ev["name"], ...)
        elif kind == "on_chat_model_stream":   # gpt-5.5 토큰
            yield sse("file_token", path=..., delta=ev["data"]["chunk"])
        elif kind == "on_tool_start":
            yield sse("tool_call", tool=ev["name"], args=...)
        elif kind == "on_tool_end":
            yield sse("tool_result", tool=ev["name"], ...)
        # 노드 내부 커스텀 이벤트는 state.events에서 drain
```

**핵심 메커니즘:**
1. **두 이벤트 소스 결합** — astream_events(노드/토큰/도구 자동 방출) + state.events(LangGraph가 모르는 도메인 이벤트: `file_gate`, `file_fixed`). 어댑터가 병합해 단일 스트림.
2. **병렬 토큰 구분** — `file_token`에 `path`를 실어 프론트가 파일별 패널에 분배(현재는 단일 스트림이라 섞임).
3. **재개 시 이벤트** — SqliteSaver 재개 시 완료 노드는 캐시 반환 → `node_end`(cached) 즉시 방출, 실패 지점부터 실시간 재개.
4. **`EventSourceResponse` 유지** — 전송 계층(sse-starlette)은 그대로, 이벤트 내용만 신규.

### 프론트엔드 변경
- `sessionStore.ts`: 신규 이벤트 핸들러, 파일별 상태를 `Map<path, FileState>`로 관리.
- `CodeGenPanel.tsx`: wave 병렬 진행 바 + (선택 파일) 토큰 스트리밍 패널 + Reviewer ReAct 타임라인(thought/tool_call). 4개 동시 패널은 펼치지 않고 wave 진행 바 + 선택 파일 스트리밍으로 절충.
- `client.ts` `consumeSSE`: 파싱 로직 유지(JSON line), 타입만 신규.

---

## 7. 체크포인팅 · 에러 처리 · 테스트

### 체크포인팅 (AsyncSqliteSaver)
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
checkpointer = AsyncSqliteSaver.from_conn_string(".sessions/codegen_graph.db")
graph = builder.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": session_id}}
```
- **thread_id = session_id** → 기존 세션 모델(`.sessions/`)과 동일 수명·키.
- **재개 API** `POST /api/codegen/resume` → 같은 thread_id로 `graph.astream(None, config)` → 마지막 체크포인트부터 재개. 완료 노드 캐시, 실패 노드부터 실재실행.
- **superstep 단위 저장** — wave1 완료 후 죽으면 wave1 캐시, wave2부터 재개. 비싼 LLM 생성 재실행 최소화.
- **정리** — 세션 만료(`SESSION_TTL_HOURS`) 시 해당 thread 체크포인트도 삭제(세션 cleanup 연동).

### 에러 처리 (계층별)
| 계층 | 전략 |
|------|------|
| LLM 호출 | `_with_retry`(transient 3회) 계승 — 프록시 끊김 대응 |
| contract/planner 실패 | `error` 이벤트 + 그래프 중단(재개 가능 체크포인트 보존) |
| wave 파일 생성 실패 | 해당 파일만 `status=failed` 마킹, 나머지 병렬 파일 계속 → Reviewer가 인지 |
| static_check 게이트 | 1회 재생성 후에도 위반 남으면 통과 + `open_issues`로 Reviewer 전달 |
| Reviewer 도구 에러 | 관찰값으로 LLM 반환(ReAct 자가복구), 하드캡이 무한루프 차단 |
| 그래프 전체 | 어느 노드서 죽어도 체크포인트 보존 → resume 가능 |

### 테스트 전략 (TDD)
```
backend/tests/graph/
  test_state.py        # reducer(merge_files) 병렬 병합, 충돌 없음
  test_tools.py        # 7개 도구 각각 (정규식/조회/가이드 mtime-fresh)
  test_contract.py     # Vue+spec+table → 계약 추출 (mock LLM)
  test_planner.py      # 파일목록 + wave 고정배정 규칙
  test_waves.py        # fan-out/fan-in, wave 게이팅, static 게이트 1회
  test_reviewer.py     # ReAct 수렴 / 하드캡 / 직접수정 (mock tool 응답)
  test_checkpoint.py   # 중단 후 resume → 완료노드 캐시 확인
  test_sse_adapter.py  # astream_events → 신규 이벤트 매핑
  test_graph_e2e.py    # 전체 그래프 (mock LLM) 입력→완성
```
- **원칙**: LLM은 mock, 그래프 구조·라우팅·reducer·도구는 실제 검증. 결정론적 부분(static_check, wave 배정, 계약 스키마)은 실제 로직 테스트.
- **회귀**: 기존 테스트는 재작성 대상이나 `/api/codegen/*` 엔드포인트 요청/응답 계약은 유지해 프론트 호환 확인.

### 마이그레이션 (전면 재작성)
- **신규**: `backend/app/llm/graph/` 패키지 (state/tools/nodes/react/build/sse_adapter/llm/guides)
- **폐기**: `orchestrator.py`, `agents.py`(4913줄), `codegen_context.py` 죽은 캐시 로직
- **계승**: `_with_retry`, gpt-5.5 클라이언트(명칭 정정), 정규식 검증 룰(도구로 재작성), 가이드 로더(mtime-fresh로 개선)
- **의존성 추가**: `langgraph`, `langgraph-checkpoint-sqlite`
- **명칭 정정**: `codex_client`/`CodexLLMClient` → gpt-5.5 명칭, `CODEX_AZURE_OPENAI_*` env 정리 (구현 계획에서 마이그레이션 방식 확정)

---

## 8. 컴포넌트 경계 (단위별 책임)

| 단위 | 한 가지 책임 | 의존 |
|------|-------------|------|
| `state.py` | 상태 스키마 + reducer | (없음) |
| `llm.py` | gpt-5.5 Responses API 호출 + 재시도 + tool-calling 루프 | config |
| `guides.py` | 가이드 md mtime-fresh 로드 + file_type→가이드 매핑 | config, 파일시스템 |
| `tools.py` | 7개 도구의 결정론적 코어 + @tool 래퍼 | state, guides |
| `nodes.py` | contract/planner/generate_file/wave_gate 노드 | llm, tools, guides, state |
| `react.py` | Reviewer ReAct 루프 (수렴/하드캡) | llm, tools, state |
| `build.py` | StateGraph 조립 + Send fan-out + checkpointer | nodes, react, state |
| `sse_adapter.py` | astream_events → 신규 SSE 이벤트 변환 | build |
| `routers/codegen.py` | HTTP/SSE 엔드포인트 (generate/resume) | sse_adapter, session |

각 단위는 인터페이스만으로 사용 가능하고 내부 변경이 소비자를 깨지 않도록 설계한다.

---

## 9. 검증 계획

### 단위
- [ ] reducer 병렬 병합 충돌 없음
- [ ] 7개 도구 정상 동작 (특히 `lookup_guide` mtime-fresh, `cross_check` 계약 대조)
- [ ] wave 고정 배정 규칙
- [ ] static_check 게이트 정확히 1회 재생성
- [ ] Reviewer 수렴 종료 / 하드캡 종료 둘 다

### 통합
- [ ] 전체 그래프 (mock LLM) — 확정 Vue+spec+table → 완성 파일 세트
- [ ] 3-wave 병렬 실행 + 배리어 (wave1 완료 전 wave2 미시작)
- [ ] 중단 후 resume → 완료 노드 캐시, 실패 지점 재개
- [ ] SSE 어댑터 신규 이벤트 매핑

### E2E
- [ ] 실제 gpt-5.5로 한 화면 생성 → 백엔드 컴파일(배포 단계) 통과
- [ ] 가이드 md 수정 → 다음 생성에 반영 확인
- [ ] 확정 Vue의 레이아웃/필드가 생성 결과에 보존되는지
- [ ] 프론트-백 계약 정합성 (Reviewer가 불일치 잡아 수정하는지)
