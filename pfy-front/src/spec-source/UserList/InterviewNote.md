# 📄 Interview Note

---

## 1. 개요 (Overview)

- 화면명: 사용자관리
- 화면 ID: SCR_USERLIST_001
- 인터뷰 대상: TBD
- 인터뷰 일자: 2026-04-10

---

## ✅ 유지 및 확정 (Keep)

기존 MockUp의 기능을 그대로 유지하는 항목입니다.

- [x]
  - @id: KEEP-001
  - name: 사용자 목록 조회는 서버 페이징 처리
  - detail: 사용자 목록은 서버에서 페이징/필터링 처리한다(클라이언트 전체 다운로드 방식 미사용).

- [x]
  - @id: KEEP-002
  - name: 목록 응답 스펙 유지
  - detail: 목록 API 응답은 `{items, total, page, size}` 구조를 유지한다.

---

## ❌ 변경 및 보완 (Change)

기존 MockUp 컴포넌트의 수정 또는 제거가 필요한 항목입니다.

| @id | asIs | toBe | rule |
| :--- | :--- | :--- | :--- |
| CHG-001 | total = 필터 적용 후 전체 건수 | total = 필터 적용 전 전체 건수 | 목록 응답의 total은 “필터 미적용 전체 건수” 기준으로 반환 |
| CHG-002 | 통합검색 대상: userId/userName/email | 통합검색 대상: userId/userName/email + empNo(사번) | keyword는 4개 필드에 대해 부분일치(contains)로 검색 |
| CHG-003 | 부서 조건: 부서명 자유입력 + 부분일치 | 부서명 검색 후 부서코드 선택(조직도/부서코드 기반) → deptCode로 사용자 조회 | 조회 파라미터는 deptCode(EQ) 사용(부서명은 선택 UI용) |
| CHG-004 | deptId를 FK로 저장 | deptId FK 제거 | 사용자 데이터는 deptCode/deptName 등 비FK 방식으로 관리(정합성은 별도 규칙으로 보완) |
| CHG-005 | lastLoginDate/createdDate = DATE | lastLoginAt/createdAt = datetime(KST) | 날짜 필드는 datetime으로 저장/표시하며 타임존은 KST 기준 |
| CHG-006 | 권한: 다중 가능성/표기 불명확 | 권한(roleCode)은 단일값 고정, 목록 표시는 대표 권한 1개 | roleCode는 단일값이며 목록/조회 모두 단일 기준 |
| CHG-007 | useYn 체크박스(사용중만) | 상태 필터: 전체/사용/미사용 3상태 + statusCode 확장 | 상태는 statusCode(ACTIVE/DORMANT/LOCKED) 기반으로 확장하고 UI는 3상태 선택 제공 |
| CHG-008 | 등록일 필터 기준/포함여부/타임존 불명확 | 생성일(createdAt) 기준, From/To 포함(BETWEEN), KST | createdFrom~createdTo는 포함 조건으로 처리 |
| CHG-009 | 정렬: 단일 정렬 또는 미정 | 멀티 정렬 지원, 파라미터 규격 `sort=createdAt,desc` | sort는 다중 전달 가능(예: sort=createdAt,desc&sort=userId,asc) |
| CHG-010 | 상세조회/수정 화면 이동 가능성 | 본 화면은 조회 전용(상세 이동 없음) | 행 클릭/ID 클릭 시 상세 라우팅/수정 기능 제공하지 않음 |
| CHG-011 | 오류 UX 미정 | 401 로그인 이동, 403/500/타임아웃은 에러메시지만 표시 | 오류코드별 UX 정책 고정(재시도 버튼 등 미정책) |

---

## 💡 추가 요구 (Add)

새로운 기능이나 데이터 항목을 추가하는 섹션입니다.

| priority | @id | name | detail | impact |
| :--- | :--- | :--- | :--- | :--- |
| High | ADD-001 | statusCode 도입 | 사용자 상태코드 `ACTIVE/DORMANT/LOCKED`를 조회/표시/필터에 사용 | API 파라미터 및 응답 필드 추가, 코드 조회 필요 |
| High | ADD-002 | 상태 필터 3상태 UX | 상태 필터를 `전체/사용/미사용` 3상태로 제공(전체는 필터 미적용) | 검색조건 UI 및 API 파라미터 매핑 필요 |
| Mid | ADD-003 | 부서 코드 선택 UI 지원 | 부서명 검색(자동완성/조직도) 후 deptCode 선택하여 조회 | 부서 검색/조직 조회 API 필요 |
| Mid | ADD-004 | 통합검색 입력 유효성 규칙 | 소문자 구분(대소문자 정책), 공백/특수문자만 입력 시 처리 규칙 적용 | 프론트/백엔드 validation 및 에러 메시지 규칙 필요 |
| Mid | ADD-005 | 멀티 정렬 파라미터 처리 | `sort=field,dir`를 복수로 받아 우선순위대로 정렬 | 목록 API 정렬 파라미터 확장 |
| Low | ADD-006 | roleCode 다중 선택 검색(OR) | roleCode는 단일값이지만 검색조건은 복수 선택 가능하며 OR로 적용 | API에서 roleCode IN 처리 필요 |

### priority ENUM
- High
- Mid
- Low

---

## 🚫 제외 기능 (Out of Scope)

이번 개발 범위에서 제외되는 항목입니다.

- @id: OUT-001
  - name: 사용자 상세조회/수정/토글/삭제 화면 및 기능
  - reason: 인터뷰에서 “조회 전용”으로 확정되어 상세 라우팅 및 CRUD는 범위 제외

---

## 📊 Data Spec (Technical Definition)

Spec.md 및 DB DDL 자동 생성을 위한 기술 명세입니다.

| @id | field | type | required | operator | description | source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| KEEP-001 | page | number(10) | Y | EQ | 페이지 번호(0 또는 1 기반은 TBD, API에서 일관 적용) | Keep |
| KEEP-001 | size | number(10) | Y | EQ | 페이지 크기 | Keep |
| CHG-001 | total | number(10) | Y | EQ | 필터 미적용 전체 건수(전체 사용자 수) | Change |
| KEEP-002 | items | string(0) | Y | EQ | 사용자 목록 배열(구조는 아래 User Row 필드로 정의) | Keep |
| KEEP-002 | page | number(10) | Y | EQ | 응답 페이지 번호 | Keep |
| KEEP-002 | size | number(10) | Y | EQ | 응답 페이지 크기 | Keep |
| CHG-002 | keyword | string(200) | N | LIKE | 통합검색 키워드(userId/userName/email/empNo 대상, contains) | Change |
| CHG-003 | deptCode | string(20) | N | EQ | 선택된 부서 코드(부서명 검색 후 코드로 조회) | Change |
| ADD-003 | deptNameKeyword | string(100) | N | LIKE | 부서명 검색 키워드(부서 선택 UI용) | Add |
| CHG-006 | roleCode | string(20) | N | IN | 권한 코드(검색은 복수 선택 OR → IN 처리) | Change |
| CHG-007 | statusCode | string(20) | N | EQ | 사용자 상태코드(ACTIVE/DORMANT/LOCKED) | Change |
| ADD-002 | useFilter | string(10) | N | EQ | 3상태 필터 값(ALL/USE/UNUSE) → statusCode로 매핑 | Add |
| CHG-008 | createdFrom | datetime | N | BETWEEN | 생성일 시작(KST, 포함) | Change |
| CHG-008 | createdTo | datetime | N | BETWEEN | 생성일 종료(KST, 포함) | Change |
| CHG-009 | sort | string(200) | N | EQ | 멀티 정렬 파라미터(예: createdAt,desc) | Change |
| CHG-004 | userId | string(50) | Y | EQ | 사용자 ID(PK) | Change |
| CHG-004 | userName | string(50) | Y | LIKE | 사용자명(최대 50) | Change |
| CHG-002 | email | string(254) | N | LIKE | 이메일(형식 검증은 TBD) | Change |
| CHG-002 | empNo | string(30) | N | LIKE | 사번(통합검색 대상 포함) | Change |
| CHG-003 | deptName | string(100) | N | LIKE | 부서명(표시용) | Change |
| CHG-006 | roleCode | string(20) | Y | EQ | 사용자 권한 코드(단일값) | Change |
| ADD-001 | statusCode | string(20) | Y | EQ | 사용자 상태코드(ACTIVE/DORMANT/LOCKED) | Add |
| CHG-005 | lastLoginAt | datetime | N | EQ | 최종 로그인 일시(KST) | Change |
| CHG-005 | createdAt | datetime | Y | EQ | 생성 일시(KST) | Change |

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
| pagination | BR-001 | 목록은 서버 페이징 필수이며 응답은 items/total/page/size를 반환한다(KEEP-001, KEEP-002). total은 필터 미적용 전체 건수 기준이다(CHG-001). |
| ordering | BR-002 | 멀티 정렬을 지원하며 요청 파라미터는 `sort=field,dir` 형식으로 복수 전달 가능하다(CHG-009). |
| permission | BR-003 | API 401은 로그인 화면으로 이동, 403은 권한 없음 메시지만 표시한다(CHG-011). |
| validation | BR-004 | 통합검색 keyword는 userId/userName/email/empNo에 대해 contains(LIKE)로 매칭한다(CHG-002). 공백/특수문자만 입력 시 처리 규칙 및 소문자 구분 정책을 적용한다(ADD-004). |
| validation | BR-005 | 생성일 필터는 createdAt 기준이며 From/To는 포함(BETWEEN) 처리, 타임존은 KST로 해석한다(CHG-008, CHG-005). |
| validation | BR-006 | 상태 필터는 3상태(전체/사용/미사용)이며 내부적으로 statusCode(ACTIVE/DORMANT/LOCKED)로 확장/매핑한다(CHG-007, ADD-001, ADD-002). |
| permission | BR-007 | 500/타임아웃은 에러메시지만 표시하며 별도 재시도 UX는 정의하지 않는다(CHG-011). |

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
| API-001 | GET | /api/users | 사용자 목록 조회(서버 페이징/필터/정렬) | keyword(string, LIKE), deptCode(string, EQ), roleCode(string, IN), statusCode(string, EQ), createdFrom(datetime, BETWEEN), createdTo(datetime, BETWEEN), page(number, EQ), size(number, EQ), sort(string, EQ) | items(UserDTO[], EQ), total(number, EQ), page(number, EQ), size(number, EQ) | KEEP-001, KEEP-002, CHG-001, CHG-002, CHG-003, CHG-006, CHG-007, CHG-008, CHG-009 |
| API-002 | GET | /api/departments | 부서 검색/선택용 목록(부서명으로 검색 후 코드 선택) | deptNameKeyword(string, LIKE), page(number, EQ), size(number, EQ) | items(DeptDTO[], EQ), total(number, EQ), page(number, EQ), size(number, EQ) | CHG-003, ADD-003 |
| API-003 | GET | /api/codes/roles | 권한 코드 목록 조회(필터 UI 구성) | codeGroup(string, EQ) | items(CodeDTO[], EQ) | CHG-006, ADD-006 |
| API-004 | GET | /api/codes/user-status | 사용자 상태 코드 목록 조회(ACTIVE/DORMANT/LOCKED) | codeGroup(string, EQ) | items(CodeDTO[], EQ) | CHG-007, ADD-001, ADD-002 |

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

- @id: TBD-001
  - name: keyword 대소문자(소문자 구분) 처리의 정확한 정의
  - reason: “소문자 구분 규칙 포함”만 확정되었고, DB collation/정규화(lowercase 변환) 적용 여부가 미정

- @id: TBD-002
  - name: 공백/특수문자만 입력 시 keyword 처리 방식
  - reason: 허용/차단/무시(필터 미적용)/에러 처리 중 어떤 정책인지 미정

- @id: TBD-003
  - name: email 필수 여부/UNIQUE 여부/형식 검증 규칙
  - reason: userName 길이/PK/datetime만 확정되었고 이메일 제약 조건은 미확정

- @id: TBD-004
  - name: userId 허용문자/중복정책(=PK 외 추가 정책) 및 길이
  - reason: userId가 PK인 것은 확정이나 허용문자/최대길이/생성규칙은 미정

- @id: TBD-005
  - name: createdFrom/createdTo 단일 입력 허용 여부 및 page 번호 기준(0/1 base)
  - reason: From/To 포함 및 KST는 확정이나 단일 입력 허용과 페이지 기준은 미정

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