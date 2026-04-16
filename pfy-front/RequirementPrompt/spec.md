# 📄 윤리경영시스템 — 부정제보 신고 관리 Technical Specification (spec.md)

> **Source Priority**: `interviewNotes.md` > `EthicsReportMockup.vue` > `screen_brief.md`
> **Generated**: 2026-04-06 | **참조 Mockup**: `mockup/EthicsReportMockup.vue`

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
- **Source Priority**: `interviewNotes.md` > `Mockup.vue` > `screen_brief.md`

---

## 1. Requirement Refinement

### Functional

- **[F-01]** 부정제보 신고 목록 조회 — 신고유형 / 처리상태 / 신고일 범위 / 신고자(userId 기준) 조건 검색
- **[F-02]** 부정제보 신고 등록 — 신고유형, 제목, 내용, 첨부파일 입력
- **[F-03]** 부정제보 신고 상세 조회 — 신고 내용 + 처리 이력 확인
- **[F-04]** 부정제보 신고 처리 — 처리상태 변경, 담당자 지정, 처리내용 입력 (ADMIN 전용)
- **[F-05]** 부정제보 신고 삭제 — Soft Delete (ADMIN 전용)
- **[F-06]** 처리완료 액션 — `IN_PROGRESS` 상태에서만 활성화, 클릭 시 `COMPLETED`로 전이
- **[F-07]** 엑셀 다운로드 — 현재 검색 조건 기준 전체 결과 다운로드 (항상 노출, ADMIN 전용)
- **[F-08]** 신고자 이름 → userId 조회 API — 이름 입력 시 매핑된 userId 반환, 목록 조회 파라미터로 사용

### Non-Functional

- **Performance**: API response time < 300ms (목록 조회 포함)
- **Security**: JWT 기반 인증 + RBAC (`ROLE_ADMIN` 만 접근 허용)
- **Scalability**: Stateless architecture (수평 확장 가능)
- **File**: 첨부파일 최대 5개 / 개당 10MB 이하

### Constraints

- **Tech Stack**: Spring Boot 3.x, Java 21, JPA, Querydsl
- **Auth**: Spring Security + JWT (`ROLE_ADMIN` 권한 체크)
- **Excel**: Apache POI 또는 EasyExcel
- **File Storage**: [NEEDS CLARIFICATION: S3 vs 내부 파일서버]
- **External Integration**: 사용자 정보 조회 (이름 → userId 매핑) — 자체 User 테이블 vs HR 연동 [NEEDS CLARIFICATION]

---

## 2. Atomic User Stories

- **US-01**: As an **ADMIN**, I want to **search ethics reports by type, status, date range, and reporter name**, so that I can quickly find specific cases.
- **US-02**: As an **ADMIN**, I want to **register a new ethics report**, so that I can document whistleblowing cases.
- **US-03**: As an **ADMIN**, I want to **view the full detail of a report**, so that I can review the content and processing history.
- **US-04**: As an **ADMIN**, I want to **update the processing status and write processing content**, so that I can manage the case progress.
- **US-05**: As an **ADMIN**, I want to **mark a report as COMPLETED when it is IN_PROGRESS**, so that I can close resolved cases.
- **US-06**: As an **ADMIN**, I want to **delete a report (soft delete)**, so that I can remove invalid or duplicate submissions.
- **US-07**: As an **ADMIN**, I want to **download search results as Excel**, so that I can analyze or report the data offline.
- **US-08**: As an **ADMIN**, I want to **search a reporter by name and get their userId**, so that I can use the correct system identifier for filtering.
- **US-09**: As a **USER**, I want to **see an access-denied message when I try to enter this screen**, so that unauthorized access is clearly communicated.

---

## 3. Domain Modeling (Core)

### Entity: EthicsReport (Table: `ethics_report`)

| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | UUID | uuid | false | PK | - | Primary Key |
| reportNo | String | String | varchar(20) | false | UNIQUE | @NotBlank | 신고번호 (RPT-YYYY-NNNN, 자동생성) |
| reportType | Enum | ReportType | varchar(20) | false | - | @NotNull | 신고유형 |
| title | String | String | varchar(200) | false | - | @NotBlank, @Size(max=200) | 제목 |
| content | Text | String | text | false | - | @NotBlank | 신고 내용 |
| reporterId | UUID | UUID | uuid | false | FK → users.id | @NotNull | 신고자 ID |
| reporterNm | String | String | varchar(50) | false | - | @NotBlank | 신고자 이름 (비정규화) |
| reporterUserId | String | String | varchar(50) | false | - | @NotBlank | 신고자 시스템 userId |
| reportDt | Date | LocalDate | date | false | - | - | 신고일 (등록일 자동 설정) |
| status | Enum | ReportStatus | varchar(20) | false | - | @NotNull | 처리상태 |
| processorId | UUID | UUID | uuid | true | FK → users.id | - | 담당자 ID |
| processorNm | String | String | varchar(50) | true | - | - | 담당자 이름 |
| processContent | Text | String | text | true | - | - | 처리내용 |
| createdAt | DateTime | LocalDateTime | timestamp | false | - | - | 생성일 |
| updatedAt | DateTime | LocalDateTime | timestamp | false | - | - | 수정일 |
| deletedAt | DateTime | LocalDateTime | timestamp | true | - | - | 삭제일 (Soft Delete) |

### Entity: EthicsReportAttachment (Table: `ethics_report_attachment`)

| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | UUID | uuid | false | PK | - | Primary Key |
| reportId | UUID | UUID | uuid | false | FK → ethics_report.id | @NotNull | 신고 ID |
| originalFileName | String | String | varchar(255) | false | - | @NotBlank | 원본 파일명 |
| storedFileName | String | String | varchar(255) | false | - | @NotBlank | 저장 파일명 |
| fileSize | Long | Long | bigint | false | - | @Min(1) | 파일 크기 (bytes) |
| fileUrl | String | String | varchar(500) | false | - | @NotBlank | 파일 접근 URL |
| createdAt | DateTime | LocalDateTime | timestamp | false | - | - | 생성일 |
| deletedAt | DateTime | LocalDateTime | timestamp | true | - | - | 삭제일 (Soft Delete) |

### Relationships

- **EthicsReport (1:N) EthicsReportAttachment**
  - FK: `report_id` (in EthicsReportAttachment)
  - Owner: `EthicsReportAttachment`
  - Mapping: `@OneToMany(mappedBy = "report")` / `@ManyToOne` (FetchType.LAZY)

### Enums

- **ReportType**: `CORRUPTION`, `HARASSMENT`, `FRAUD`, `ETC`
  - Mockup 출처: `EthicsReportMockup.vue` > `reportType` 더미 데이터 상태값

- **ReportStatus**: `RECEIVED`, `IN_PROGRESS`, `COMPLETED`, `REJECTED`
  - Mockup 출처: `EthicsReportMockup.vue` > `status` DotStatusText 상태값
  - 상태 전이: `RECEIVED` → `IN_PROGRESS` → `COMPLETED` / `REJECTED`

---

## 4. Business Logic Rules

- **[Validation-01]**: `title` 최대 200자, `content` 필수 입력
- **[Validation-02]**: 첨부파일 최대 5개 / 개당 10MB 이하. 초과 시 400 반환
- **[Validation-03]**: `reportNo`는 서버에서 자동 생성 (`RPT-{YYYY}-{0001 ~ 9999}`, 연도별 시퀀스)
- **[State-01]**: 상태 전이 규칙
  - `RECEIVED` → `IN_PROGRESS` (처리 시작)
  - `IN_PROGRESS` → `COMPLETED` (처리완료 액션)
  - `IN_PROGRESS` → `REJECTED` (반려 처리)
  - 역방향 전이 불가 (`COMPLETED` / `REJECTED` → 이전 상태 변경 금지)
- **[State-02]**: `처리완료` 버튼은 `status === IN_PROGRESS` 일 때만 활성화
  - `[MEETING OVERRIDE: Mockup에서 ADMIN 조건 없이 항상 표시 → 상태 조건 추가]`
- **[Auth-01]**: 전체 API `ROLE_ADMIN` 권한 필수. `ROLE_USER` 접근 시 403 반환
  - `[MEETING OVERRIDE: Mockup에서 ADMIN/USER 모두 접근 → ADMIN 전용으로 확정]`
- **[Auth-02]**: 엑셀 다운로드 API — `ROLE_ADMIN` 전용, 항상 노출
  - `[MEETING OVERRIDE: Mockup에서 조건부 노출 → 항상 노출로 확정]`
- **[Search-01]**: 신고자 검색 — UI에서 이름 입력, API 파라미터는 `reporterUserId` (userId 기준 조회)
  - `[MEETING OVERRIDE: Mockup에 신고자 검색 없음 → 이름 입력/userId 매핑 조회로 추가]`
- **[Search-02]**: 키워드(제목·내용) 검색 필드 **제외**
  - `[MEETING OVERRIDE: Mockup의 키워드 검색 필드 → 제거]`
- **[Calc-01]**: 목록 조회 시 `deletedAt IS NULL` 조건 필수 (Soft Delete 적용)

---

## 5. API Specification

### [GET] /api/v1/ethics-reports (목록 조회)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/ethics-reports` |
| **Description** | 부정제보 신고 목록 조회 (검색 조건 + 페이징) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > SearchForm > 조회 버튼 클릭 |

**Query Parameters**

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| reportType | string | false | 신고유형 (`CORRUPTION`, `HARASSMENT`, `FRAUD`, `ETC`) |
| reportStatus | string | false | 처리상태 (`RECEIVED`, `IN_PROGRESS`, `COMPLETED`, `REJECTED`) |
| reportDtFrom | string | false | 신고일 시작 (yyyy-MM-dd) |
| reportDtTo | string | false | 신고일 종료 (yyyy-MM-dd) |
| reporterUserId | string | false | 신고자 userId (이름→userId 변환 후 전송) |
| page | number | false | 페이지 번호 (default: 0) |
| size | number | false | 페이지 크기 (default: 20) |
| sort | string | false | 정렬 (e.g., `reportDt,desc`) |

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": "uuid",
        "reportNo": "RPT-2025-0001",
        "reportType": "CORRUPTION",
        "title": "부서장의 금품 수수 의혹",
        "reporterNm": "홍길동",
        "reporterUserId": "hong001",
        "reportDt": "2025-03-15",
        "status": "IN_PROGRESS",
        "processorNm": "김윤리"
      }
    ],
    "totalElements": 5,
    "totalPages": 1,
    "pageNumber": 0,
    "size": 20,
    "last": true
  },
  "message": "success"
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 401 | Unauthorized |
| 403 | Forbidden — ADMIN 권한 필요 |

---

### [POST] /api/v1/ethics-reports (신고 등록)

| Item | Detail |
| :--- | :--- |
| **Method** | `POST` |
| **Path** | `/api/v1/ethics-reports` |
| **Description** | 부정제보 신고 등록 (`reportNo` 서버 자동생성) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > 신규 버튼 > 등록 Dialog > 저장 버튼 |

**Request Body** (`multipart/form-data`)
```json
{
  "reportType": "CORRUPTION",
  "title": "부서장의 금품 수수 의혹",
  "content": "2025년 2월부터 ...",
  "reporterUserId": "hong001",
  "attachFiles": ["(binary)"]
}
```

**Response (201 Created)**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "reportNo": "RPT-2025-0006"
  },
  "message": "신고가 접수되었습니다."
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 400 | Invalid input (필수값 누락, 파일 크기/개수 초과) |
| 401 | Unauthorized |
| 403 | Forbidden |

---

### [GET] /api/v1/ethics-reports/{id} (단건 상세 조회)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/ethics-reports/{id}` |
| **Description** | 부정제보 신고 상세 조회 (첨부파일 목록 포함) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > DataTable 행 더블클릭 |

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "reportNo": "RPT-2025-0001",
    "reportType": "CORRUPTION",
    "title": "부서장의 금품 수수 의혹",
    "content": "2025년 2월부터 ...",
    "reporterNm": "홍길동",
    "reporterUserId": "hong001",
    "reportDt": "2025-03-15",
    "status": "IN_PROGRESS",
    "processorNm": "김윤리",
    "processContent": "면담 진행 예정",
    "attachments": [
      {
        "id": "uuid",
        "originalFileName": "증거자료.pdf",
        "fileUrl": "/files/stored-name.pdf",
        "fileSize": 204800
      }
    ],
    "createdAt": "2025-03-15T09:00:00",
    "updatedAt": "2025-03-20T14:30:00"
  },
  "message": "success"
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 403 | Forbidden |
| 404 | 신고 정보를 찾을 수 없습니다. |

---

### [PUT] /api/v1/ethics-reports/{id} (신고 처리 수정)

| Item | Detail |
| :--- | :--- |
| **Method** | `PUT` |
| **Path** | `/api/v1/ethics-reports/{id}` |
| **Description** | 신고 처리 정보 수정 (처리상태, 담당자, 처리내용, 첨부파일 추가) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > 상세 Dialog > 저장 버튼 |

**Request Body**
```json
{
  "reportType": "CORRUPTION",
  "title": "부서장의 금품 수수 의혹 (수정)",
  "content": "추가 내용...",
  "status": "IN_PROGRESS",
  "processorNm": "김윤리",
  "processContent": "면담 완료. 추가 조사 진행 중."
}
```

**Response (200 OK)**
```json
{
  "success": true,
  "data": { "id": "uuid" },
  "message": "저장되었습니다."
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 400 | Invalid input / 상태 전이 불가 |
| 403 | Forbidden |
| 404 | 신고 정보를 찾을 수 없습니다. |

---

### [POST] /api/v1/ethics-reports/{id}/complete (처리완료)

| Item | Detail |
| :--- | :--- |
| **Method** | `POST` |
| **Path** | `/api/v1/ethics-reports/{id}/complete` |
| **Description** | `IN_PROGRESS` → `COMPLETED` 상태 전이 (처리완료 액션) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > 상세 Dialog > 처리완료 버튼 (status=IN_PROGRESS 일 때만 노출) |

**Request Body**
```json
{
  "processContent": "조사 완료. 징계위원회 회부."
}
```

**Response (200 OK)**
```json
{
  "success": true,
  "data": { "id": "uuid", "status": "COMPLETED" },
  "message": "처리완료 처리되었습니다."
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 400 | 처리완료는 처리중(IN_PROGRESS) 상태에서만 가능합니다. |
| 403 | Forbidden |
| 404 | 신고 정보를 찾을 수 없습니다. |

---

### [DELETE] /api/v1/ethics-reports/{id} (삭제)

| Item | Detail |
| :--- | :--- |
| **Method** | `DELETE` |
| **Path** | `/api/v1/ethics-reports/{id}` |
| **Description** | 부정제보 신고 삭제 — Soft Delete (`deletedAt` 갱신) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > 상세 Dialog > 삭제 버튼 > 확인 |

**Response (200 OK)**
```json
{
  "success": true,
  "data": null,
  "message": "삭제되었습니다."
}
```

**Errors**

| Status | Message |
| :--- | :--- |
| 403 | Forbidden |
| 404 | 신고 정보를 찾을 수 없습니다. |

---

### [GET] /api/v1/ethics-reports/excel (엑셀 다운로드)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/ethics-reports/excel` |
| **Description** | 현재 검색 조건 기준 전체 결과 엑셀 다운로드 (페이징 없음) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > 엑셀 다운로드 버튼 (항상 노출) |

**Query Parameters** — 목록 조회와 동일 (`reportType`, `reportStatus`, `reportDtFrom`, `reportDtTo`, `reporterUserId`)

**Response**: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (binary)

> 다운로드 파일명: `부정제보신고관리_YYYYMMDD.xlsx`
> 컬럼 범위: [NEEDS CLARIFICATION: 전체 컬럼 vs 선택 컬럼 — 다음 회의 확인]

**Errors**

| Status | Message |
| :--- | :--- |
| 403 | Forbidden |

---

### [GET] /api/v1/users/search (사용자 이름 → userId 조회)

| Item | Detail |
| :--- | :--- |
| **Method** | `GET` |
| **Path** | `/api/v1/users/search` |
| **Description** | 신고자 이름으로 사용자 목록 조회 → userId 반환 (신고자 검색 필드 자동완성용) |
| **Auth** | Required — `ROLE_ADMIN` |
| **Mockup 트리거** | 부정제보 신고 관리 > SearchForm > 신고자 이름 입력 (onChange) |

**Query Parameters**

| Name | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| name | string | true | 신고자 이름 (부분 일치 검색) |

**Response (200 OK)**
```json
{
  "success": true,
  "data": [
    { "userId": "hong001", "userNm": "홍길동", "deptNm": "기획팀" }
  ],
  "message": "success"
}
```

> 매핑 방식 확정 필요: [NEEDS CLARIFICATION: 팝업 검색 vs 직접 입력 자동완성 — 다음 회의 확인]

**Errors**

| Status | Message |
| :--- | :--- |
| 400 | name 파라미터 필수 |
| 403 | Forbidden |

---

## 6. UI/UX Flow (Mockup ↔ API 매핑)

### Flow: 부정제보 신고 관리 — 전체 흐름

| Step | User Action | Mockup 화면 | UI 컴포넌트 | API | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 화면 진입 | 부정제보 신고 관리 | 접근 권한 체크 | — | 403 → 접근불가 화면 표시 (USER) |
| 2 | 신고자 이름 입력 | SearchForm | 신고자 Input (onChange) | `GET /api/v1/users/search?name=홍길동` | — |
| 3 | 조회 버튼 클릭 | SearchForm | 조회 Button | `GET /api/v1/ethics-reports?reporterUserId=hong001&...` | — |
| 4 | 행 더블클릭 | DataTable | 행 dblclick | `GET /api/v1/ethics-reports/{id}` | — |
| 5 | 저장 버튼 클릭 (수정) | 상세 Dialog | 저장 Button | `PUT /api/v1/ethics-reports/{id}` | 상태 변경 |
| 6 | 처리완료 버튼 클릭 | 상세 Dialog | 처리완료 Button (IN_PROGRESS만 노출) | `POST /api/v1/ethics-reports/{id}/complete` | IN_PROGRESS → COMPLETED |
| 7 | 삭제 버튼 클릭 | 상세 Dialog | 삭제 Button → confirm | `DELETE /api/v1/ethics-reports/{id}` | → Soft Delete |
| 8 | 신규 버튼 클릭 | DataTable Header | 신규 Button | — (Dialog 오픈) | — |
| 9 | 신규 저장 버튼 클릭 | 등록 Dialog | 저장 Button | `POST /api/v1/ethics-reports` | → RECEIVED |
| 10 | 엑셀 다운로드 클릭 | DataTable Header | 엑셀 다운로드 Button (항상 노출) | `GET /api/v1/ethics-reports/excel` | — |

---

## 7. TBD (미결 사항)

| # | 항목 | 현재 가정 | 확인 필요 |
| :--- | :--- | :--- | :--- |
| TBD-01 | 신고자 이름 → userId 매핑 방식 | Input onChange 자동완성 (userId 뱃지 표시) | 팝업 검색 vs 자동완성 — 다음 회의 |
| TBD-02 | 엑셀 다운로드 컬럼 범위 | 전체 컬럼 다운로드 | 전체 vs 선택 컬럼 — 다음 회의 |
| TBD-03 | 첨부파일 저장소 | [NEEDS CLARIFICATION] | S3 vs 내부 파일서버 |
| TBD-04 | 사용자 정보 조회 출처 | 자체 User 테이블 | 자체 DB vs HR 시스템 연동 |

---

## AI_HINT

- **Framework**: Spring Boot 3.x (Java 21)
- **Language Features**: Java Records for DTOs
- **Layered Architecture**: Controller → Service → Repository
- **DTO / Entity**: 분리 (MapStruct 권장)
- **Validation**: Jakarta Bean Validation (`@Valid`)
- **Persistence**: Spring Data JPA + Querydsl (동적 검색 쿼리)
- **File Upload**: `multipart/form-data`, Apache POI (Excel)
- **REST Level 2+**

### Soft Delete
- `deletedAt` nullable
- 모든 Repository 쿼리에 `deletedAt IS NULL` 조건 (`@SQLRestriction` — Hibernate 6.x)
- Delete API는 `deletedAt` 갱신 (물리 삭제 금지)

### Transaction Management
- `@Transactional` — Service layer
- `readOnly = true` — GET 전용

### Security
- Spring Security + JWT
- `@PreAuthorize("hasRole('ADMIN')")` — 전체 Controller 메서드 적용
- `ROLE_USER` 접근 시 **403 Forbidden** 반환

### Error Handling
- 일관된 Response 포맷 (`{ success, data, message }`)
- 중앙화 예외 처리 (`@RestControllerAdvice`)

### API Documentation
- Swagger / OpenAPI 3 (`springdoc-openapi`)
