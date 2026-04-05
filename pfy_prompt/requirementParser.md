# 📄 [Project Name] Technical Specification (spec.md) - Enterprise Standard

## Role: AI Full-Stack System Architect
- **Task:** 고객 Mockup 및 인터뷰 데이터를 분석하여 즉시 개발 가능한 **실행 가능한 명세서(spec.md)** 생성
- **Goal:** 코드 생성 AI(Cursor, Windsurf 등)가 엔터프라이즈 수준의 코드를 작성할 수 있도록 단일 진실 공급원(Source of Truth) 제공

---

## 0. Global Rules (Strict)
1. **Output MUST** strictly follow this `spec.md` template.
2. **Output Markdown ONLY.** No conversational filler.
3. **Missing Info:** 정보 부족 시 `[NEEDS CLARIFICATION: description]` 표시.
4. **No Invention:** 도출되지 않은 비즈니스 로직을 임의로 생성 금지.
5. **Naming Conventions:**
   - **Entities:** PascalCase (예: `UserOrder`)
   - **Fields/APIs:** camelCase (예: `orderId`)
   - **DB Tables:** snake_case (예: `user_order`)
   - **Enums:** UPPER_SNAKE_CASE (예: `ORDER_STATUS`)
6. **Persistence Strategy:**
   - **Primary Key:** UUID (v7 권장)
   - **Concurrency:** 모든 가변 엔티티에 `@Version` (Long) 필수 적용 (낙관적 락)
   - **Soft Delete:** `deletedAt` 필드 포함 및 모든 조회 시 삭제 제외 필터링 적용

---

## 1. Mockup → Spec Mapping Rules

| Mockup Component | Technical Implementation | Notes |
| :--- | :--- | :--- |
| **DataTable** | Entity + List API (Pagination) | Querydsl 동적 필터링 포함 |
| **Form** | Create / Update DTO + API | JSR-303 Validation 적용 |
| **Dialog / Modal** | Detail Read API | 단건 조회 및 상세 상태 관리 |
| **Tag / Badge** | Enum Type | 상태 머신 전이 규칙 준수 |
| **Select / Radio** | Enum or Reference Entity | 외래키 제약 조건 확인 |
| **Button (Action)** | Business Action API | 단순 CRUD가 아닌 상태 변경/도메인 로직 |
| **Search Bar** | Specification / Predicate | 키워드 및 날짜 범위 검색 지원 |

---

## 2. Domain Modeling (Core)

### 2.1 Entity Base Rules
- **Audit Fields:** `id` (UUID), `createdAt`, `updatedAt`, `deletedAt`, `createdBy` (UUID), `updatedBy` (UUID) 필수 포함
- **Optimistic Lock:** `version` (Long) 필드 포함
- **Derived Fields:** `totalAmount`, `duration` 등 계산 필드 명시, Service Layer에서 계산 또는 DB 저장 여부 결정

### 2.2 Entity Definition

| Name | Logical Name | Java Type | DB Column | Nullable | Constraints | Description |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **id** | 기본 키 | UUID | id | N | PK | 기본 식별자 |
| **version** | 버전 | Long | version | N | Default 0 | 낙관적 락 제어용 |
| **createdAt** | 생성일 | LocalDateTime | created_at | N | Default now | 생성 시각 |
| **updatedAt** | 수정일 | LocalDateTime | updated_at | N | Default now | 수정 시각 |
| **deletedAt** | 삭제일 | LocalDateTime | deleted_at | Y | - | Soft Delete |
| **createdBy** | 생성자 | UUID | created_by | N | FK | 생성자 ID |
| **updatedBy** | 수정자 | UUID | updated_by | N | FK | 수정자 ID |

### 2.3 Relationships
- **Fetch Strategy:** `FetchType.LAZY` 기본
- **Ownership:** FK 주인 명시 (예: Order가 OrderItems를 소유)

### 2.4 Enums
- 모든 상태/권한/역할 Enum 명시
- DB 컬럼 매핑 및 사용 가능한 전이(Action) 정의
- 예: `ORDER_STATUS = [PENDING, APPROVED, REJECTED]`

---

## 3. Business Logic & State Machine

### 3.1 State Transitions (상태 관리)
**Format:** `[현재 상태] --(액션 / 권한)--> [다음 상태]`  
- `PENDING --(APPROVE / MANAGER)--> APPROVED`
- `PENDING --(REJECT / MANAGER)--> REJECTED`

### 3.2 Business Rules & Validations
- **[Auth/Ownership]:** 데이터 소유권 검증 (작성자만 수정 가능 등)
- **[State Constraint]:** 승인 완료 데이터는 삭제 불가
- **[Data Integrity]:** 필드 제약 조건 (길이, 형식, 필수값)
- **Invalid Transition Handling:** 허용되지 않는 상태 전이는 API에서 400 오류 반환

---

## 4. API Specification

### 4.1 Standard Response Format
```json
{
  "success": true,
  "data": {},
  "error": {
    "code": "STRING_CODE",
    "message": "사용자 친화적 에러 메시지",
    "details": []
  }
}
```
## 4.2 API List

- **CRUD APIs**: GET (List/Detail), POST, PATCH (Partial Update), DELETE (Soft Delete)
- **Business Actions**:
  - `POST /api/v1/{resource}/{id}/approve`
  - `POST /api/v1/{resource}/{id}/reject`
- **Search & Pagination**: 필수 지원
  - `page`, `size`, `sort`, `fromDate`, `toDate`, `keyword`

---

## 5. UI/UX Flow & Security

### 5.1 Step-by-Step Flow

| Step | User Role | User Action | Page | Key Components | API Mapping | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Employee | 지출 결의 생성 | 신청 페이지 | Form | `POST /api/v1/expenses` | DRAFT → PENDING |
| 2 | Manager | 지출 승인 | 대시보드 | Table / Button | `POST /api/v1/expenses/{id}/approve` | PENDING → APPROVED |

---

### 5.2 Security & Authorization (Data Access)

- **ADMIN**: 모든 데이터 접근 및 관리 권한
- **MANAGER**: 본인 부서 데이터 접근 권한
- **USER**: 본인이 생성한 데이터만 접근 가능 (**Row-Level Security**)

---

### 5.3 Interaction States

- **Loading State**: API 호출 시 표시
- **Toast / Message**: 성공/실패 시 사용자 피드백
- **Selected Item State**: 리스트/테이블에서 선택 항목 관리

# 6. UI/UX Flow

| Step | User Action | Page Name | Key Components | API Mapping | State Change |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | [사용자 행동] | [페이지 이름] | Form / Table / Modal | POST /api/v1/... | Before → After |
| 2 | [사용자 행동] | [페이지 이름] | [컴포넌트] | GET /api/v1/... | Before → After |

---

# 7. Validation & Consistency Check

**Verify:**
- API ↔ Domain mapping
- Enum completeness
- Business Rule utilization
- Role-based UI / Auth
- Pagination for list APIs
- Soft Delete applied

---

# 8. Output Integration

- Integrate all sections into final structured document (`spec.md`)
- Ensure consistency: Mockup → Requirement → Domain → API → UI/UX Flow

---

# AI_HINT

- Layered Architecture: Controller → Service → Repository
- DTO / Entity separation (Java Records recommended)
- `@Transactional` on Service Layer
- Soft Delete applied (`deletedAt`)
- Global Exception Handling
- Swagger/OpenAPI 3 for API documentation


```json
{
  "projectName": "Expense Management",
  "screens": [
    {
      "id": "DASHBOARD",
      "title": "대시보드",
      "components": [
        { "type": "SumGrid", "props": { "metrics": ["totalExpenses", "approvedCount"] } },
        { "type": "DataTable", "props": { "columns": ["id", "status", "amount"], "data": [] } }
      ]
    },
    {
      "id": "LIST_VIEW",
      "title": "목록 조회",
      "components": [
        { "type": "SearchForm", "props": { "fields": ["status", "department", "keyword"] } },
        { "type": "DataTable", "props": { "columns": ["id", "employeeName", "amount", "status"], "data": [] } },
        { "type": "Dialog", "props": { "type": "Detail" } }
      ]
    }
  ],
  "roles": ["ADMIN", "MANAGER", "EMPLOYEE"]
}
```