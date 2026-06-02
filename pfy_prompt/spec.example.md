# 📄 (Example) 교육 프로그램 실적 조회 Technical Specification (SPEC.md)

> 이 파일은 **채워진 예시**입니다. 구조만 필요하면 `spec.template.md`를, LLM에 주입되는 빈 골격은 동일 디렉터리의 `spec.template.md`가 사용됩니다.
>
> 목적:
> 본 문서는 화면/업무별 선언 데이터만 정의한다.
>
> 공통 규칙은 아래 문서를 따른다.
>
> * DATA_STANDARD.md (`pfy_prompt/DataGuide/00.data_standard.md`)
> * SEED_STANDARD.md
> * FRONT_UI_STANDARD.md
> * SQL_OUTPUT_CONTRACT.md
> * 백엔드 DTO·검색 페이징: `pfy_prompt/BackendGuide/표준.md` (특히 `SearchBaseDto`)

### 공통 주의 (검색 API 페이징)

> **검색 API** Request Body의 페이징 필드는 `com.common.dto.base.SearchBaseDto`와 **동일한 필드명**을 쓴다: **`page`**, **`size`** (`integer`). `page_index`, `page_size` 등 다른 이름은 SPEC에 적지 않는다.  
> 구현·상속·재선언 금지 등 상세는 **`BackendGuide/표준.md`** 의 SearchBaseDto·Request DTO 절을 따르고, SPEC·DDL과의 정합은 **`DataGuide/00.data_standard.md`(DATA_STANDARD)** 를 따른다.  
> 화면별 `SPEC.md` §8.1에는 위 두 필드를 표에 넣거나, **비즈니스 검색 조건만** 나열하고 본 주의 블록을 따른다고만 명시해도 된다.

### 공통 주의 (PK·ID / Java·MyBatis)

> SPEC §4 컬럼의 `logical_type`이 **`uuid`**인 PK·식별자라도, **Java/MyBatis 계층에서는 `java.lang.String`** 으로 둔다 (`varchar`/`uuid` 컬럼과 매핑). **`java.util.UUID` 타입·import·`UUID.randomUUID()` 사용 금지** — 코드젠 `static_check`·sanitize와 충돌한다.  
> DB 물리 타입·DDL은 **DATA_STANDARD**·§4를 따르고, 구현 규칙은 **`BackendGuide/표준.md`** §11.5·§11.6을 따른다.

### 공통 주의 (Soft Delete `del_yn`)

> 논리 삭제 컬럼 **`del_yn`** 은 CPMS·DATA_STANDARD에서 **DB `CHAR(1)`**, 값 **`'Y'` / `'N'`** 로 **고정**한다. SPEC §4 `logical_type`에는 **`boolean`이 아니라 `yn_flag`** 를 쓴다. DDL·Mapper·Java는 **DATA_STANDARD §6·§6.1** 을 따른다.

### 공통 주의 (업무 일시·등록일 `reg_dt` 등)

> 등록일·발생일·처리일 등 **시점 의미**가 있는 컬럼은 SPEC §4에서 **`logical_type: string` + 임의 길이(예: 255)** 로 두지 않는다. DB 저장은 **`timestamptz`**(날짜만이면 **`date`**)·SPEC 동일 `logical_type`을 사용한다. 화면 표시 문자열은 **`FrontendGuide/04_DataTable_구현.md`**, **`성능_최적화_가이드.md`**, **`14_자주_발생하는_에러.md`** 에 따라 **`watch` + `nextTick()` 또는 그리드 데이터 전처리**에서만 포맷하고, **DataTable 템플릿 슬롯에서 날짜 포맷 금지**이다. 레거시만 `varchar` 저장이면 `[NEEDS CLARIFICATION]`과 함께 근거를 명시하고, 코드젠 기본은 **시점형 DB 타입 + 프론트 전처리**이다.

### 공통 주의 (코드·키 표시명 `*_nm`)

> **`risk_evl_rslt_cd_nm`** 등 **코드/키에 대한 가독성 표시명**(`*_nm` 접미)은 **업무 테이블 DDL에 저장하지 않는 것을 원칙**으로 한다. **`db_init_sql`의 `CREATE TABLE`** 에 `*_nm` 물리 컬럼을 두지 않는다.  
> 목록·상세 **조회 SQL(SELECT)** 에서만 `*_cd`(또는 FK)에 대해 **공통코드·마스터 LEFT JOIN** 등으로 별칭을 붙여 채운다. **ResDto·Vue**에는 응답 필드로 둘 수 있으나 **INSERT/UPDATE 바인딩 대상이 아니다.** §11 외부 의존(코드사전)과 정합시킨다. 레거시 비정규화 저장이 있으면 `[NEEDS CLARIFICATION]`·근거를 명시한다.

---

# 1. Screen Metadata

| 항목            | 값                                                 |
| ------------- | ------------------------------------------------- |
| screen_id     | CpmsEduPgrRsltLst                                 |
| screen_name   | 교육 프로그램 실적 조회                                     |
| module        | edu                                               |
| category      | program                                           |
| page_type     | list                                              |
| menu_id       | EDU_PROG_RSLT                                     |
| program_id    | CPMSEDUPGRRSLTLST                                 |
| route_path    | /edu/program/result                               |
| vue_page_path | src/pages/edu/program/cpmsEduPgrRsltLst/index.vue |
| seed_enabled  | true                                              |

---

# 2. Business Requirement

## 2.1 Functional Requirements

### FR-01 교육 실적 조회

* 교육 프로그램 실적 현황 목록 조회 기능 제공

### FR-02 엑셀 업로드

* Excel 파일 기반 일괄 등록 기능 제공

### FR-03 사용자 자동 매핑

* user_id 기준 사용자명/부서 자동 조회

### FR-04 중복 검증

* 동일 사용자/교육/수료일 중복 저장 금지

---

## 2.2 Non-Functional Requirements

| 항목                | 값         |
| ----------------- | --------- |
| max_response_time | 300ms     |
| authentication    | JWT       |
| authorization     | RBAC      |
| architecture      | stateless |

---

## 2.3 Technical Constraints

| 항목            | 값           |
| ------------- | ----------- |
| backend       | Spring Boot |
| orm           | MyBatis     |
| frontend      | Vue3        |
| ui_library    | PrimeVue    |
| excel_library | Apache POI  |

---

# 3. Entity Definition

## 3.1 Entity

| 항목          | 값                  |
| ----------- | ------------------ |
| entity_name | EduProgramResult   |
| table_name  | cptb_edu_prog_rslt |
| description | 교육 프로그램 실적         |
| primary_key | edu_prog_rslt_id   |

---

# 4. Column Definition

## 4.1 Columns

| column_name      | logical_name | logical_type | nullable | length | precision | scale | pk    | fk    | unique | indexed |
| ---------------- | ------------ | ------------ | -------- | ------ | --------- | ----- | ----- | ----- | ------ | ------- |
| edu_prog_rslt_id | 교육실적ID       | uuid         | false    | -      | -         | -     | true  | false | true   | true    |
| user_id          | 사용자ID        | string       | false    | 50     | -         | -     | false | false | false  | true    |
| user_name        | 사용자명         | string       | false    | 100    | -         | -     | false | false | false  | false   |
| department_name  | 부서명          | string       | false    | 100    | -         | -     | false | false | false  | false   |
| education_title  | 교육명          | string       | false    | 255    | -         | -     | false | false | false  | true    |
| completion_date  | 수료일          | timestamptz  | false    | -      | -         | -     | false | false | false  | true    |
| reg_dt           | 등록일          | timestamptz  | true     | -      | -         | -     | false | false | false  | true    |
| del_yn           | 삭제여부         | yn_flag      | false    | 1      | -         | -     | false | false | false  | true    |

*(PK `uuid` → Java `String`: 상단 **공통 주의 (PK·ID / Java·MyBatis)**·DATA_STANDARD §3.3. `del_yn` → `yn_flag` / DB `CHAR(1)`: **공통 주의 (Soft Delete `del_yn`)**·§3.4·§6.1. 업무 일시·등록일: **`timestamptz`/`date`**, `string(255)` 표시 전용 금지 — **공통 주의 (업무 일시·등록일 `reg_dt` 등)**·§3.5. `*_nm` 표시명: **DDL 비저장·SELECT 조인만** — **공통 주의 (코드·키 표시명 `*_nm`)**·§2.4.)*

---

# 5. Relation Definition

## 5.1 Relations

현재 직접 FK 없음.

사용자 정보는 외부 사용자 시스템 조회 기반으로 처리한다.

---

# 6. Index Definition

## 6.1 Unique Index

| index_name                            | columns                                   | unique |
| ------------------------------------- | ----------------------------------------- | ------ |
| uk_cptb_edu_prog_rslt_user_title_date | user_id, education_title, completion_date | true   |

---

## 6.2 Search Index

| index_name                             | columns         | unique |
| -------------------------------------- | --------------- | ------ |
| idx_cptb_edu_prog_rslt_user_id         | user_id         | false  |
| idx_cptb_edu_prog_rslt_completion_date | completion_date | false  |

---

# 7. Business Rules

## 7.0 DB Seed & codegen alignment (요약)

> 코드젠이 SPEC에서 `## 7.` 접두 블록을 주입에 사용한다. 상세는 `SEED_STANDARD.md` §1.5.

* 시드 메타·메뉴·역할의 SSOT: **`# 10. Seed Metadata`**
* `cmn_*` 순서·`ON CONFLICT`·`DEV_AUTO`·`ROOT98` fallback: **SEED_STANDARD.md**
* `pgm_url`: `vue_page_path` → `/pages/.../index.vue` 변환
* 화면 UI 라벨: `{화면코드}.{대컴포넌트명}.{라벨ID}` — Vue: `t('{대컴포넌트명}.{라벨ID}')`
* 실행 SQL 전문은 spec이 아닌 `db_init_sql`에서 생성

---

## 7.1 Duplicate Validation

아래 조건 동일 시 중복으로 간주한다.

* user_id
* education_title
* completion_date

중복 저장 시:

* validation error 반환
* insert 금지

---

## 7.2 Authorization Rule

업로드 기능은 ADMIN 권한만 허용한다.

---

## 7.3 User Mapping Rule

엑셀 업로드 시:

* user_id 기준
* 외부 사용자 시스템 조회
* user_name
* department_name

자동 매핑 수행.

조회 실패 시:

* validation error 반환
* 저장 금지

---

# 8. API Definition

## 8.1 Search API

| 항목            | 값                                        |
| ------------- | ---------------------------------------- |
| api_id        | searchEducationResult                    |
| method        | POST                                     |
| path          | /online/mvcJson/CPMSEDUPGRRSLTLST-search |
| service_id    | CPMSEDUPGRRSLTLST/search                 |
| auth_required | true                                     |

### Request Fields

| field_name           | type    |
| -------------------- | ------- |
| user_id              | string  |
| user_name            | string  |
| completion_date_from | date    |
| completion_date_to   | date    |
| page                   | integer |
| size                   | integer |

*(페이징: `SearchBaseDto`와 동일 필드명 — `spec.template.md` 공통 주의·DATA_STANDARD §1.2 참고.)*

---

## 8.2 Save API

| 항목            | 값                                      |
| ------------- | -------------------------------------- |
| api_id        | saveEducationResult                    |
| method        | POST                                   |
| path          | /online/mvcJson/CPMSEDUPGRRSLTLST-save |
| service_id    | CPMSEDUPGRRSLTLST/save                 |
| auth_required | true                                   |
| required_role | ADMIN                                  |

### Request Type

* multipart/form-data

### Upload File

| field_name | type          |
| ---------- | ------------- |
| file       | MultipartFile |

---

# 9. UI Block Definition

## 9.1 SearchForm

| label_id           | label_name |
| ------------------ | ---------- |
| userId             | 사용자 ID     |
| userName           | 사용자명       |
| completionDateFrom | 시작 수료일     |
| completionDateTo   | 종료 수료일     |
| search             | 조회         |

---

## 9.2 DataTable

| label_id       | label_name |
| -------------- | ---------- |
| userId         | 사용자 ID     |
| userName       | 사용자명       |
| departmentName | 부서명        |
| educationTitle | 교육명        |
| completionDate | 수료일        |

---

## 9.3 UploadDialog

| label_id    | label_name |
| ----------- | ---------- |
| uploadExcel | 엑셀 업로드     |
| upload      | 업로드        |
| close       | 닫기         |

---

# 10. Seed Metadata

## 10.1 Menu Information

| 항목             | 값             |
| -------------- | ------------- |
| menu_id        | EDU_PROG_RSLT |
| menu_name      | 교육 프로그램 실적 조회 |
| parent_menu_id | ROOT01        |
| menu_sort      | 1             |
| menu_component_key | edu       |
| seed_enabled   | true          |

---

## 10.2 Role Mapping

| role_code |
| --------- |
| ADMIN     |
| USER      |

---

## 10.3 Mockup-derived Common Code (optional)

> 교육 예시 화면에는 Mockup 정적 Select 기반 코드가 없으면 **비워 둔다**. 아래는 **리스크 등급 검색 필드가 있는 화면**을 가정한 예시 행이다.

| class_cd   | class_nm   | code_cd | code_nm |
| ---------- | ---------- | ------- | ------- |
| riskGrdCd  | 리스크 등급    | L       | Low     |
| riskGrdCd  | 리스크 등급    | M       | Medium  |
| riskGrdCd  | 리스크 등급    | H       | High    |

---

# 11. External Dependency

> **§10.3 vs §11**: §10.3은 목업 정적 Select에서 시드할 코드값이다. §11은 외부 시스템·쿼리 마스터 등이다.

> 코드·키의 **표시명(`*_nm`)** 은 **조회 시에만** 채운다(상단 **공통 주의 (코드·키 표시명 `*_nm`)**·DATA_STANDARD §2.4). 아래 표는 공통코드·마스터 등 **조인/참조 소스**를 선언한다.

## 11.1 User Information System

| 항목              | 값                       |
| --------------- | ----------------------- |
| dependency_name | user_information_system |
| required        | true                    |
| purpose         | 사용자명/부서 조회              |

조회 실패 시:

* 저장 실패 처리

---

# 12. Validation Rules

## 12.1 Required Validation

필수 검증:

* menu_id 존재 여부
* program_id 존재 여부
* table_name 존재 여부
* PK 존재 여부
* duplicate index 충돌 여부

---

## 12.2 Fail-Fast Rule

아래 발생 시 생성 중단:

* unresolved dependency
* duplicate index
* duplicate column
* invalid logical_type
* nullable mismatch
* duplicate menu_id
