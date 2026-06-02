# MyBatis Binding Verification (Phase 1) Design

> 코드 생성 결과의 가장 치명적 결함인 **DAO statement id ↔ Mapper id 불일치 + namespace 오류**(런타임 100% 실패)를, 룰 추가가 아니라 **결정론적 파서 기반 검증·자동교정**으로 봉쇄한다. "검증의 심판을 LLM/정규식 추측에서 실행 가능한 진실로 옮기는" 단계적 개선의 1단계.

## Context

LangGraph 코드 생성 파이프라인이 만든 실제 산출물(`outputs/code`)을 검토한 결과, 표면적으로는 그럴듯하나 **런타임에 100% 실패**하는 치명결함이 있었다:

- **DAO ↔ Mapper statement id 불일치**: DAO가 `super.selectList("selectCpmsEduRsltList")`를 부르는데 Mapper의 실제 id는 `selectCpmsEduRsltLstList` (`Rslt` vs `RsltLst`). MyBatis가 바인딩할 statement를 못 찾아 런타임 예외.
- **namespace 오류**: Mapper namespace가 `com.example.cpms.mapper.CpmsEduRsltLstMapper`인데, CPMS 표준 + `super.xxx("id")` 호출 방식은 namespace = DaoImpl FQCN이어야 함.

이 결함의 근본 원인은 **생성 루프 안에 "실행되는 진실(executable ground truth)"이 없다**는 것이다. 검증의 최종 심판이 LLM(Reviewer)이나 정규식(static_check)인데, 둘 다 "그럴듯함"은 알아도 "실제로 바인딩되는가"는 모른다. 또한 statement id 불일치는 **maven 컴파일로도 안 잡힌다** — Java는 문자열 id를 모르고 런타임에야 터지기 때문. 반면 DAO(.java)와 Mapper(.xml)를 파싱해 대조하면 밀리초 만에, 환경 의존 없이 잡을 수 있다.

룰을 하나씩 추가하는 방식은 두더지잡기(본 적 있는 실수만 잡음)다. 대신 **결정론적 바인딩 검증기**를 도입해, 이 부류의 결함을 구조적으로 봉쇄한다. 이것이 "단계적 근본 해결"의 Phase 1이다.

## 설계 결정 요약

| 항목 | 결정 |
|------|------|
| oracle | MyBatis 바인딩 검증 (결정론적 파서, LLM·빌드 불필요) |
| 검증 범위 | statement id 일치(양방향) + namespace = DaoImpl FQCN |
| 처리 방식 | 명백한 1:1 변형 → 결정론 자동교정 / 모호 → Reviewer 도구로 위임 |
| 진실 출처 (source of truth) | DAO의 `super.xxx("id")` 호출 문자열 (Phase 2에서 contract로 승격 예정) |
| 파일 매칭 | 이름 규칙 (`XxxDaoImpl` ↔ `XxxMapper`) |
| 자동교정 위치 | reviewer 직전 단일 노드 `mybatis_fix` (LLM 없음) |
| 잔여 탐지 | Reviewer 도구 `validate_mybatis_binding` → `apply_fix`로 수정 |
| 미사용 Mapper id | 경고만 (자동 삭제 안 함) |
| 범위 | Phase 1만. Phase 2(contract를 statement-id 레벨로 확장)는 별도 spec |

**Phase 2 예고**: 본 Phase는 DAO를 진실 출처로 삼는다. Phase 2에서 contract를 statement id·시그니처 레벨까지 확장하면, 진실 출처를 contract로 승격하고 DAO·Mapper 양쪽을 거기 맞춰 "애초에 틀리게 생성할 수 없게" 만든다.

---

## 1. 컴포넌트 구조

신규 모듈 1개 + 연결 3곳:

```
backend/app/llm/graph/
  mybatis_check.py   (신규)  ── 순수 파서·교정 로직 (LLM 없음, 결정론)
      ├ parse_dao(dao_content)        → {statement_ids: set, expected_namespace: str(FQCN)}
      ├ parse_mapper(mapper_content)  → {ids: set, namespace: str}
      ├ match_pairs(files)            → [(dao_file, mapper_file)] 이름규칙 매칭
      ├ check_binding(files)          → list[issue]  (id 불일치 + namespace 오류)
      └ autofix_binding(files)        → (fixed_files, fix_logs)  ← 명백한 1:1만
```

연결 지점:
1. **`tools.py`** — `check_binding`을 Reviewer 도구 `validate_mybatis_binding`으로 노출. `REVIEWER_TOOL_SPECS`에만 추가(읽기 전용 진단), `dispatch_tool`에 분기 등록. `TOOL_SPECS`(7개)는 불변.
2. **`build.py`** — reviewer 직전에 결정론 자동교정 노드 `mybatis_fix` 삽입.
3. **`react.py` (변경 없음)** — Reviewer가 `validate_mybatis_binding` 도구로 자동교정이 못 잡은 잔여 불일치를 탐지 → 기존 `apply_fix`로 수정.

**경계 근거**: `mybatis_check.py`는 LLM과 완전 분리된 순수 함수 → mock 없이 결정론적 단위 테스트 가능. 그래프는 그것을 "노드(자동교정)"와 "도구(잔여 탐지)" 두 방식으로 소비. 기존 `cross_check`와 동일 패턴이라 일관성 유지.

---

## 2. 검증·교정 알고리즘

### 2.1 파일 매칭 (이름 규칙)
- DaoImpl: 파일명 `*DaoImpl.java` → 베이스명 (`CpmsEduRsltLstDaoImpl` → `CpmsEduRsltLst`)
- Mapper: 파일명 `*Mapper.xml` → 베이스명 (`CpmsEduRsltLstMapper` → `CpmsEduRsltLst`)
- 베이스명이 같으면 짝. 짝 없으면 issue("DaoImpl에 대응 Mapper 없음" / 그 반대).

### 2.2 파싱 (정규식, 결정론적)
```
parse_dao:
  - super\.(select|selectOne|selectList|insert|update|delete|batchUpdate\w*)\s*\(\s*"(<id>)"
        → statement_ids
  - package <pkg>;  +  public class <Cls>DaoImpl
        → expected_namespace = "<pkg>.<Cls>DaoImpl"
parse_mapper:
  - <mapper namespace="(<ns>)">                → namespace
  - <(select|insert|update|delete)\s+id="(<id>)" → ids
```

### 2.3 check_binding — 3종 issue
1. **namespace 불일치**: mapper.namespace ≠ dao.expected_namespace
2. **DAO→Mapper 누락**: DAO statement_id ∉ mapper.ids (치명 — 런타임 실패)
3. **Mapper→DAO 미사용**: mapper.id ∉ DAO statement_ids → **경고 레벨**(삭제·교정 안 함; 의도된 내부 statement일 수 있음)

각 issue: `{"file_path", "issue", "severity": "error"|"warning"}`

### 2.4 autofix_binding — "명백한 1:1"만, DAO가 진실
```
namespace 오류:
  → mapper namespace를 DaoImpl FQCN으로 교체 (항상 명백 → 자동교정)

id 불일치:
  미사용 Mapper id가 정확히 1개 AND 누락 DAO 호출 id가 정확히 1개 (1:1)
    AND normalized_edit_distance(mapper_id, dao_id) ≤ THRESHOLD (예: 0.3)
      → 그 Mapper id를 DAO 호출 id로 rename (DAO 기준)
  그 외 (1:N, N:1, 매칭 모호, 거리 큼)
    → 자동교정 안 함 → issue로 잔류 → Reviewer 위임 (보수 원칙)
```
- THRESHOLD는 구현 시 테스트로 조정하되, **모호하면 교정하지 않고 Reviewer로** 보내는 보수성은 불변.
- 자동교정은 **1-pass**: 적용 후 `check_binding` 재실행해 잔여만 다음 단계로. 무한루프 없음.

**방금 버그 검증**:
- namespace `...mapper.CpmsEduRsltLstMapper` ≠ FQCN `com.example.cpms.dao.CpmsEduRsltLstDaoImpl` → 자동교정 ✅
- DAO 누락 `selectCpmsEduRsltList`(1) ↔ Mapper 미사용 `selectCpmsEduRsltLstList`(1), 편집거리 작음 → Mapper id를 DAO 기준 rename ✅

---

## 3. 그래프 통합 + 데이터 흐름

```
wave3 (service_impl) fan-in
   │
[wave_gate] 3→4 (>MAX_WAVE)
   │
★ [mybatis_fix] (신규, LLM 없음) ★
   │   autofix_binding(files) → fixed_files + fix_logs
   │   check_binding(fixed_files) → remaining issues
   ▼
[reviewer]  (validate_mybatis_binding 도구로 잔여 탐지 → apply_fix)
   ▼
  END
```

**위치 근거 (reviewer 직전 단일 노드)**: dao+mapper는 wave2지만, service까지 모두 생성된 뒤 한 번에 정합하는 것이 안전하고, 자동교정 → reviewer 잔여처리가 연속된다. wave2 중간 삽입은 라우팅이 복잡해진다.

### 노드 구현
```python
def mybatis_fix(state: dict) -> dict:
    files = dict(state.get("files", {}))
    try:
        fixed_files, fix_logs = autofix_binding(files)   # 결정론, LLM 없음
        remaining = check_binding(fixed_files)
    except Exception as e:
        # 검증은 보조 안전망이지 차단기가 아님 — 실패해도 생성 전체를 막지 않음
        return {"events": [{"type": "log", "line": f"[MYBATIS] error: {e}"}]}
    events = [{"type": "log", "line": f"[MYBATIS-FIX] {log}"} for log in fix_logs]
    if remaining:
        events.append({"type": "log",
                       "line": f"[MYBATIS] {len(remaining)} binding issue(s) left for reviewer"})
    return {"files": fixed_files, "events": events, "open_issues": remaining}
```

### 상태 영향
- `files` (merge_files reducer): 교정된 dao/mapper content 덮어씀. 단일 노드라 동시쓰기 충돌 없음.
- `open_issues` (add reducer): 잔여 바인딩 issue 추가 → reviewer가 인지.
- `events`: `[MYBATIS-FIX]` 로그 → SSE로 사용자에게 표시(어느 파일이 교정됐는지).

### build.py 변경 (최소)
```python
g.add_node("mybatis_fix", mybatis_fix)
g.add_edge("mybatis_fix", "reviewer")
# _route_waves가 "reviewer" 반환하던 지점을 "mybatis_fix"로 변경
```

---

## 4. 테스트 전략

전부 LLM 불필요(결정론) — mock 없이 실제 검증.

### `backend/tests/graph/test_mybatis_check.py`
- **파싱**: parse_dao(super 호출 id + FQCN namespace 추출), parse_mapper(namespace + id 추출)
- **매칭**: 이름규칙 `XxxDaoImpl ↔ XxxMapper`, 짝 없을 때 issue
- **check_binding**: namespace 불일치 / DAO→Mapper 누락 / Mapper→DAO 미사용(warning)
- **autofix_binding**: namespace 자동교체 / 1:1+근접 rename / 1:N·거리큼·모호 → 교정 안 함(보수성) / 교정 후 재검증 시 issue 소멸
- **회귀 픽스처 ★**: `outputs/code`의 실제 결함 dao+mapper(`selectCpmsEduRsltList` ↔ `selectCpmsEduRsltLstList` + 틀린 namespace)를 픽스처로 박아, autofix가 둘 다 잡는지 end-to-end. "이 버그는 다시는 안 통과한다"를 영구 고정.

### `backend/tests/graph/test_mybatis_node.py`
- `mybatis_fix` 노드: 결함 files in → 교정된 files + open_issues + events out
- 깨끗한 입력 → 무변경, open_issues 빈 채

### `backend/tests/graph/test_llm.py` (기존 확장)
- `validate_mybatis_binding`이 `REVIEWER_TOOL_SPECS`에 있고 `TOOL_SPECS`엔 없음
- `dispatch_tool("validate_mybatis_binding", ...)` 동작

### 통합 (실 LLM 1개)
- 기존 `test_build.py` e2e에 `mybatis_fix` 노드가 끼어도 그래프가 정상 종료(라우팅 정상).

### 에러 처리
- 파싱 실패(깨진 XML/Java): 해당 파일 건너뛰고 다른 쌍 계속. 파싱 불가는 issue로 기록.
- 자동교정 모호: 교정 안 하고 issue 잔류 (추측 교정 금지).
- 프론트 전용 화면(dao/mapper 없음): no-op 통과.
- `mybatis_fix` 자체 예외: try/except로 로그만 내고 reviewer로 진행 (검증은 보조 안전망, 차단기 아님).

---

## 5. 컴포넌트 경계 (단위별 책임)

| 단위 | 한 가지 책임 | 의존 |
|------|-------------|------|
| `mybatis_check.parse_dao/parse_mapper` | 텍스트 → 구조(id 집합, namespace) | (없음) |
| `mybatis_check.match_pairs` | 이름규칙으로 dao↔mapper 짝짓기 | (없음) |
| `mybatis_check.check_binding` | 불일치 탐지 (3종 issue) | parse_*, match_pairs |
| `mybatis_check.autofix_binding` | 명백한 1:1 결정론 교정 | parse_*, match_pairs, check_binding |
| `nodes/build.mybatis_fix` | 그래프 노드: 교정 적용 + 잔여를 상태로 | mybatis_check |
| `tools.validate_mybatis_binding` | Reviewer 도구: 잔여 탐지 | mybatis_check.check_binding |

각 단위는 인터페이스만으로 사용 가능하고 내부 변경이 소비자를 깨지 않는다.

---

## 6. 검증 계획

- [ ] parse_dao / parse_mapper 정확성 (id 집합, namespace)
- [ ] 이름규칙 매칭 + 짝 없음 issue
- [ ] check_binding 3종 issue (namespace / 누락 / 미사용-warning)
- [ ] autofix: namespace 교체 + 1:1 근접 rename
- [ ] autofix 보수성: 1:N·거리큼·모호 → 교정 안 함
- [ ] **회귀: outputs/code 실결함 픽스처를 autofix가 해소**
- [ ] mybatis_fix 노드 입출력 (files/open_issues/events)
- [ ] validate_mybatis_binding 도구 등록 + dispatch
- [ ] e2e(실 LLM): mybatis_fix 삽입 후 그래프 정상 종료
- [ ] 회귀: 기존 graph 테스트 무손상
