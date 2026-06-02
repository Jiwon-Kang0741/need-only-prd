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

## 7. DB Seed Data (init.sql 포함 필수, menu_tree 기반)

> `db/init.sql`에는 반드시 아래 5개 테이블의 DDL/Seed를 포함한다.  
> 대상: `cmn_lbl`, `cmn_pgm`, `cmn_menu`, `cmn_role_pgm`, `cmn_role_menu`  
> 생성 순서: `cmn_lbl` → `cmn_pgm` → `cmn_menu` → `cmn_role_pgm` → `cmn_role_menu`  
> SQL은 PostgreSQL 문법만 사용한다. (`MERGE` 대신 `INSERT ... ON CONFLICT ... DO UPDATE` 권장)

### 7.1 입력 원본 (menu_tree.json)

- 화면 설계에서 선택된 메뉴를 기준으로 `menu_tree.json`에서 조회한다.
- 조회 키 우선순위: `menu_id` > `menu_name`.
- 사용 컬럼: `menu_id`, `p_menu_id`, `menu_nm`, `sort_num`, `roles`.

### 7.2 매핑 규칙

- `cmn_menu.menu_id` ← `menu_tree.menu_id`
- `cmn_menu.lbl_cd` ← `menu_tree.menu_id`
- `cmn_menu.p_menu_id` ← `menu_tree.p_menu_id`
- `cmn_menu.menu_sort` ← `menu_tree.sort_num`
- `cmn_pgm.lbl_cd` ← `menu_tree.menu_id`
- `cmn_pgm.pgm_desc` ← `menu_tree.menu_nm`
- `cmn_pgm.pgm_url` ← **실제 생성되는 Vue 페이지 경로 기반으로 산출**
  - 생성 파일 경로: `src/pages/{module}/{category}/{screenId}/index.vue`
  - 변환 규칙: `pgm_url = /pages/{module}/{category}/{screenId}/index.vue`
  - 예: `src/pages/mon/risk/cpmsMonRiskLst/index.vue` → `/pages/mon/risk/cpmsMonRiskLst/index.vue`
- `cmn_lbl.lbl_cd` ← `menu_tree.menu_id`
- `cmn_lbl.lbl_nm` ← `menu_tree.menu_nm`

### 7.2-A Vue 화면 라벨 호출 키 규칙 (UI 라벨)

- Vue 화면에서 사용하는 UI 라벨 호출 키는 아래 규칙으로 생성한다.
  - `{대컴포넌트명}.{라벨ID}`
  - 예: `SearchForm.searchDate`, `DataTable.colRiskStatus`
- `{대컴포넌트명}` prefix는 추정 이름을 만들지 않고, 실제 생성된 Vue 컴포넌트/폴더명(prefix)를 그대로 사용한다.
- 대컴포넌트명은 아래 고정 블록 단위를 사용한다.
  - `SearchForm`
  - `DataTable`
  - `SumGrid`
  - `EditDialog` / `DetailDialog` (다이얼로그 존재 시)
  - `TabPanel` (탭 구조 시)
  - 예: `src/pages/mon/risk/cpmsMonRiskLst/components/cpmsMonRiskLstSearchForm/`
  - 예: `src/pages/mon/risk/cpmsMonRiskLst/components/cpmsMonRiskLstDataTable/`
- Vue 화면에서는 모든 라벨을 `t('{대컴포넌트명}.{라벨ID}')` 형태로 호출한다.
- 하드코딩 라벨 텍스트(`'조회일자'`, `'사용자명'` 등) 직접 출력은 지양하고 i18n 키를 사용한다.

### 7.2-B cmn_lbl 생성 원칙 (menu 라벨 + 화면 UI 라벨)

- `cmn_lbl`은 아래 두 범주를 모두 생성해야 한다.
  - 메뉴 라벨: `menu_tree.menu_id`/`menu_tree.menu_nm` 기반
  - 화면 UI 라벨(`cmn_lbl.lbl_cd`): `{화면코드}.{대컴포넌트명}.{라벨ID}` 기반
- Vue i18n 호출 키는 `cmn_lbl.lbl_cd`와 분리하여 `{대컴포넌트명}.{라벨ID}` 형식을 사용한다.
- `cmn_lbl.lang_cd`는 기본값으로 `'ko-KR'`를 사용한다. (다국어 확장 시 추가 row로 확장)
- 동일 `lbl_cd + lang_cd` 키가 이미 존재하면 업데이트한다.
- Upsert 문법은 PostgreSQL `INSERT ... ON CONFLICT ... DO UPDATE`를 사용한다. (`MERGE` 사용 금지)

### 7.3 권한 규칙

- `cmn_role_menu`, `cmn_role_pgm`는 대상 키 기준 선삭제 후 재등록한다.
- `menu_tree.roles`를 기준으로 role 매핑을 생성한다.
- `DEV_AUTO` 권한은 항상 `cmn_role_menu`, `cmn_role_pgm`에 자동 포함한다. (중복 금지)

### 7.4 Fallback 규칙

- 지정된 메뉴를 `menu_tree.json`에서 찾지 못하면:
  - 부모 메뉴: `ROOT98`
  - 생성 `menu_id`: `ROOT98_YYMMDD_NNN` 형식 (예: `ROOT98_260526_001`)
  - 같은 날짜 내 NNN은 3자리 증가값 사용
- fallback으로 생성된 메뉴도 동일하게 `cmn_lbl`, `cmn_pgm`, `cmn_menu`, `cmn_role_*`를 모두 생성한다.

### 7.5 감사/기본 컬럼 규칙

- `insert_uid`, `update_uid`: `'SYSTEM'`
- `insert_dt`, `update_dt`: `now()`
- `use_yn`: `'Y'`

### 7.6 검증 체크리스트

- [ ] `cmn_lbl`, `cmn_pgm`, `cmn_menu`, `cmn_role_pgm`, `cmn_role_menu`가 모두 생성되었는가?
- [ ] `cmn_lbl.lang_cd` 기본값이 `'ko-KR'`로 생성되었는가?
- [ ] `cmn_lbl` 화면 라벨 ID가 `{화면코드}.{대컴포넌트명}.{라벨ID}` 규칙을 따르는가?
- [ ] 대컴포넌트명이 `SearchForm`, `DataTable`, `SumGrid`, `EditDialog`, `DetailDialog`, `TabPanel` 중 실제 화면 블록명으로 사용되었는가?
- [ ] Vue 라벨 호출이 `t('{대컴포넌트명}.{라벨ID}')` 규칙을 따르는가?
- [ ] `DEV_AUTO` 권한이 `cmn_role_menu`, `cmn_role_pgm`에 포함되었는가?
- [ ] fallback(`ROOT98_YYMMDD_NNN`) 규칙이 적용되었는가?
- [ ] `menu_id`/`pgm_id`/`lbl_cd` 참조 일관성이 유지되는가?
- [ ] `cmn_pgm.pgm_url`이 실제 `vue_page` 파일 경로(`src/pages/{module}/{category}/{screenId}/index.vue`)와 일치하는가?

---

# AI_HINT
- **Framework**: Spring Boot + MyBatis (Mapper XML)
- **Validation**: `CpmsEduPgrRsltLstServiceImpl`에서 저장 전 중복 체크 로직 구현.
- **Excel**: Apache POI 사용 시 `SXSSF`를 활용한 메모리 최적화 권장.
- **Soft Delete**: `deletedAt IS NULL` 조건 모든 조회 쿼리에 적용.
- **ServiceId**: `@ServiceId("CPMSEDUPGRRSLTLST/search")`, `@ServiceId("CPMSEDUPGRRSLTLST/save")` 형식 필수.
- **DB Seed**: `db/init.sql`은 Section 7의 `menu_tree` 규칙을 그대로 반영하여 `cmn_lbl` → `cmn_pgm` → `cmn_menu` → `cmn_role_pgm` → `cmn_role_menu` 순서로 생성한다. `DEV_AUTO` 자동 포함, 메뉴 미존재 시 `ROOT98_YYMMDD_NNN` fallback을 반드시 적용한다. 특히 `cmn_pgm.pgm_url`은 실제 Vue 생성 경로(`src/pages/{module}/{category}/{screenId}/index.vue`)에서 `/pages/{module}/{category}/{screenId}/index.vue` 규칙으로 산출해야 하며, 화면 UI 라벨은 `cmn_lbl`에 `{화면코드}.{대컴포넌트명}.{라벨ID}`로 upsert(`ON CONFLICT`)하고 Vue 호출은 `t('{대컴포넌트명}.{라벨ID}')`를 사용해야 한다.
