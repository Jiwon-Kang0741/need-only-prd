# Contract-Driven Generation (Phase 2) Design

> contract를 **코드 레벨 식별자(statement id, DAO 메서드, DTO 필드)까지 정의하는 진실 출처**로 승격한다. 식별자는 LLM이 아니라 결정론적 규칙(namebook)으로 코드가 파생하고, 생성 노드는 프롬프트로 그 식별자를 강제 주입받으며(예방), Phase 1 검증기는 contract 기준으로 교정한다(교정). 목표: DAO↔Mapper↔Service↔DTO 불일치를 "사후 교정"이 아니라 "애초에 생성 불가능"하게 만든다.

## Context

Phase 1(`mybatis-binding-verification`)은 DAO↔Mapper statement id/namespace 불일치를 **사후 검증·자동교정**으로 봉쇄했다. 효과는 입증됐지만(`outputs/code` 7 에러 → 0), 근본적으로는 "LLM이 식별자를 자유 생성 → 어긋남 → 코드가 교정"이라는 사후 대응이다.

근본 원인은 **식별자가 여러 파일에서 독립적으로 자유 생성**된다는 것이다. DAO가 `super.selectList("selectCpmsEduRsltList")`로 한 번, Mapper가 `<select id="selectCpmsEduRsltLstList">`로 또 한 번 — 같은 식별자를 두 곳에서 LLM이 따로 쓰니 어긋난다(`Rslt` vs `RsltLst`). ServiceImpl이 DTO에 없는 `getXxx()`를 부르는 결함(cross_check가 잡던 것)도 같은 부류 — DTO 필드명이 단일 정의되지 않았다.

Phase 2의 해법: **식별자·DTO 필드를 contract가 단일 정의**하고, 모든 생성 노드가 그것을 *참조*한다. 식별자를 코드가 결정론적으로 파생하면(LLM 변덕 제거) 명명이 100% 일관되어, 같은 contract를 참조하는 한 불일치가 수학적으로 불가능하다.

이것은 "검증의 심판을 실행 가능한 진실로 옮긴다"는 단계적 개선의 Phase 2다. Phase 1이 *검증/교정*이었다면 Phase 2는 *예방*(생성 단으로 끌어올림)이다.

## 설계 결정 요약

| 항목 | 결정 |
|------|------|
| contract 확장 범위 | 식별자(operations) + DTO 스키마(dtos). 전체 코드 골격(Phase 3/C)은 품질 보고 결정 |
| 식별자/명명 생성 | **결정론 코드 파생**(namebook 규칙), LLM 아님 |
| 파생 위치 | planner 직후 신규 코드 노드 `derive_contract` |
| 명명 규칙 모듈 | 신규 `naming.py` (순수 함수) |
| op 세트 | 화면 type별 고정 세트 + api_signatures 보정 (둘 다) |
| 생성 노드 강제 | 프롬프트에 "REQUIRED IDENTIFIERS" 강조 주입(예방) + 검증 승격(교정) 이중 방어 |
| 검증 승격 | `mybatis_check`에 `contract` 옵션 인자 추가. 있으면 contract 기준(DAO도 교정) / 없으면 Phase 1 동작(DAO 기준) |
| DTO 필드 검증 | 같은 모듈에 contract.dtos 기준 추가 (cross_check 승격) + 누락 필드 autofix |
| 하위호환 | `contract=None` 기본값으로 Phase 1 테스트 9개 그대로 통과 — **필수** |
| 충돌 처리 | contract가 진실. contract 없거나 op 누락 시 Phase 1(DAO 기준) 폴백 |
| 에러 정책 | derive/파생/주입 실패는 차단 아님 — 로그 + 생성 계속, 검증이 잡음 |

**Phase 3 후보 (C, 미착수)**: 최종 생성 코드 품질이 부족하면, 식별자가 고정된 부분(DAO 래퍼·Mapper 골격·DTO 필드 선언)을 LLM이 아닌 **템플릿 코드로 생성**하고 LLM은 쿼리 본문·비즈니스 로직만 채우는 방향으로 확장. 별도 brainstorming.

---

## 1. 확장된 contract 스키마

기존 contract에 코드 레벨 진실 두 블록을 추가한다.

```jsonc
{
  // ── 기존 (LLM 추출, 화면 의미) ──
  "screen": {"id": "CPMSEDURSLTLST", "name": "교육이수현황", "type": "list"},
  "tables": [...], "fields": [...], "search_conditions": [...],
  "table_columns": [...], "api_signatures": [...],

  // ── 신규 (코드 파생, 결정론) ──
  // 식별자는 namebook 공식 규칙 = bare (화면당 Mapper 1개라 접두/접미 불필요)
  "operations": [
    {
      "op": "selectList",
      "statement_id": "selectList",
      "dao_method": "selectList",
      "param_type": "CpmsEduRsltLstReqDto",
      "return_type": "List<CpmsEduRsltLstResDto>",
      "mybatis_tag": "select"
    },
    {"op": "selectOne", "statement_id": "select", "dao_method": "select", "mybatis_tag": "select", ...},
    {"op": "count", "statement_id": "selectCount", "dao_method": "selectCount", "mybatis_tag": "select", ...},
    {"op": "insert", "statement_id": "insert", "dao_method": "insert", "mybatis_tag": "insert", ...},
    {"op": "update", "statement_id": "update", ...}, {"op": "delete", "statement_id": "delete", ...}
  ],
  "dtos": [
    {"name": "CpmsEduRsltLstReqDto", "kind": "request",
     "fields": [{"name": "employeeName", "java_type": "String", "db_column": "EMP_NM"}, ...]},
    {"name": "CpmsEduRsltLstResDto", "kind": "response", "fields": [...]}
  ]
}
```

**파생 규칙 (코드, namebook 공식 = bare 식별자):**
- `statement_id` = `dao_method` = op별 고정 bare 이름 (selectList→`selectList`, selectOne→`select`, count→`selectCount`, insert→`insert`, update→`update`, delete→`delete`). 화면당 Mapper 1개라 화면코드 접두/접미 불필요.
- DTO 클래스명 = `{ScreenCode}` + `ReqDto`/`ResDto`
- DTO 필드 = contract.fields에서 파생 (vue_field → java 필드명, type → java_type)
- operations 종류 = 화면 type 고정세트 ∪ api_signatures 도출 op

**핵심**: operations/dtos는 LLM이 만들지 않고 코드가 screen/fields에서 파생한다. 명명이 규칙적이라, DAO·Mapper·Service가 같은 값을 참조하면 불일치가 불가능하다.

---

## 2. naming.py + derive_contract 노드

### `naming.py` (순수 함수, LLM·IO 없음)
```python
def statement_id(op: str) -> str    # "selectList"→"selectList", "selectOne"→"select", "count"→"selectCount"
def dao_method(op: str) -> str       # == statement_id (bare, namebook 공식)
def dto_class(screen_code: str, kind: str) -> str     # ("CpmsEduRsltLst","request") → "CpmsEduRsltLstReqDto"
def java_field(vue_field: str) -> str                 # camelCase 유지
def java_type(contract_type: str) -> str              # "string"→"String", "number"→"Integer", "date"→"String"...
def ops_for_screen_type(screen_type: str) -> list[str]
    # "list" → ["selectList","count"]
    # "list-detail" → ["selectList","count","selectOne","insert","update","delete"]
    # "edit"/"tab-detail" → 해당 표준 세트

# op → (statement_id, mybatis_tag) bare 매핑 상수 (namebook):
#   selectList→("selectList","select"), selectOne→("select","select"),
#   count→("selectCount","select"), insert→("insert","insert"),
#   update→("update","update"), delete→("delete","delete")
```

op_prefix/op_suffix 매핑(예: selectList→prefix=select,suffix=List; count→prefix=select,suffix=Count; insert→prefix=insert,suffix="")은 namebook 규칙 상수로 `naming.py`에 둔다.

### `derive_contract` 노드 (planner 직후, 코드만)
```
contract_extract (LLM) → planner (LLM) → ★derive_contract (코드)★ → waves → mybatis_fix → reviewer
```
```python
def derive_contract(state: dict) -> dict:
    contract = dict(state.get("contract") or {})
    plan = state.get("plan") or {}
    screen = contract.get("screen") or {}
    screen_code = _pascal(screen.get("id", ""))   # CPMSEDURSLTLST → CpmsEduRsltLst (namebook)
    try:
        ops = ops_for_screen_type(screen.get("type", "list"))
        ops = _merge_api_signature_ops(ops, contract.get("api_signatures", []))   # (a) 보정
        planned_types = {f["file_type"] for f in plan.get("files", [])}
        operations = [_build_operation(screen_code, op) for op in ops
                      if _op_file_present(op, planned_types)]    # planner 파일목록 우선
        dtos = _build_dtos(screen_code, contract.get("fields", []))
        contract["operations"] = operations
        contract["dtos"] = dtos
    except Exception as e:
        return {"events": [{"type": "log", "line": f"[CONTRACT] derive failed: {e}"}]}
    return {"contract": contract,
            "events": [{"type": "log", "line": f"[CONTRACT] derived {len(operations)} ops, {len(dtos)} dtos"}]}
```

**규칙:**
- (a) op 세트 = 화면 type 고정세트 ∪ api_signatures 도출 op (충돌 시 표준 우선)
- planner 파일목록에 대응 파일 없는 operation은 스킵 + 경고 로그
- 파생 실패(빈 fields 등) → 빈 operations/dtos + 로그, 생성 계속 (차단 아님)

---

## 3. generator 프롬프트 주입 (예방)

확장 contract의 식별자를 파일 타입별로 "REQUIRED IDENTIFIERS" 강조 섹션으로 주입한다.

### 파일 타입별 주입
| file_type | 주입 내용 |
|---|---|
| dao_impl | operations 전체 (dao_method, statement_id, param/return). "super.xxx(\"statement_id\") 호출" |
| mapper_xml | operations (statement_id, mybatis_tag, param/result). "namespace = DaoImpl FQCN" |
| service_impl | operations(dao_method 호출) + dtos(필드) |
| dto_request/response | 해당 dtos[].fields (name, java_type) 정확히 |
| vue_types | dtos fields (TS 타입 매핑) |
| db_init_sql, vue_page | 미주입 (기존대로) |

### 구현
```python
# nodes.py
def _contract_section_for(file_type: str, contract: dict) -> str:
    """파일 타입별로 operations/dtos에서 관련 식별자만 골라 명시적 지시문으로 포맷."""
    # operations 없으면 "" 반환 (기존 동작)

# generate_file 안:
spec_section = _contract_section_for(spec["file_type"], state["contract"])
base_user = (
    f"=== CONTRACT ===\n{json.dumps(contract, ensure_ascii=False)}\n\n"
    + (f"=== REQUIRED IDENTIFIERS (use EXACTLY, do not rename) ===\n{spec_section}\n\n"
       if spec_section else "")
    + f"=== GUIDE ===\n{guide}\n{_dep_context(state, spec)}\n\n"
    + f"Generate file: ..."
)
```
- `_dep_context`(Phase 1, 의존 파일 내용)와 병행 — 상호보완(식별자 명세 vs 실제 파일).

### GENERATOR_SYSTEM 보강
```
...Use the contract as the source of truth. When REQUIRED IDENTIFIERS are given,
use those exact statement ids / method names / DTO field names — never invent or
rename them.
```

---

## 4. 검증기 승격 (contract 기준 교정)

Phase 1 `mybatis_check`에 `contract` 옵션 인자를 추가. 진실 출처를 DAO super 호출 → contract로 승격. **하위호환 필수**.

### 시그니처
```python
def check_binding(files, contract=None) -> list[dict]
def autofix_binding(files, contract=None) -> tuple[dict, list[str]]
def check_dto_fields(files, contract) -> list[dict]       # 신규
def autofix_dto_fields(files, contract) -> tuple[dict, list[str]]  # 신규
```

### contract 제공 시 동작 (진실 = contract.operations)
1. Mapper namespace ≠ DaoImpl FQCN → FQCN 교정 (Phase 1과 동일)
2. Mapper statement id ∉ contract id → 가까운 contract id로 rename
3. **DAO super("id") ∉ contract id → 가까운 contract id로 rename (신규 — DAO도 교정)**
4. **DAO 메서드명 ≠ contract.dao_method → 교정 (신규)**

→ Phase 1은 Mapper만 고쳤지만, contract가 진실이면 DAO가 틀려도 교정 가능.

### DTO 필드 검증 (cross_check 승격)
- contract.dtos[].fields 기준, 생성 DTO에 계약 필드 누락 → autofix로 `private <java_type> <name>;` 선언 추가 (계약에 타입 있어 결정론). java_type 없는 필드는 스킵 + 경고.
- ServiceImpl이 계약·DTO에 없는 getter 호출 → issue (모호 → reviewer 위임)

### mybatis_fix 노드 업데이트
```python
def mybatis_fix(state):
    files = dict(state.get("files", {}))
    contract = state.get("contract")
    fixed, logs = autofix_binding(files, contract)
    fixed, dto_logs = autofix_dto_fields(fixed, contract) if contract else (fixed, [])
    remaining = check_binding(fixed, contract)
    if contract:
        remaining += check_dto_fields(fixed, contract)
    ...
```

### 폴백
contract 없거나 해당 op 누락 → Phase 1 동작(DAO 기준)으로 폴백. 안전망.

---

## 5. 테스트 전략

### `test_naming.py` (순수 함수)
- statement_id/dao_method/dto_class 파생 정확성
- java_type 매핑 (string→String, number→Integer, date→String...)
- ops_for_screen_type (list, list-detail, edit, tab-detail 세트)

### `test_derive_contract.py` (코드 노드)
- screen+fields+api_signatures → operations/dtos 파생
- op 세트 = 고정세트 ∪ api_signatures 보정
- planner 파일목록에 없는 op 스킵 + 경고
- 빈 fields → 빈 operations/dtos + 로그 (차단 안 함)

### `test_mybatis_check.py` (확장 — 하위호환 필수)
- **기존 9개 `contract=None` 그대로 통과** (하위호환)
- contract 제공 시: DAO가 틀려도 contract 기준 교정
- DAO·Mapper 둘 다 contract와 다를 때 → 셋 다 contract로 통일
- check_dto_fields: 계약 필드 누락 탐지 + autofix 필드 추가
- 계약에 없는 getter 호출 → issue (reviewer 위임)

### `test_contract_injection.py` (프롬프트 헬퍼)
- `_contract_section_for("dao_impl", contract)` → operations 식별자 포함
- `_contract_section_for("dto_request", contract)` → 해당 DTO 필드만
- operations 없으면 "" (db_init_sql/vue_page)

### 회귀
- `outputs/code` 실결함이 contract 기준에서도 0 에러로 교정

### 실 LLM e2e (1개)
- derive_contract 노드 삽입 후 그래프 정상 종료 + 생성물 DAO/Mapper id가 contract 일치

### 에러 처리
- derive_contract 파생 실패 → 빈 채 진행 + 로그
- contract/op 없음 → mybatis_check Phase 1 폴백
- 프롬프트: operations 없으면 REQUIRED IDENTIFIERS 섹션 생략
- DTO autofix: java_type 없는 필드 스킵 + 경고

---

## 6. 컴포넌트 경계

| 단위 | 한 가지 책임 | 의존 |
|------|-------------|------|
| `naming.py` | 화면코드+op → 식별자 파생 (namebook 규칙) | (없음) |
| `nodes.derive_contract` | contract에 operations/dtos 병합 (코드 노드) | naming, state |
| `nodes._contract_section_for` | 파일타입별 식별자 프롬프트 섹션 | (contract dict) |
| `mybatis_check.*(contract=)` | contract 기준 바인딩+DTO 검증·교정 | naming(거리), state |
| `build.mybatis_fix` | 노드: contract 기준 교정 적용 | mybatis_check |

각 단위는 인터페이스만으로 사용 가능하고 contract=None 하위호환을 보존한다.

---

## 7. 검증 계획

- [ ] naming 파생 함수 정확성 (id/method/class/type/op세트)
- [ ] derive_contract: 고정세트+api 보정, 파일목록 우선, 빈입력 폴백
- [ ] mybatis_check 하위호환 (contract=None 9개 통과)
- [ ] contract 기준 교정: DAO도 교정, 셋 통일
- [ ] check_dto_fields + autofix_dto_fields (누락 필드 추가)
- [ ] _contract_section_for 파일타입별 주입
- [ ] outputs/code 회귀 (contract 기준 0 에러)
- [ ] 실 LLM e2e (derive_contract 삽입 후 정상 종료, 식별자 일치)
- [ ] 기존 graph 테스트 무손상
