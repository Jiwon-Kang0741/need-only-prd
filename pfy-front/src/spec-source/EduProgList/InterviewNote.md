# 📄 Interview Note

---

## 1. 개요 (Overview)

- 화면명: 교육실적관리
- 화면 ID: SCR_EDUPROGLIST_001
- 인터뷰 대상: 준법담당자(업무 담당)
- 인터뷰 일자: 2026-04-13

---

## ✅ 유지 및 확정 (Keep)

기존 MockUp의 기능을 그대로 유지하는 항목입니다.

- [x]
  - @id: KEEP-001
  - name: 조회 결과 0건 메시지
  - detail: 조회 결과 0건 시 메시지는 ‘조회 결과가 없습니다.’로 고정한다.

- [x]
  - @id: KEEP-002
  - name: 참여여부/합격여부 YN 사용
  - detail: 참여여부(participationYn), 합격여부(passYn)는 Y/N 값으로 유지한다.

---

## ❌ 변경 및 보완 (Change)

기존 MockUp 컴포넌트의 수정 또는 제거가 필요한 항목입니다.

| @id | asIs | toBe | rule |
| :--- | :--- | :--- | :--- |
| CHG-001 | 교육실적 PK가 복합키(사번+과정+일자 등) 또는 미정 | eduResultId 단일키(Primary Key) 생성 | DB/DTO에 eduResultId 추가 및 상세조회/삭제 기준키로 사용 |
| CHG-002 | 교육일자 저장 타입 DATE | 교육일자 저장 타입 DATETIME, KST 기준(향후 locale에 따라 변경 가능) | 기간검색은 포함(>=from, <=to)로 처리 |
| CHG-003 | 검색 조건 성명/부서가 단순 텍스트 입력(가정) | 성명/부서는 코드검색 기반으로 진행(성명은 부분일치 + 대소문자/공백/초성 지원) | 성명 검색은 LIKE + 추가 검색옵션(초성/정규화) 적용 |
| CHG-004 | 목록 기본 정렬이 교육일자 등 다른 기준(가정) | 기본 정렬: 사번 오름차순, 다중정렬 지원 | 정렬 파라미터(sort) 다중 전달 허용 |
| CHG-005 | 등록이 단건 입력(가정) | 등록 버튼은 엑셀 업로드 일괄등록으로 처리 | 업로드 검증 및 중복 차단 규칙 적용 |
| CHG-006 | 삭제가 단건 삭제 또는 논리삭제(가정) | 체크박스 다건 삭제 + 물리삭제, 삭제 전 확인 팝업 | 삭제 가능 조건: 교육과정이 ‘활성’인 건만 삭제 |
| CHG-007 | 화면 접근 권한이 일반 사용자 포함(가정) | 해당 화면은 준법담당자만 접근 가능(조회/등록/삭제/엑셀다운로드 포함) | 403 시 접근 차단 페이지로 이동 |
| CHG-008 | 과정명이 단순 문자열 저장(가정) | 과정코드(및 과정ID/버전) 마스터 연계 + 실적에는 ‘당시 명칭’ 스냅샷 표시/저장 | 조회 표시는 당시명칭 기준, 마스터 키는 별도 저장 |

---

## 💡 추가 요구 (Add)

새로운 기능이나 데이터 항목을 추가하는 섹션입니다.

| priority | @id | name | detail | impact |
| :--- | :--- | :--- | :--- | :--- |
| High | ADD-001 | 엑셀 업로드 일괄등록 | 등록 버튼 클릭 시 엑셀 파일 업로드로 교육실적을 일괄 생성한다. | 업로드 API/검증/에러리포트 응답 필요 |
| High | ADD-002 | 중복 차단 규칙(사번+교육과정) | 교육과정, 사번 기준으로 중복 여부 체크하여 중복 시 등록 차단한다(과정은 차수별 신규 생성 전제). | 등록 API에서 중복검사 및 에러코드 정의 필요 |
| High | ADD-003 | 과정 마스터 연계 키/버전 | 과정ID/과정코드/버전(개정) 관리 및 실적과 연계한다. | 코드/마스터 조회 API 및 DB FK/참조 필요 |
| Mid | ADD-004 | 다건 삭제(체크박스) | 목록에서 체크박스로 선택한 다건을 물리삭제한다. | DELETE 배치 API 필요 |
| Mid | ADD-005 | 성명/부서 코드검색 | 성명/부서는 코드검색(검색 팝업/자동완성 등)으로 선택한다. 성명은 부분일치 + 대소문자/공백/초성 지원. | 인사(직원/부서) 검색 API 필요 |
| Mid | ADD-006 | 오류 처리 UX | 403은 접근 차단 페이지, 5xx/네트워크 오류는 오류페이지 이동, 엑셀 다운로드 실패 시 안내 문구 표시 | 공통 에러 핸들링/메시지 표준 필요 |
| Low | ADD-007 | 삭제 확인 팝업 | 삭제 실행 전 확인 팝업을 제공한다. | 프론트 UX 추가(백엔드 영향 낮음) |

### priority ENUM
- High
- Mid
- Low

---

## 🚫 제외 기능 (Out of Scope)

이번 개발 범위에서 제외되는 항목입니다.

- @id: OUT-001
  - name: 해당 없음
  - reason: 인터뷰에서 명시적으로 제외된 기능이 없음

---

## 📊 Data Spec (Technical Definition)

Spec.md 및 DB DDL 자동 생성을 위한 기술 명세입니다.

| @id | field | type | required | operator | description | source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CHG-001 | eduResultId | string(50) | Y | EQ | 교육실적 식별자(단일 PK) | Change |
| ADD-002 | employeeNo | string(50) | Y | EQ | 사번 | Add |
| ADD-005 | employeeName | string(100) | N | LIKE | 성명(검색/표시), 부분일치 + 대소문자/공백/초성 지원 | Add |
| ADD-005 | departmentName | string(100) | N | LIKE | 부서명(검색/표시), 코드검색 기반 | Add |
| ADD-003 | trainingCourseId | string(50) | Y | EQ | 교육과정 ID(마스터 키) | Add |
| ADD-003 | trainingCourseCode | string(50) | Y | EQ | 교육과정 코드(마스터 연계) | Add |
| ADD-003 | trainingCourseVersion | string(20) | Y | EQ | 교육과정 버전(개정) | Add |
| CHG-008 | trainingCourseNameSnapshot | string(500) | Y | LIKE | 교육과정명(당시 명칭 스냅샷) | Change |
| CHG-002 | trainingDateTime | datetime | Y | BETWEEN | 교육일시(DATETIME), KST 기준(향후 locale 변경 가능) | Change |
| KEEP-002 | participationYn | boolean | Y | EQ | 참여여부(Y/N) | Keep |
| ADD-001 | examScore | number(3) | Y | EQ | 시험점수(정수), 0~100 | Add |
| KEEP-002 | passYn | boolean | N | EQ | 합격여부(Y/N) | Keep |
| CHG-007 | createdBy | string(50) | N | EQ | 생성자(감사/추적용, 권한 통제 연계) | Change |
| CHG-007 | createdAt | datetime | N | BETWEEN | 생성일시 | Change |

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
| ordering | CHG-004 | 기본 정렬은 employeeNo 오름차순. 다중정렬 지원(예: sort=employeeNo,asc&sort=trainingDateTime,desc). |
| pagination | TBD-001 | 목록 페이징 방식(page/size) 및 기본/최대 size는 추후 확정 필요. |
| permission | CHG-007 | 화면 접근은 준법담당자만 허용. 준법담당자는 조회/등록(엑셀업로드)/삭제/엑셀다운로드 가능. 403 발생 시 접근 차단 페이지로 이동. |
| validation | ADD-002 | 등록(엑셀업로드) 시 필수: employeeNo, trainingCourse(연계키), trainingDateTime, participationYn, examScore. 중복키(employeeNo+trainingCourseId 또는 courseCode 기준) 존재 시 차단. |
| validation | ADD-001 | examScore는 정수이며 0~100 범위만 허용. |
| validation | CHG-006 | 삭제는 체크박스 다건 물리삭제. 삭제 가능 조건: 교육과정이 ‘활성’ 상태인 실적만 삭제 가능. 삭제 전 확인 팝업 필수. |
| validation | CHG-002 | 기간검색은 from/to 포함(>=from, <=to). 저장은 DATETIME이며 기준 시간대는 KST(향후 locale에 따라 변경 가능). |
| validation | CHG-008 | 교육과정은 마스터(과정코드/ID/버전)와 연계하며, 화면 표시는 당시명칭 스냅샷(trainingCourseNameSnapshot) 기준. |
| validation | CHG-003 | 성명 검색은 부분일치(LIKE)이며 대소문자/공백/초성 검색을 지원. 성명/부서는 코드검색으로 선택 가능해야 함. |
| validation | CHG-007 | 부서 기준은 ‘교육 당시 소속 부서’ 기준으로 조회/표시한다. |

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
| API-001 | GET | /api/edu-results | 교육실적 목록 조회(검색/정렬/페이징) | employeeNo(string, EQ), employeeName(string, LIKE), departmentId(string, EQ), trainingCourseId(string, EQ), trainingCourseCode(string, EQ), fromDateTime(datetime, BETWEEN), toDateTime(datetime, BETWEEN), participationYn(boolean, EQ), passYn(boolean, EQ), sort(string, IN), page(number, EQ), size(number, EQ) | list: EduResultDTO[], totalCount(number) | CHG-002, CHG-003, CHG-004, ADD-005, TBD-001 |
| API-002 | GET | /api/edu-results/{eduResultId} | 교육실적 상세 조회 | eduResultId(string, EQ) | eduResultId(string), employeeNo(string), employeeName(string), departmentName(string), trainingCourseId(string), trainingCourseCode(string), trainingCourseVersion(string), trainingCourseNameSnapshot(string), trainingDateTime(datetime), participationYn(boolean), examScore(number), passYn(boolean) | CHG-001, CHG-008, ADD-003 |
| API-003 | POST | /api/edu-results/excel-upload | 교육실적 엑셀 업로드 일괄등록 | file(string, EQ) | successCount(number), failCount(number), errors: UploadErrorDTO[] | ADD-001, ADD-002, CHG-005 |
| API-004 | DELETE | /api/edu-results | 교육실적 다건 삭제(물리삭제) | eduResultIds(string, IN) | deletedCount(number) | CHG-006, ADD-004 |
| API-005 | GET | /api/training-courses | 교육과정 마스터 목록/검색(코드/버전 포함) | keyword(string, LIKE), courseCode(string, EQ), activeYn(boolean, EQ), page(number, EQ), size(number, EQ) | list: TrainingCourseDTO[], totalCount(number) | ADD-003, CHG-008 |
| API-006 | GET | /api/hr/employees | 직원 코드검색(성명 부분일치 + 대소문자/공백/초성 지원) | name(string, LIKE), employeeNo(string, EQ), deptId(string, EQ), page(number, EQ), size(number, EQ) | list: EmployeeDTO[], totalCount(number) | CHG-003, ADD-005 |
| API-007 | GET | /api/hr/departments | 부서 코드검색 | keyword(string, LIKE), page(number, EQ), size(number, EQ) | list: DepartmentDTO[], totalCount(number) | CHG-003, ADD-005 |
| API-008 | GET | /api/edu-results/excel-download | 교육실적 엑셀 다운로드 | employeeNo(string, EQ), employeeName(string, LIKE), departmentId(string, EQ), trainingCourseId(string, EQ), fromDateTime(datetime, BETWEEN), toDateTime(datetime, BETWEEN), sort(string, IN) | fileName(string), fileContentBase64(string) | CHG-007, ADD-006 |

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
  - name: 목록 페이징 정책
  - reason: page/size 사용 여부, 기본 size, 최대 size, 무한스크롤 여부가 인터뷰에서 확정되지 않음

- @id: TBD-002
  - name: 미참여 시 시험점수/합격여부 저장 규칙
  - reason: participationYn=N일 때 examScore/passYn을 NULL로 둘지(또는 0/N) 저장 규칙이 확정되지 않음

- @id: TBD-003
  - name: 중복 체크의 정확한 키 정의
  - reason: “교육과정, 사번” 중복 차단으로 합의했으나, 교육과정 기준을 trainingCourseId vs trainingCourseCode+version 중 무엇으로 할지 확정 필요

- @id: TBD-004
  - name: DATETIME 시간대 처리 방식
  - reason: 현재 KST 기준이나 향후 locale에 따라 변경 필요. 저장/조회 시 timezone 변환 정책(UTC 저장 여부 등) 미확정

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