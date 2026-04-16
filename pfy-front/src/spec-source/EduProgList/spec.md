# 📄 교육실적관리 Technical Specification (spec.md)

> **화면 ID**: SCR_EDUPROGLIST_001  
> **화면명**: 교육실적관리  
> **기준 일자**: 2026-04-13  
> **Source Priority**: `InterviewNote.md` > `Component.vue`

---

## 0. Global Rules (Strict)

- **Primary Key Strategy**: UUID (Default)
- **Naming Convention**:
  - **Entities**: PascalCase
  - **Fields/APIs/Query Parameters**: camelCase
  - **Database Tables**: snake_case
- **Architecture Rules**:
  - All Business Logic **MUST** be implemented in **Service Layer**.
  - Controllers **MUST** be thin (no business logic, only routing & validation).
  - Soft Delete **MUST** be applied using `deletedAt` field.
  - All APIs **MUST** follow **REST Level 2+**.
- **Source Priority**: `InterviewNote.md` > `Component.vue`

---

## 1. Requirement Refinement

### Functional

- 교육실적 목록 조회 (검색/정렬/페이징)
- 교육실적 엑셀 업로드 일괄등록 (필수/중복/유효성 검증 포함) `[MEETING OVERRIDE: 단건 입력 → 엑셀 업로드 일괄등록]`
- 교육실적 체크박스 다건 물리삭제 (삭제 전 확인 팝업, 활성 과정 건만 허용) `[MEETING OVERRIDE: 단건/논리삭제(가정) → 다건 + 물리삭제]`
- 교육실적 엑셀 다운로드 (현재 검색 조건 기반)
- 교육과정 마스터 코드 조회 (과정코드/버전/활성여부 포함)
- 부서 코드검색 (선택용)
- 사원 코드검색 (성명/사번, 초성·공백·대소문자 무시 검색)
- 조회 결과 0건 시 '조회 결과가 없습니다.' 고정 메시지 표시
- 403 발생 시 접근 차단 페이지 이동, 5xx/네트워크 오류 시 오류 페이지 이동
- 교육일자 기간 검색 포함 조건 (≥from, ≤to, DATETIME 기준, KST 저장)
- 기본 정렬: 사번(employeeNo) ASC, 사용자 다중 정렬 지원 `[MEETING OVERRIDE: 기존 미정 → employeeNo ASC]`
- 참여여부(participationYn) / 합격여부(passYn) Y/N 필터 제공

### Non-Functional

- **Performance**: API response time < 300ms
- **Security**: JWT 기반 인증 + RBAC (준법담당자 role만 화면 접근 허용)
- **Scalability**: Stateless architecture

### Constraints

- **Tech Stack**: Spring Boot 3.x, Java 21, JPA, Querydsl
- **Access Control**: 준법담당자만 접근 가능. 403 시 접근 차단 페이지 이동
- **삭제**: 물리삭제(hard delete). 단, 교육과정 비활성 건은 삭제 불가
- **페이징**: `[NEEDS CLARIFICATION: page/size 기본값, 최대 size, 다중 sort 파라미터 포맷 미확정 — TBD-001]`
- **External Integration**: 교육과정 마스터(courses), 사원/부서 마스터 연동

---

## 2. Atomic User Stories

- **US-01**: As a 준법담당자, I want to search training records by employee name/department/course/date range, so that I can quickly find specific records.
- **US-02**: As a 준법담당자, I want to upload an Excel file to register multiple training records at once, so that bulk data entry is efficient.
- **US-03**: As a 준법담당자, I want to select multiple records via checkbox and delete them, so that I can clean up incorrect data.
- **US-04**: As a 준법담당자, I want to download the current search results as an Excel file, so that I can share or archive data externally.
- **US-05**: As a 준법담당자, I want duplicate training records (same employeeNo + courseId) to be blocked on upload, so that data integrity is maintained.
- **US-06**: As a 준법담당자, I want the system to store the course name at the time of training as a snapshot, so that course name changes do not affect historical records.
- **US-07**: As a 준법담당자, I want the department shown to reflect the employee's department at the time of training, so that historical accuracy is preserved.
- **US-08**: As a 시스템, I want to block access for non-준법담당자 users and redirect them to an access-denied page (403), so that unauthorized access is prevented.

---

## 3. Domain Modeling (Core)

### Entity: EduResult (Table: `edu_result`)

| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | UUID | uuid | false | PK | - | Primary Key |
| eduResultId | String | String | varchar(50) | false | UNIQUE | @NotBlank, size≤50 | 교육실적 단일 식별키(업무 키) |
| employeeNo | String | String | varchar(50) | false | - | @NotBlank, size≤50 | 사번 |
| employeeName | String | String | varchar(100) | true | - | size≤100 | 성명 |
| departmentId | String | String | varchar(50) | true | FK→Department | size≤50 | 부서 코드 |
| departmentNameSnapshot | String | String | varchar(100) | true | - | size≤100 | 교육 당시 부서명 스냅샷 |
| courseId | String | String | varchar(50) | false | FK→Course | @NotBlank, size≤50 | 교육과정 ID (마스터 연계) |
| courseCode | String | String | varchar(50) | false | - | @NotBlank, size≤50 | 교육과정 코드 |
| courseVersion | String | String | varchar(20) | false | - | @NotBlank, size≤20 | 교육과정 버전/개정 |
| trainingCourseNameSnapshot | String | String | varchar(500) | false | - | @NotBlank, size≤500 | 교육 당시 과정명 스냅샷 |
| trainingDateTime | DateTime | LocalDateTime | datetime | false | - | @NotNull | 교육일시 (DATETIME, KST 기준 저장) |
| participationYn | Boolean | Boolean | char(1) | false | - | @NotNull | 참여여부 (Y/N) |
| examScore | Integer | Integer | int | false | 0≤score≤100 | @NotNull, @Min(0), @Max(100) | 시험점수 (정수) |
| passYn | Boolean | Boolean | char(1) | true | - | - | 합격여부 (Y/N) |
| uploadBatchId | String | String | varchar(50) | true | - | - | 업로드 배치 ID (일괄등록 그룹 식별) |
| createdAt | DateTime | LocalDateTime | datetime | false | - | - | 생성일 |
| updatedAt | DateTime | LocalDateTime | datetime | false | - | - | 수정일 |

> **[ASSUMED: 물리삭제(hard delete) 정책으로 deletedAt 컬럼 불필요. CHG-005 기준.]**

---

### Entity: Course (Table: `course`)

| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | UUID | uuid | false | PK | - | Primary Key |
| courseCode | String | String | varchar(50) | false | UNIQUE | @NotBlank | 과정 코드 |
| courseVersion | String | String | varchar(20) | false | - | @NotBlank | 과정 버전/개정 |
| courseName | String | String | varchar(500) | false | - | @NotBlank | 과정명 |
| activeYn | Boolean | Boolean | char(1) | false | - | @NotNull | 활성여부 (Y=활성, N=비활성) |
| createdAt | DateTime | LocalDateTime | datetime | false | - | - | 생성일 |
| updatedAt | DateTime | LocalDateTime | datetime | false | - | - | 수정일 |
| deletedAt | DateTime | LocalDateTime | datetime | true | - | - | 삭제일 (Soft Delete) |

---

### Entity: Department (Table: `department`)

| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | UUID | uuid | false | PK | - | Primary Key |
| departmentId | String | String | varchar(50) | false | UNIQUE | @NotBlank | 부서 코드 |
| departmentName | String | String | varchar(100) | false | - | @NotBlank | 부서명 |
| createdAt | DateTime | LocalDateTime | datetime | false | - | - | 생성일 |
| updatedAt | DateTime | LocalDateTime | datetime | false | - | - | 수정일 |
| deletedAt | DateTime | LocalDateTime | datetime | true | - | - | 삭제일 (Soft Delete) |

---

### Entity: Employee (Table: `employee`)

| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | UUID | uuid | false | PK | - | Primary Key |
| employeeNo | String | String | varchar(50) | false | UNIQUE | @NotBlank | 사번 |
| employeeName | String | String | varchar(100) | false | - | @NotBlank | 성명 |
| departmentId | String | String | varchar(50) | true | FK→Department | - | 소속 부서 코드 |
| createdAt | DateTime | LocalDateTime | datetime | false | - | - | 생성일 |
| updatedAt | DateTime | LocalDateTime | datetime | false | - | - | 수정일 |
| deletedAt | DateTime | LocalDateTime | datetime | true | - | - | 삭제일 (Soft Delete) |

---

### Relationships

- **Course (1:N) EduResult**
  - FK: `course_id` (in edu_result)
  - Owner: `EduResult`
  - Mapping: `@OneToMany(mappedBy = "course")` / `@ManyToOne(FetchType.LAZY)`

- **Department (1:N) EduResult**
  - FK: `department_id` (in edu_result)
  - Owner: `EduResult`
  - Mapping: `@OneToMany(mappedBy = "department")` / `@ManyToOne(FetchType.LAZY)`

---

### Enums

- **ParticipationYn**: `Y`, `N`
  - Mockup 출처: `search.completionStatus` select 옵션 / participationYn 필드 기반
- **PassYn**: `Y`, `N`
  - Mockup 출처: passYn 필드 기반

---

## 4. Business Logic Rules

- **[Validation]** `examScore`는 정수이며 0~100 범위만 허용. (CHG-004)
- **[Validation]** 엑셀 업로드 필수 컬럼: `employeeNo`, `courseId`(또는 과정코드+버전), `trainingDateTime`, `participationYn`, `examScore`. `passYn`은 선택. (ADD-004)
- **[Validation]** 중복 등록 차단: `employeeNo` + `courseId`(또는 `courseCode`+`courseVersion`) 조합 중복 시 해당 행 실패 처리 또는 전체 실패 처리. 에러 코드 및 실패 리포트 응답 필수. (ADD-002)
- **[Validation]** 교육일자 기간 검색 포함 조건: `trainingDateTime >= fromTrainingDateTime`, `trainingDateTime <= toTrainingDateTime`. 한쪽만 입력 시 해당 조건만 적용. (ADD-007)
- **[Validation]** 삭제 가능 조건: 연결된 교육과정의 `courseActiveYn = Y`(활성)인 건만 삭제 허용. 비활성 과정 건 포함 삭제 요청 시 오류 반환. (ADD-006)
- **[Auth]** 화면 접근: 준법담당자(ROLE_COMPLIANCE) 전용. 403 발생 시 접근 차단 페이지로 이동. 기능별 권한: 조회/등록(엑셀업로드)/삭제/엑셀다운로드 모두 준법담당자만 가능. (CHG-006)
- **[Auth]** 버튼 표시: 권한 없는 사용자에게는 등록/삭제/엑셀다운로드 버튼 비표시 또는 비활성화. (ADD-008)
- **[Ordering]** 기본 정렬: `employeeNo ASC`. 사용자 다중 정렬 허용 컬럼: `employeeNo`, `employeeName`, `departmentNameSnapshot`, `trainingDateTime`, `trainingCourseNameSnapshot`, `examScore`, `passYn`, `participationYn`. (CHG-003)
- **[Pagination]** 페이지 사이즈/최대 조회 건수/정렬 파라미터 상세 포맷: `[NEEDS CLARIFICATION: TBD-001 — 기본값 및 최대 size 미확정. 임시 기본값: page=0, size=20 적용]`
- **[State]** 조회 결과 0건 시 '조회 결과가 없습니다.' 고정 메시지 표시. (KEEP-001)
- **[Calc]** 부서 표시 기준: 교육 당시 소속 부서 (`departmentNameSnapshot`). 현재 소속 부서 아님. (ADD-009)
- **[Calc]** 과정명 표시 기준: 교육 당시 과정명 (`trainingCourseNameSnapshot`). 과정 마스터의 현재 명칭 아님. (ADD-003)

---

## 5. API Specification

### [GET] /api/v1/edu-results (목록 조회)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/edu-results` |
| **Description** | 교육실적 목록 조회 (검색/정렬/페이징) |
| **Auth** | Required (ROLE_COMPLIANCE) |
| **Mockup 트리거** | 교육실적관리 > SearchForm > 조회 버튼 |

**Query Parameters**

| Name | Type | Required | Operator | Description |
| :--- | :--- | :--- | :--- | :--- |
| employeeNo | string | false | EQ | 사번 |
| employeeName | string | false | LIKE | 성명 (부분일치, 초성·공백·대소문자 무시) |
| departmentId | string | false | EQ | 부서 코드 (코드검색 선택값) |
| courseId | string | false | EQ | 교육과정 ID |
| courseCode | string | false | EQ | 교육과정 코드 |
| courseVersion | string | false | EQ | 교육과정 버전 |
| fromTrainingDateTime | datetime | false | GTE | 교육일시 시작 (포함) |
| toTrainingDateTime | datetime | false | LTE | 교육일시 종료 (포함) |
| participationYn | boolean | false | EQ | 참여여부 (Y/N) |
| passYn | boolean | false | EQ | 합격여부 (Y/N) |
| sort | string | false | - | 정렬 (예: `employeeNo,asc`) 다중 허용 |
| page | number | false | - | 페이지 번호 (default: 0) |
| size | number | false | - | 페이지 크기 (default: 20) `[NEEDS CLARIFICATION: TBD-001]` |

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": "uuid",
        "eduResultId": "string",
        "employeeNo": "string",
        "employeeName": "string",
        "departmentId": "string",
        "departmentNameSnapshot": "string",
        "courseId": "string",
        "courseCode": "string",
        "courseVersion": "string",
        "trainingCourseNameSnapshot": "string",
        "trainingDateTime": "2026-04-13T10:00:00",
        "participationYn": "Y",
        "examScore": 85,
        "passYn": "Y",
        "courseActiveYn": "Y"
      }
    ],
    "totalElements": 0,
    "totalPages": 0,
    "pageNumber": 0,
    "size": 20,
    "last": true
  },
  "message": "string"
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 401 | Unauthorized |
| 403 | Access denied — redirect to access-denied page |

---

### [GET] /api/v1/edu-results/{id} (단건 상세 조회)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/edu-results/{id}` |
| **Description** | 교육실적 단건 상세 조회 |
| **Auth** | Required (ROLE_COMPLIANCE) |
| **Mockup 트리거** | 교육실적관리 > DataTable 행 클릭 |

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "eduResultId": "string",
    "employeeNo": "string",
    "employeeName": "string",
    "departmentId": "string",
    "departmentNameSnapshot": "string",
    "courseId": "string",
    "courseCode": "string",
    "courseVersion": "string",
    "trainingCourseNameSnapshot": "string",
    "trainingDateTime": "2026-04-13T10:00:00",
    "participationYn": "Y",
    "examScore": 85,
    "passYn": "Y",
    "courseActiveYn": "Y"
  },
  "message": "string"
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 403 | Access denied |
| 404 | EduResult not found |

---

### [POST] /api/v1/edu-results/uploads/excel (엑셀 업로드 일괄등록)

| Item | Detail |
| :--- | :--- |
| **Method** | `POST` |
| **Path** | `/api/v1/edu-results/uploads/excel` |
| **Description** | 교육실적 엑셀 업로드 일괄등록 (검증·중복체크 포함) |
| **Auth** | Required (ROLE_COMPLIANCE) |
| **Mockup 트리거** | 교육실적관리 > 등록 버튼 `[MEETING OVERRIDE: 단건 등록 Dialog → 엑셀 업로드]` |
| **Content-Type** | `multipart/form-data` |

**Request (multipart/form-data)**

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| file | File | true | .xlsx 파일 |
| duplicatePolicy | string | false | `FAIL_ALL` / `SKIP_ROW` (default: `SKIP_ROW`) |

**엑셀 필수 컬럼**: `employeeNo`, `courseId` 또는 (`courseCode`+`courseVersion`), `trainingDateTime`, `participationYn`, `examScore`  
**엑셀 선택 컬럼**: `passYn`

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "acceptedCount": 10,
    "failedCount": 2,
    "failures": [
      {
        "rowNumber": 3,
        "employeeNo": "string",
        "courseId": "string",
        "errorCode": "DUPLICATE",
        "errorMessage": "string"
      }
    ]
  },
  "message": "string"
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 400 | Invalid file format or missing required columns |
| 403 | Access denied |
| 422 | All rows failed validation |

---

### [DELETE] /api/v1/edu-results (다건 물리삭제)

| Item | Detail |
| :--- | :--- |
| **Method** | `DELETE` |
| **Path** | `/api/v1/edu-results` |
| **Description** | 교육실적 체크박스 선택 다건 물리삭제. 활성 과정 건만 삭제 허용 `[MEETING OVERRIDE: 단건/논리삭제 → 다건 물리삭제]` |
| **Auth** | Required (ROLE_COMPLIANCE) |
| **Mockup 트리거** | 교육실적관리 > 체크박스 선택 > 삭제 버튼 > 확인 팝업 > 확인 |

**Request Body**
```json
{
  "ids": ["uuid1", "uuid2"]
}
```

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "deletedCount": 2
  },
  "message": "string"
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 400 | ids must not be empty |
| 403 | Access denied |
| 422 | Cannot delete: linked course is inactive (courseActiveYn=N) |

---

### [GET] /api/v1/edu-results/export (엑셀 다운로드)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/edu-results/export` |
| **Description** | 현재 검색 조건 기반 교육실적 엑셀 다운로드 |
| **Auth** | Required (ROLE_COMPLIANCE) |
| **Mockup 트리거** | 교육실적관리 > 엑셀 다운로드 버튼 |

**Query Parameters**: 목록 조회(GET /api/v1/edu-results)의 검색 파라미터와 동일 (page/size 제외)

**Response**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (파일 다운로드)

**Errors**

| Status | Message |
| :--- | :--- |
| 403 | Access denied |
| 500 | Excel generation failed — display error message to user |

---

### [GET] /api/v1/courses (교육과정 마스터 조회)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/courses` |
| **Description** | 교육과정 코드검색 (과정코드·버전·활성여부 포함) |
| **Auth** | Required |
| **Mockup 트리거** | 엑셀 업로드 검증 / 삭제 조건 판단 |

**Query Parameters**

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| courseCode | string | false | 과정 코드 (부분일치) |
| courseName | string | false | 과정명 (부분일치) |
| activeYn | boolean | false | 활성여부 필터 |
| page | number | false | - |
| size | number | false | - |

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": "uuid",
        "courseCode": "string",
        "courseVersion": "string",
        "courseName": "string",
        "activeYn": "Y"
      }
    ],
    "totalElements": 0,
    "totalPages": 0,
    "pageNumber": 0,
    "size": 20,
    "last": true
  },
  "message": "string"
}
```

---

### [GET] /api/v1/departments (부서 코드검색)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/departments` |
| **Description** | 부서 코드검색 (목록 검색 필터 선택용) `[MEETING OVERRIDE: 텍스트 직접 입력 → 코드검색 선택]` |
| **Auth** | Required |
| **Mockup 트리거** | 교육실적관리 > SearchForm > 부서 코드검색 |

**Query Parameters**

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| keyword | string | false | 부서명 부분일치 |
| page | number | false | - |
| size | number | false | - |

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "content": [
      {
        "departmentId": "string",
        "departmentName": "string"
      }
    ],
    "totalElements": 0,
    "totalPages": 0
  },
  "message": "string"
}
```

---

### [GET] /api/v1/employees (사원 코드검색)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/employees` |
| **Description** | 사원 코드검색 (성명 부분일치 + 초성·공백·대소문자 무시) `[MEETING OVERRIDE: 텍스트 직접 입력 → 코드검색 선택]` |
| **Auth** | Required |
| **Mockup 트리거** | 교육실적관리 > SearchForm > 성명 코드검색 |

**Query Parameters**

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| keyword | string | false | 성명 또는 사번 검색 (LIKE + 초성/공백/대소문자 무시) |
| employeeNo | string | false | 사번 완전일치 |
| page | number | false | - |
| size | number | false | - |

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "content": [
      {
        "employeeNo": "string",
        "employeeName": "string",
        "departmentId": "string",
        "departmentName": "string"
      }
    ],
    "totalElements": 0,
    "totalPages": 0
  },
  "message": "string"
}
```

---

## 6. UI/UX Flow (Mockup ↔ API 매핑)

### Flow: 교육실적 조회

| Step | User Action | Mockup 화면 | UI 컴포넌트 | API | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 성명 코드검색 | 교육실적관리 | SearchForm > 성명 검색 팝업 | `GET /api/v1/employees` | - |
| 2 | 부서 코드검색 | 교육실적관리 | SearchForm > 부서 검색 팝업 | `GET /api/v1/departments` | - |
| 3 | 교육일자 from/to 입력 후 조회 | 교육실적관리 | SearchForm > 조회 버튼 | `GET /api/v1/edu-results` | - |
| 4 | 초기화 클릭 | 교육실적관리 | SearchForm > 초기화 버튼 | (클라이언트 초기화, API 없음) | - |

### Flow: 교육실적 엑셀 업로드 등록

| Step | User Action | Mockup 화면 | UI 컴포넌트 | API | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 등록 버튼 클릭 | 교육실적관리 | 상단 등록 버튼 | - | 파일 선택 Dialog 오픈 |
| 2 | .xlsx 파일 선택 및 업로드 | 교육실적관리 | 파일 업로드 Dialog | `POST /api/v1/edu-results/uploads/excel` | - → 업로드 완료/부분실패 |
| 3 | 업로드 결과 확인 | 교육실적관리 | 업로드 결과 리포트 | - | - |
| 4 | 목록 새로고침 | 교육실적관리 | 조회 | `GET /api/v1/edu-results` | - |

### Flow: 교육실적 다건 삭제

| Step | User Action | Mockup 화면 | UI 컴포넌트 | API | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 체크박스 선택 (1건 이상) | 교육실적관리 | DataTable 체크박스 | - | - |
| 2 | 삭제 버튼 클릭 | 교육실적관리 | 상단 삭제 버튼 | - | 확인 팝업 표시 |
| 3 | 확인 팝업 > 확인 클릭 | 교육실적관리 | 삭제 확인 Dialog | `DELETE /api/v1/edu-results` | 물리 삭제 완료 |
| 4 | 목록 새로고침 | 교육실적관리 | 조회 | `GET /api/v1/edu-results` | - |

### Flow: 엑셀 다운로드

| Step | User Action | Mockup 화면 | UI 컴포넌트 | API | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 엑셀 다운로드 버튼 클릭 | 교육실적관리 | 상단 엑셀 다운로드 버튼 | `GET /api/v1/edu-results/export` | 파일 다운로드 / 실패 시 안내 문구 표시 |

---

# AI_HINT

- Framework: Spring Boot 3.x (Java 21)
- Language Features: Use Java Records for DTOs
- Layered Architecture (Controller-Service-Repository)
- DTO / Entity separation (MapStruct or Manual Mapping)
- Validation: Jakarta Bean Validation (@Valid)
- Persistence: Spring Data JPA + Querydsl (for dynamic queries)
- REST Level 2+

## 삭제 정책 (Hard Delete)

- 이 화면은 물리삭제(hard delete)를 사용한다. `deletedAt` 컬럼 불필요.
- 삭제 전 서비스 레이어에서 `courseActiveYn` 검증 필수.

## 검색 확장 (초성/공백/대소문자 무시)

- 성명(employeeName) 검색은 일반 LIKE 외 초성 검색 지원 필요.
- DB 함수 또는 별도 검색 인덱스(예: Full-Text Search) 구현 고려.
- `[NEEDS CLARIFICATION: 초성 검색 구현 방식 — DB 함수 vs 검색 엔진(Elasticsearch 등)]`

## 엑셀 업로드

- `multipart/form-data` 처리: `@RequestPart MultipartFile file`
- 업로드 결과는 성공 건수 + 실패 건수 + 실패 리포트(행번호/사유) 포함
- 부분 실패 정책(`duplicatePolicy`): `SKIP_ROW`(해당 행만 실패) 또는 `FAIL_ALL`(전체 롤백) 선택 가능

## Transaction Management

- `@Transactional` on Service layer
- `readOnly = true` for GET operations

## Error Handling

- Consistent response format
- Centralized exception handling (`@RestControllerAdvice`)
- 403: 접근 차단 페이지 리다이렉트 (프론트 처리)
- 5xx / Network Error: 오류 페이지 이동 (프론트 처리)
- 엑셀 다운로드 실패: 안내 문구 표시 (프론트 처리)

## API Documentation

- Use Swagger / OpenAPI 3 annotations

---

## ⚠️ NEEDS CLARIFICATION 요약

| # | 항목 | 내용 |
| :--- | :--- | :--- |
| 1 | TBD-001 | 페이징 기본값(page size), 최대 size, 다중 sort 파라미터 포맷 미확정 |
| 2 | - | 초성 검색 구현 방식 (DB 함수 vs 검색 엔진) |
| 3 | - | 엑셀 다운로드 최대 다운로드 건수 제한 및 비동기 생성(대용량) 여부 |
| 4 | - | 중복 등록 차단 시 기본 정책 (`FAIL_ALL` vs `SKIP_ROW`) 확정 필요 |
