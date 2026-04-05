# 📄 Compliance Education Management System Technical Specification (spec.md)

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

---

## 1. Requirement Refinement
### Functional
- **교육 실적 관리**: 준법지원 교육 실적 현황 조회 및 관리 기능.
- **엑셀 업로드**: 교육 실적 데이터를 엑셀 파일을 통해 일괄 등록.
- **사용자 자동 매핑**: 입력된 사용자 ID를 기반으로 성명 및 부서 정보 자동 조회 및 결합.
- **중복 검증**: 저장 시 기존 데이터와의 중복 여부 확인.

### Non-Functional
- **Performance**: API response time < 300ms (단, 대용량 엑셀 업로드 제외).
- **Security**: JWT based Authentication & RBAC (Role-Based Access Control).
- **Scalability**: Stateless architecture for horizontal scaling.

### Constraints
- **Tech Stack**: Spring Boot 3.x, Java 21, JPA, Querydsl.
- **External Integration**: [ASSUMED: 인사 시스템 API 또는 DB (사용자 정보 조회용)], Apache POI (Excel Library).

---

## 2. Atomic User Stories
- **US-01**: As an Admin, I want to upload an Excel file, so that I can register multiple education records at once.
- **US-02**: As an Admin, I want the system to automatically fetch user names and departments by ID, so that I don't have to enter them manually.
- **US-03**: As an Admin, I want the system to check for duplicate records, so that data integrity is maintained.
- **US-04**: As a User/Admin, I want to view the compliance education status, so that I can monitor the training progress.

---

## 3. Domain Modeling (Core)

### Entity: EducationRecord (Table: `education_record`)
| Name | Logical Type | Java Type | DB Type | Nullable | Constraints | Validation | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| id | UUID | UUID | uuid | false | PK | - | Primary Key |
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

### [POST] /api/v1/education-records/excel-upload
| Item | Detail |
| :--- | :--- |
| **Method** | `POST` |
| **Path** | `/api/v1/education-records/excel-upload` |
| **Description** | 엑셀 파일을 업로드하여 교육 실적을 일괄 등록함 |
| **Auth** | Required (Admin) |

**Request Body**
- `multipart/form-data` (file: MultipartFile)

**Response (200 OK)**
```json
{
  "success": true,
  "data": { "processedCount": 100 },
  "message": "Upload successful"
}

###[GET] /api/v1/education-records
-Description: 교육 실적 현황 목록 조회 (Pagination & Filter)
-Auth: Required
-Query Parameters:
-page: number (기본값: 0)
-size: number (기본값: 20)
-userId: string (선택 - 사번 검색)
-userName: string (선택 - 이름 검색)

**Response (200 OK)**
```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "userId": "STR001",
        "userName": "홍길동",
        "departmentName": "준법지원팀",
        "educationTitle": "윤리경영 교육",
        "completionDate": "2024-03-31T00:00:00"
      }
    ],
    "totalElements": 1,
    "totalPages": 1,
    "pageNumber": 0,
    "size": 20,
    "last": true
  },
  "message": "조회 성공"
}

### Error Codes
| Status Code | Message | Description |
| :--- | :--- | :--- |
| **401** | `Unauthorized` | 유효한 인증 정보가 없거나 인증에 실패함 |
| **403** | `Forbidden` | 요청한 리소스에 접근할 권한이 없음 (Admin 전용 등) |
| **404** | `Not Found` | 요청한 리소스를 찾을 수 없음 |
| **400** | `Bad Request` | 중복 데이터 존재 또는 입력값이 유효하지 않음 |
| **500** | `Internal Server Error` | 서버 내부 로직 처리 중 예기치 못한 오류 발생 |

## 6. UI/UX Flow
### Flow: 교육 실적 일괄 등록 및 확인
| Step | User Action | Page Name | Key Components | API Mapping | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 엑셀 파일 선택 및 업로드 버튼 클릭 | 실적 관리 페이지 | Upload Modal / Button | `POST .../excel-upload` | 파일 검증 및 DB 저장 |
| 2 | 업로드 결과 메시지 확인 | 실적 관리 페이지 | Toast Message | - | 목록 자동 새로고침 |
| 3 | 목록 필터링 및 조회 | 실적 관리 페이지 | Search Bar / Table | `GET .../education-records` | 검색 조건에 따른 데이터 출력 |


# AI_HINT
- **Validation**: `EducationRecordService`에서 저장 전 중복 체크 로직 구현.
- **Excel**: Apache POI 사용 시 `SXSSF`를 활용한 메모리 최적화 권장.
- **Soft Delete**: `@SQLRestriction("deleted_at IS NULL")` 적용.