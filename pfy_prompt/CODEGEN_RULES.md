# CODEGEN_RULES — 코드 생성 에이전트 주입용 규칙

> 출처(pfy_prompt 가이드)에서 코드 생성에 필요한 규칙만 추출·정리한 문서.
> 패키지/경로는 **가이드(`표준.md §11.4`) 기준 `biz.{module}`** 를 따른다 (skeleton `hsc.tomms.web` 아님).
> 각 섹션은 해당 file_type 에이전트 프롬프트에 그대로 주입할 수 있도록 self-contained 하게 작성.

---

## 0. 규칙 출처 매핑

| 영역 | 소스 md |
|------|--------|
| 네이밍 | `표준.md §3`, `namebook.md`, `CPMS_namebook.md` |
| 파일 경로/패키지 | `표준.md §11.4`, `§4.2` |
| 생성 순서 | `표준.md §11.3` |
| DB Init SQL | `표준.md §11.1`, `DataGuide/00.data_standard.md`, `DataGuide/01.seed_standard.md` |
| DTO | `표준.md §4.3` |
| Mapper XML | `표준.md §11.2`, `§4.5` |
| DAO Impl | `표준.md §4.4` |
| Service Impl | `표준.md §4.3(Service)`, `§4.8`, `§8.1` |
| import | `표준.md §10.3`, `§10.4` |
| DB 컬럼 매핑 | `BackendGuide/테이블정보.md` |
| Vue | `FrontendGuide/00·02·03·04·06·07` |

---

## 1. 네이밍 (공통)

- **화면 ID**: `[LV1][LV2][행위][역할]` PascalCase — 예 `CpmsEduRegLst` (Cpms=LV1, Edu=LV2, Reg=등록, Lst=내역)
- **역할(suffix)**: `Lst`(목록/조회/로그/현황), `Edit`(등록/수정), `SPopup`(조회팝업), `EPopup`(CRUD팝업)
- **모듈 코드**(`CPMS_namebook`): `act, mon, pra, edu, cnr, sys, top, rnm, inf, evn, cmn`
- **클래스명**:
  - DAO `{Screen}Dao`, `{Screen}DaoImpl`
  - Service `{Screen}Service`, `{Screen}ServiceImpl`
  - Mapper `{Screen}Mapper.xml`
  - DTO `{Screen}ReqDto`, `{Screen}ResDto`
- **메서드명**:
  - Service 레이어: `search`(조회), `save`(등록/수정/삭제)
  - DAO/Mapper(도메인 접미사형, statement id와 1:1): `select{Screen}List`, `select{Screen}`, `select{Screen}Count`, `insert{Screen}`, `update{Screen}`, `delete{Screen}`
- **변수**: camelCase / **DB 컬럼**: snake_case → 응답은 `AS "camelCase"` 별칭

---

## 2. 파일 경로 / 패키지 (`표준.md §11.4`) — biz.{module}

```
<!-- BEGIN codegen-paths (naming.file_path 가 파싱한다: {module}=모듈세그먼트, {screen}=화면세그먼트, {Screen}=화면코드 PascalCase) -->
db_init_sql  = db/init.sql
dto_request  = src/main/java/biz/{module}/dto/request/{Screen}ReqDto.java
dto_response = src/main/java/biz/{module}/dto/response/{Screen}ResDto.java
dao          = src/main/java/biz/{module}/dao/{Screen}Dao.java
dao_impl     = src/main/java/biz/{module}/dao/{Screen}DaoImpl.java
service      = src/main/java/biz/{module}/service/{Screen}Service.java
service_impl = src/main/java/biz/{module}/service/{Screen}ServiceImpl.java
mapper_xml   = src/main/resources/biz/{module}/mybatis/mappers/{Screen}Mapper.xml
vue_page     = src/pages/{module}/{screen}/{Screen}/index.vue
vue_types    = src/api/pages/{module}/{screen}/types.ts
<!-- END codegen-paths -->
```

- **패키지는 모듈 레벨까지만**. 화면코드 삽입 **절대 금지** (`biz.edu.dao` ✅ / `biz.edu.cpmseduproglst.dao` ❌ / `com.*` 접두어 ❌)
- Mapper namespace = `biz.{module}.dao.{Screen}DaoImpl`

---

## 3. 생성 순서 (`표준.md §11.3`)

```
dto_request → dto_response → mapper_xml → dao_impl → service_impl
vue_types → vue_page
```
- `mapper_xml`은 `dao_impl` **이전** (DaoImpl이 statement id 참조)
- `service_impl`은 `dao_impl` **이후** (ServiceImpl이 DaoImpl 메서드 호출)
- `db/init.sql`은 독립 (의존 없음)

---

## 4. 파일별 규칙

### 4.1 db_init_sql (`표준.md §11.1` + DataGuide)
- **PostgreSQL 전용**. MySQL/MariaDB 문법 절대 금지:
  - PK `BIGSERIAL`/`SERIAL` (❌`AUTO_INCREMENT`), `BOOLEAN`(❌`TINYINT(1)`), `TEXT`(❌`LONGTEXT`)
  - `TIMESTAMP`/`TIMESTAMPTZ`(❌`DATETIME`), `NOW()`, `COALESCE`(❌`IFNULL`), `ILIKE`(❌`LIKE`), `::TEXT`/`CAST`
  - `ENGINE=`/`CHARSET=` 금지
- **논리삭제** `del_yn CHAR(1) NOT NULL DEFAULT 'N' CHECK (del_yn IN ('Y','N'))` — `BOOLEAN` 금지
- **감사 컬럼**: `insert_uid`, `insert_dt`, `update_uid`, `update_dt` (`DEFAULT NOW()`)
- **표시명 `*_nm` 은 DDL에 저장 안 함** (조회 시 JOIN/COALESCE)
- **시드(seed)**:
  - 필수 테이블: `cmn_lbl`, `cmn_pgm`, `cmn_menu`, `cmn_role_pgm`, `cmn_role_menu`
  - 선택: `cmn_class`, `cmn_code` — SPEC `§10.3`에 행 있을 때만 (있으면 둘 다)
  - **순서**: `cmn_class → cmn_code → cmn_lbl → cmn_pgm → cmn_menu → cmn_role_pgm → cmn_role_menu`
  - upsert: `INSERT … ON CONFLICT … DO UPDATE` (MERGE 금지)
  - `cmn_lbl.lbl_cd = {program_id}.{대컴포넌트명}.{라벨ID}`, `lang_cd` 기본 `'ko-KR'`
  - `DEV_AUTO` 롤 포함, `ROOT98` fallback parent
  - **Natural Key (`ON CONFLICT` 대상, `DataGuide/01 §5`)**: `cmn_class(lang_cd,cls_id)`, `cmn_code(cls_id,code_cd)`, `cmn_lbl(lbl_cd,lang_cd)`, `cmn_menu(menu_id)`, `cmn_pgm(pgm_id)`, `cmn_role_menu(role_id,menu_id)`, `cmn_role_pgm(role_id,pgm_id)`
  - **`pgm_url` 변환**: `src/pages/{module}/{category}/{screenId}/index.vue` → `/pages/{module}/{category}/{screenId}/index.vue` (`src` 제거)
  - **`menu_id`** = `{p_menu_id}{순번접미}`, **`menu_sort`** = 순번접미를 정수 해석(앞자리 0 제거)

### 4.2 dto_request / dto_response (`표준.md §4.3`)
- ReqDto `extends SearchBaseDto` (페이징 `page`/`size`는 base 제공 — 자식에 재선언 금지)
- ResDto `extends AuditBaseDto` (감사 필드는 base 제공 — 자식에 재선언 금지)
- **감사 컬럼↔필드 매핑 (`표준.md §4.7`)** — Mapper에서 이 별칭으로 매핑:

  | Java 필드 (AuditBaseDto) | DB 컬럼 |
  |---|---|
  | `fstCrtrId` | `insert_uid` |
  | `fstCretDtm` | `insert_dt` |
  | `lastMdfrId` | `update_uid` |
  | `lastMdfcDtm` | `update_dt` |
- **날짜/일시 필드 = `String`** (`Date`/`LocalDate`/`LocalDateTime` 금지)
- **ID 필드 = `String`** (`java.util.UUID`/`UUID.randomUUID()` 금지 — MyBatis TypeHandler 없음)
- Java 배열(`Type[]`) 필드 금지 → `String`(콤마구분) 또는 `List<…>`

### 4.3 mapper_xml (`표준.md §11.2` + `§4.5`)
- **필수 5 statement**: `select{Screen}List`(목록, `<if test>` 필터), `select{Screen}`(단건 PK), `insert{Screen}`(단건), `update{Screen}`(배치 `<foreach>`), `delete{Screen}`(배치 `<foreach>`)
- `namespace="biz.{module}.dao.{Screen}DaoImpl"`
- 페이징 `LIMIT #{pageSize} OFFSET #{pageStart}` (❌`LIMIT #{start}, #{size}`)
- 비교연산자 `<`/`>`/`<=`/`>=` → **CDATA** 필수
- 검색 `ILIKE '%' || #{x} || '%'`, NULL `COALESCE`
- 컬럼은 `snake_col AS "camelField"` 별칭
- `<if test>` 에 쓰는 필드는 **DTO에 실제 존재**해야 함
- 동적쿼리는 `<if test='x != null and x != ""'>` (HQML `<isNotEmpty>` 금지)

### 4.4 dao_impl (`표준.md §4.4`)
- **DAO 인터페이스 생성 안 함**, `implements XxxDao` 사용 안 함
- **bare CRUD 메서드명 금지**: `insert/update/delete/select/selectList/selectOne` 단독 ❌ → 반드시 `insert{Screen}` 식 도메인 접미사
- 메서드명 = Mapper `<statement id>` **정확히 일치**
- 본문은 `super.xxx("statementId", param)` 위임 (base = `AbstractSqlSessionDaoSupport`)

### 4.5 service_impl (`표준.md §4.3·§4.8·§8.1`)
- 모든 public 메서드: `@ServiceId("{Screen}/{methodName}")` + `@ServiceName("한글설명")`
- CUD 메서드: `@Transactional` + `@PreAuthorize("hasAuthority('롤')")`
- 클래스 `@Slf4j`, 시작 `log.debug("Service Method: {}, Param={}", method, param)`
- 예외: `try { … } catch (Exception e) { throw HscException.systemError("메시지", e); }` (**2-arg 필수**)
- **throw 직전 `log.error()`/`log.warn()` 금지** (프레임워크가 로깅)
- DaoImpl의 **wrapper 메서드만** 호출 (bare super 메서드 직접 호출 금지)
- 배치 CUD는 `GridStatus`(INSERTED/UPDATED/DELETED) 필터링

### 4.6 import (`표준.md §10.3·§10.4`)
- `aondev.framework.*` 사용 (❌`hone.bom.*` 레거시)
- `jakarta.*` 사용 (❌`javax.*`)
- **pom.xml에 선언된 패키지만** import
- `org.slf4j.Logger`/`LoggerFactory` 금지 → `@Slf4j`

### 4.7 vue_types (`FrontendGuide/06`)
- 타입은 화면 폴더가 아니라 **`src/api/pages/{module}/{category}/types.ts`** (카테고리 공유)

### 4.8 vue_page (`FrontendGuide/00·02·03·04·07`)
- 경로 `src/pages/{module}/{category}/{screenId}/index.vue` (screenId camelCase), **멀티파일** 구조(`components/` 하위 SearchForm/DataTable/SumGrid 분리)
- `<script setup lang="ts">` (script-only 금지)
- **DataTable2 래퍼** 사용, 컬럼은 **`:columns` prop** (`<Column>` 자식 무시됨 ❌)
- `TableColumn` 타입 필수 필드: `objectId`(=field), `visible: true`, `width: "Npx"`
- `scrollHeight="540px"` + `virtualScrollerOptions` (❌`"flex"`)
- 날짜 포맷은 `getRows()` 전처리 또는 `watch`+`nextTick` (템플릿 슬롯 포맷 ❌)
- `alert()`/`confirm()` 금지 → Toast / ConfirmDialog
- i18n `t('{대컴포넌트명}.{라벨ID}')` (2단계, 화면코드 접두어 ❌)
- API: `api.post('/online/mvcJson/{화면코드}-{메서드}', params)` (GET 금지), 파라미터 camelCase 그대로 전달
- `@ServiceId("{화면코드}/{메서드}")` 와 URL `{화면코드}-{메서드}` **정확히 대응**
- **SearchForm/상태 동기화 핵심 (FrontendGuide 03·08, 가장 틀리기 쉬움)**:
  - searchParams는 index.vue가 보유하고 `provide`, 하위는 `inject` (searchFormRef provide 금지)
  - `watch` 조건은 `if (newVal !== undefined)` — `if (newVal)` 금지 (`null`·`''`도 유효한 필터값)
  - ref 접근은 `xxxRef.value.form.setFieldValue()` — `.value.value.form` 금지 (expose 자동 unwrap)

---

## 5. 자동검증(static_check) 참고

생성 후 코드가 자동 검증/차단하는 항목 (위 규칙을 지키면 통과):
`java.util.UUID`/`randomUUID`, `@Service(빈이름)`, `LoggerFactory`, `HscException.systemError(1-arg)`,
throw 직전 log, bare DAO 메서드 호출, DTO 배열필드, Mapper `javaType=UUID`,
`scrollHeight="flex"`, `<script>`(setup 없음), `alert`/`confirm`,
DAO↔Mapper 바인딩, `<if test>`↔DTO 필드 정합성, 시드 필수테이블/순서.
