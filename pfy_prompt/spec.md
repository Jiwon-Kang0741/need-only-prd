# 📄 교육 프로그램 실적 조회 Technical Specification (spec.md)

## 0. Global Rules (Strict)

### Primary Key Strategy
- UUID (String, varchar(36)) — Default

### Naming Convention (CPMS 표준)
- **화면명**: `[LV1메뉴][LV2메뉴][행위][역할Suffix]` (예: `CpmsEduPgrRsltLst`)
  - Suffix: 목록/현황=`Lst`, 등록/수정=`Edit`, 조회팝업=`SPopup`, CRUD팝업=`EPopup`
- **Entities**: PascalCase
- **Fields/Query Parameters**: camelCase
- **Database Tables**: snake_case (접두어 `CPTB_` 사용, 예: `CPTB_EDU_PROG_RSLT`)
- **Backend Classes**: `화면명Dao`, `화면명DaoImpl`, `화면명Service`, `화면명ServiceImpl`, `화면명Mapper`, `화면명ReqDto`, `화면명ResDto`
- **Service Methods**: `search` (조회), `save` (등록/수정/삭제 통합)
- **Mapper Methods**: `select`, `insert`, `update`, `delete`

### API URL Convention (CPMS 표준)
- **Pattern**: `POST /online/mvcJson/{화면코드}-{메서드명}`
- **Backend @ServiceId**: `@ServiceId("{화면코드}/{메서드명}")`
- **매핑 예시**:
  - `@ServiceId("CPMSEDUPGRRSLTLST/search")` → `POST /online/mvcJson/CPMSEDUPGRRSLTLST-search`
  - `@ServiceId("CPMSEDUPGRRSLTLST/save")` → `POST /online/mvcJson/CPMSEDUPGRRSLTLST-save`

### Architecture Rules
- All Business Logic **MUST** be implemented in **Service Layer**.
- Controllers **MUST** be thin (no business logic, only routing & validation).
- Soft Delete **MUST** be applied using `deletedAt` field.
- `@ServiceId`, `@ServiceName` annotation은 모든 public Service 메서드에 필수.

---

## 1. Requirement Refinement

### Functional
- **교육 실적 조회**: 교육 프로그램 실적 현황 목록 조회 기능.
- **엑셀 업로드**: 교육 실적 데이터를 엑셀 파일을 통해 일괄 등록.
- **사용자 자동 매핑**: 입력된 사용자 ID를 기반으로 성명 및 부서 정보 자동 조회.
- **중복 검증**: 저장 시 기존 데이터와의 중복 여부 확인.

### Non-Functional
- **Performance**: API response time < 300ms (단, 대용량 엑셀 업로드 제외).
- **Security**: JWT based Authentication & RBAC (Role-Based Access Control).
- **Scalability**: Stateless architecture for horizontal scaling.

### Constraints
- **Tech Stack**: Spring Boot, Java, MyBatis, Vue3, PrimeVue.
- **External Integration**: [ASSUMED: 인사 시스템 API 또는 DB (사용자 정보 조회용)], Apache POI (Excel Library).

---

## 2. Atomic User Stories
- **US-01**: As an Admin, I want to upload an Excel file, so that I can register multiple education records at once.
- **US-02**: As an Admin, I want the system to automatically fetch user names and departments by ID, so that I don't have to enter them manually.
- **US-03**: As an Admin, I want the system to check for duplicate records, so that data integrity is maintained.
- **US-04**: As a User/Admin, I want to view the compliance education status, so that I can monitor the training progress.

---

## 3. Domain Modeling (Core)

### Entity: EduPgrRslt (Table: `CPTB_EDU_PGR_RSLT`)
| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | String | varchar(36) | false | PK | - | Primary Key |
| userId | String | String | varchar(50) | false | - | @NotBlank | 사용자 사번/ID |
| userName | String | String | varchar(100) | false | - | - | [ASSUMED: 매핑된 이름] |
| departmentName | String | String | varchar(100) | false | - | - | [ASSUMED: 매핑된 부서] |
| educationTitle | String | String | varchar(255) | false | - | @NotBlank | 교육명 |
| completionDate | DateTime | LocalDateTime | timestamp | false | - | @NotNull | 수료일 |
| createdAt | DateTime | LocalDateTime | timestamp | false | - | - | 생성일 |
| updatedAt | DateTime | LocalDateTime | timestamp | false | - | - | 수정일 |
| deletedAt | DateTime | LocalDateTime | timestamp | true | - | - | 삭제일 (Soft Delete) |

### Relationships
- [NEEDS CLARIFICATION: User 엔티티와의 직접 연관관계 여부. 현재는 ID 기반 자동 매핑 요구사항에 따라 비정규화 또는 조회 기반으로 설계함.]

### Enums
- [NEEDS CLARIFICATION: 교육 유형이나 합격 여부(P/F) 등에 대한 정의가 필요한 경우 추가.]

---

## 4. Business Logic Rules
- **[Validation]**: 동일 사용자(`userId`), 동일 교육(`educationTitle`), 동일 수료일(`completionDate`)인 데이터가 존재할 경우 중복으로 간주하고 저장을 거부함.
- **[Auth]**: 엑셀 업로드 및 수정/삭제 권한은 특정 Role(예: ADMIN)에게만 부여함.
- **[Calc]**: 엑셀 업로드 시 각 로우의 `userId`를 사용하여 외부 인사 정보 시스템에서 이름과 부서를 조회한 뒤 엔티티 필드를 채움.

---

## 5. API Specification

### [POST] /online/mvcJson/CPMSEDUPGRRSLTLST-search

| Item | Detail |
| :--- | :--- |
| **Method** | `POST` |
| **Path** | `/online/mvcJson/CPMSEDUPGRRSLTLST-search` |
| **@ServiceId** | `CPMSEDUPGRRSLTLST/search` |
| **@ServiceName** | `교육 실적 현황 목록 조회` |
| **Description** | 교육 실적 현황 목록 조회 (Pagination & Filter) |
| **Auth** | Required |
| **Mockup 트리거** | 실적 관리 페이지 > SearchForm > 조회 버튼 |

**Request Body**
```json
{
  "userId": "string",
  "userName": "string",
  "completionDateFrom": "2024-01-01",
  "completionDateTo": "2024-12-31",
  "pageIndex": 1,
  "pageSize": 20
}
```

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "list": [
      {
        "id": "uuid",
        "userId": "STR001",
        "userName": "홍길동",
        "departmentName": "준법지원팀",
        "educationTitle": "윤리경영 교육",
        "completionDate": "2024-03-31"
      }
    ],
    "totalCount": 1,
    "pageIndex": 1,
    "pageSize": 20
  },
  "message": "조회 성공"
}
```

**Errors**
| Status | Message | Description |
| :--- | :--- | :--- |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | 권한 없음 |
| 500 | Internal Server Error | 서버 오류 |

---

### [POST] /online/mvcJson/CPMSEDUPGRRSLTLST-save

| Item | Detail |
| :--- | :--- |
| **Method** | `POST` |
| **Path** | `/online/mvcJson/CPMSEDUPGRRSLTLST-save` |
| **@ServiceId** | `CPMSEDUPGRRSLTLST/save` |
| **@ServiceName** | `교육 실적 엑셀 업로드 저장` |
| **Description** | 엑셀 파일을 업로드하여 교육 실적을 일괄 등록함 |
| **Auth** | Required (Admin) |
| **Mockup 트리거** | 실적 관리 페이지 > Upload Modal > 업로드 버튼 |

**Request Body**
- `multipart/form-data` (file: MultipartFile)

**Response (200 OK)**
```json
{
  "success": true,
  "data": { "processedCount": 100 },
  "message": "저장되었습니다."
}
```

**Errors**
| Status | Message | Description |
| :--- | :--- | :--- |
| 400 | Bad Request | 중복 데이터 또는 유효하지 않은 입력값 |
| 401 | Unauthorized | 인증 실패 |
| 403 | Forbidden | Admin 권한 필요 |
| 500 | Internal Server Error | 서버 오류 |

---

### Error Codes (공통)
| Status Code | Message | Description |
| :--- | :--- | :--- |
| **401** | `Unauthorized` | 유효한 인증 정보가 없거나 인증에 실패함 |
| **403** | `Forbidden` | 요청한 리소스에 접근할 권한이 없음 |
| **404** | `Not Found` | 요청한 리소스를 찾을 수 없음 |
| **400** | `Bad Request` | 중복 데이터 존재 또는 입력값이 유효하지 않음 |
| **500** | `Internal Server Error` | 서버 내부 로직 처리 중 예기치 못한 오류 발생 |

---

## 6. UI/UX Flow (Mockup ↔ API 매핑)

### Flow: 교육 실적 일괄 등록 및 확인

| Step | User Action | Mockup 화면 | UI 컴포넌트 | API | Method | Path |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 엑셀 파일 선택 및 업로드 버튼 클릭 | 실적 관리 페이지 | Upload Modal / Button | 일괄 등록 | POST | `/online/mvcJson/CPMSEDUPGRRSLTLST-save` |
| 2 | 업로드 결과 메시지 확인 | 실적 관리 페이지 | Toast Message | - | - | - |
| 3 | 목록 필터링 및 조회 | 실적 관리 페이지 | SearchForm / DataTable | 목록 조회 | POST | `/online/mvcJson/CPMSEDUPGRRSLTLST-search` |

---

# AI_HINT
- **Framework**: Spring Boot + MyBatis (Mapper XML)
- **Validation**: `CpmsEduPgrRsltLstServiceImpl`에서 저장 전 중복 체크 로직 구현.
- **Excel**: Apache POI 사용 시 `SXSSF`를 활용한 메모리 최적화 권장.
- **Soft Delete**: `deletedAt IS NULL` 조건 모든 조회 쿼리에 적용.
- **ServiceId**: `@ServiceId("CPMSEDUPGRRSLTLST/search")`, `@ServiceId("CPMSEDUPGRRSLTLST/save")` 형식 필수.
