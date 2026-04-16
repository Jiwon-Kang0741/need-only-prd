# 📄 Interview Note

---

## 1. 개요 (Overview)

- 화면명: ${req.title}
- 화면 ID: SCR_XXX_001
- 인터뷰 대상:
- 인터뷰 일자: YYYY-MM-DD

---

## ✅ 유지 및 확정 (Keep)

기존 MockUp의 기능을 그대로 유지하는 항목입니다.

- [x]
  - @id: 
  - name: 
  - detail: 

- [x]
  - @id: 
  - name: 
  - detail: 

---

## ❌ 변경 및 보완 (Change)

기존 MockUp 컴포넌트의 수정 또는 제거가 필요한 항목입니다.

| @id | asIs | toBe | rule |
| :--- | :--- | :--- | :--- |
|  |  |  |  |

---

## 💡 추가 요구 (Add)

새로운 기능이나 데이터 항목을 추가하는 섹션입니다.

| priority | @id | name | detail | impact |
| :--- | :--- | :--- | :--- | :--- |
| High |  |  |  | (예: API 파라미터 추가) |

### priority ENUM
- High
- Mid
- Low

---

## 🚫 제외 기능 (Out of Scope)

이번 개발 범위에서 제외되는 항목입니다.

- @id: 
  - name: 
  - reason: 

---

## 📊 Data Spec (Technical Definition)

Spec.md 및 DB DDL 자동 생성을 위한 기술 명세입니다.

| @id | field | type | required | operator | description | source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
|  |  |  |  |  |  |  |

### Type Rules (STRICT)

- string(n)
- number(n)
- date
- datetime
- boolean

### Operator Rules (STRICT)

- EQ
- LIKE
- BETWEEN
- IN
- GT
- LT

### Source Rules

- Keep
- Change
- Add

---

## ⚙️ 비즈니스 규칙 (Business Rules)

시스템 동작을 정의하는 핵심 규칙입니다.

| type | @id | rule |
| :--- | :--- | :--- |
| ordering |  |  |
| pagination |  |  |
| permission |  |  |
| validation |  |  |

### type ENUM

- ordering
- pagination
- permission
- validation

---

## 🔌 API 정의 (API Specification)

인터뷰 결과를 바탕으로 도출된 API 엔드포인트 목록입니다.

| @id | method | endpoint | description | requestParams | responseFields | relatedIds |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
|  |  |  |  |  |  |  |

### method ENUM
- GET
- POST
- PUT
- PATCH
- DELETE

### requestParams 작성 규칙
- 파라미터명(타입, operator) 형식으로 나열
- 예: `loginId(string, LIKE), deptId(string, EQ), page(number, EQ)`

### responseFields 작성 규칙
- 필드명(타입) 형식으로 나열
- 예: `list: UserDTO[], totalCount: number`

### relatedIds 작성 규칙
- 관련된 Keep/Change/Add/TBD @id를 쉼표로 나열
- 예: `KEEP-001, CHG-001, ADD-002`

---

## ⚠️ 미결 사항 (TBD)

추후 결정이 필요한 항목입니다.

- @id: 
  - name: 
  - reason: 

---

## 🔗 데이터 무결성 규칙 (Data Integrity Rules)

- 모든 항목은 반드시 @id 포함
- 동일 @id 중복 금지
- Data Spec의 @id는 반드시 상위 섹션(Keep/Change/Add)과 연결
- orphan 데이터 금지

---

## 🧠 JSON 변환 기준 (For System Use)

이 문서는 반드시 아래 구조로 변환 가능해야 한다:

- keep: []
- change: []
- add: []
- outOfScope: []
- dataSpec: []
- businessRules: []
- apiSpec: []
- tbd: []

---

## ⚠️ 작성 규칙 (LLM Strict Rules)

- 템플릿 구조 절대 변경 금지
- 섹션 순서 변경 금지
- 테이블 구조 유지 필수
- 빈 필드 없이 작성
- 자유 텍스트 최소화
- 반드시 구조화된 값 사용