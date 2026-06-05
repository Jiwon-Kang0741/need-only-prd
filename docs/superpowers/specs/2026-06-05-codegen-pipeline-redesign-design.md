# 코드 생성 파이프라인 재설계 — 설계 문서

- 날짜: 2026-06-05
- 상태: **승인됨 (2026-06-05)** → 구현 계획(writing-plans) 단계로.
- 결정 잠금: **전면 재작성** · **백엔드 스택 Spring Boot 3 / Java 21 / jakarta** (가이드 승) · §8 결정 3개 확정.

---

## 1. 배경 & 목표

`need-only-prd`의 코드 생성 파이프라인(`backend/app/llm/graph/`)을 **가이드 문서가 실제로 요구하는 구조**로 전면 재작성한다. 현재 구조 분석에서 드러난 핵심 문제:

- **규칙이 가이드-주도가 아님.** 경로/패키지는 손으로 베낀 `CODEGEN_RULES.md`(중복본)와 하드코딩 Python이 결정. 가이드를 고쳐도 출력이 안 바뀜.
- **Contract 부재.** `planner`는 가이드를 보지 못한 채 파일을 나열하고, 각 파일이 필드명·PK·메서드명·경로·컴포넌트명을 **따로 지어냄** → cross-file 불일치가 실패의 대부분.
- **`reviewer`는 빈 껍데기** (가이드 컨텍스트 0, 사실상 cross_check만), **`planner`는 가이드를 못 봄**.
- **FE 파일 세트 과소** (2개 + 임시 자식 vs 가이드 요구 ~8–12개).
- **SEED 생성 시점 오류** (Wave1 → 프론트 산출물 예측).

### 설계 원칙 (불변)
1. **가이드 = 고정·읽기 전용 단일 출처.** `pfy_prompt/{BackendGuide,FrontendGuide,DataGuide}` 를 **일절 수정하지 않는다.** 엔진이 있는 그대로 읽는다. (가이드는 외부 소유물이며 버전 스왑될 수 있음.)
2. **규칙 값을 Python에 하드코딩하지 않는다.** 가이드의 *파싱 가능한* 부분(표/순서/Natural Key 등)은 런타임 config로 로드, *prose* 규칙은 프롬프트 컨텍스트로 주입.
3. **Contract-first.** 한 번 해소한 공유 계약을 모든 생성기가 소비 → cross-file drift 제거.
4. **결정론 vs LLM 명확 분리.** 가이드가 기계적인 곳(경로·패키지·namespace·statement-id 배선·감사 매핑·PostgreSQL 문법·Natural Key·시드 순서·pgm_url 공식)은 코드. 판단이 필요한 곳(archetype·ops·타깃테이블·PK추론·필드/컬럼 세트·컴포넌트 필요여부·라벨/메뉴)은 LLM.
5. **컴파일러/검증기가 정답 오라클.** vue/java 규칙을 하드코딩하지 말고 `mvn compile` + `vite build` 의 실제 에러를 fix 루프로 환류.

### 스코프
- **재작성**: 그래프 토폴로지, 노드, 공유 Contract, 규칙/경로 소싱, 파일 세트, 생성 순서, 검증/리뷰.
- **재사용(인프라)**: LangGraph, `gpt55_client`(gpt-5.5 Responses API), SSE 어댑터, `docker_manager`, 프론트 compile-fix 루프.
- **스택 업그레이드**: skeleton → Boot3/Java21/jakarta.
- **삭제**: `pfy_prompt/CODEGEN_RULES.md`.

---

## 2. 목표 아키텍처

```
입력(고정): spec.md + 확정 mockup(vue) + 테이블정보.md + 가이드 3종 + menu_tree.json
        │
 [1] CONTRACT RESOLVER  (LLM 판단 + 결정론 정규화)         ★신설·키스톤
        │   → 단일 Contract (§3 스키마)
        ▼
 [2] FILE PLAN + BINDINGS  (결정론, 코드)                  ★blind planner 대체
        │   경로(BackendGuide §11.4 파싱 + FE resolver + data) · package · namespace
        │   statement-id 집합 · DAO 메서드면(템플릿) · 감사컬럼 매핑 · 파일목록
        ▼
 [3] 레이어 생성 (의존순서 staged; 직전 산출물을 컨텍스트로)
        ├─ DATA-DDL (cptb_*)  ───────────────┐  (백엔드가 컬럼 필요 → 먼저)
        ├─ BACKEND: DTOs → Mapper(키스톤) → DAO(템플릿) → Service
        ├─ FRONTEND: types → API → {DataTable, SearchForm, SumGrid?} → index.vue(맨 마지막)
        └─ DATA-SEED (cmn_*)  ◄──────────────┘  FE vue경로(pgm_url)+컴포넌트명 필요 → 맨 뒤
        ▼   [db/init.sql 조립: DDL → seed(고정순서) → FK ALTER 맨끝]
 [4] 결정론 검증 (가이드 static-check: BE §11.5 / FE 에러패턴 / data §12 + cross-file 바인딩)
        ▼
 [5] COMPILE-IN-THE-LOOP (mvn compile + vite build → 실제 에러 → fix)   ★근본 해법
        ▼
 [6] (선택) Consistency Reviewer — Contract+체크리스트 주입; [4][5]가 못 잡는 의미 불일치만
```

### 노드 매핑 (LangGraph)
- `contract_resolve` (LLM) → `plan_and_bind` (det) → 의존순서 라우팅
- 생성 노드: `gen_ddl`, `gen_dto`, `gen_mapper`, `gen_dao`(템플릿), `gen_service`, `gen_fe_types`, `gen_fe_api`, `gen_fe_component`(fan-out), `gen_fe_index`, `gen_seed`, `assemble_sql`(det)
- `validate`(det) → `compile_loop` → `reviewer`(선택) → END

---

## 3. Contract 스키마 (키스톤 산출물)

`contract_resolve`가 생성하고 `plan_and_bind`가 결정론 필드를 채운다. 모든 생성기는 이 객체만 본다.

```jsonc
{
  "identity": {
    "module": "edu", "category": "pondg", "screenId": "cpmsEduPondgLst",
    "className": "CpmsEduPondgLst",        // PascalCase = {ClassName}/{Screen}/{ScreenCode}
    "programId": "CPMSEDUPONDGLST",        // SPEC #1 verbatim (lbl_cd 접두 SSOT)
    "windowId": "...", "menuId": "...", "pMenuId": "ROOT.."
  },
  "archetype": "list | list-detail | edit | popup | tab-detail",
  "ops": ["selectList","selectCount","selectOne","insert","update","delete"],
  "table": {
    "name": "cptb_...",
    "pk": ["..."],                          // 추론 (테이블정보.md PK 비어있음)
    "columns": [{
      "snake":"emp_nm","camel":"empNm","dbType":"varchar(100)","javaType":"String",
      "pk":false,"nullable":true,"searchable":true,"audit":false,
      "code": null                          // cls_id if common-coded → *_nm 미저장(JOIN)
    }]
  },
  "fields": {
    "request":  [{"camel":"empNm","snake":"emp_nm","javaType":"String","optional":true,"filter":"ILIKE"}],
    "response": [{"camel":"empNm","snake":"emp_nm","javaType":"String","isStatus":false}]
    // page/size(req) · 감사필드(res)는 base 제공 → 재선언 금지
  },
  "api": [{
    "method":"selectList","serviceId":"CpmsEduPondgLst/selectList",
    "url":"/online/mvcJson/CpmsEduPondgLst-selectList",
    "reqDto":"CpmsEduPondgLstReqDto","resDto":"CpmsEduPondgLstResDto",
    "authority":"..." }],
  "frontend": {
    "components": ["SearchForm","DataTable"],          // SumGrid/ProgressList 조건부
    "searchFields": [...],
    "columns": [{"field":"empNm","header":"...","width":"140px","align":"left","isDate":false,"isNumber":false,"frozen":false}],
    "commonCodeLoad": "ensureLoaded|ensureLoadedMulti|loadMulti"
  },
  "seed": {
    "labels": [{"programId":"...","component":"SearchForm","labelId":"searchDate","text":"조회일자","langCd":"ko-KR"}],
    "menu": {"menuId":"...","pMenuId":"...","menuNm":"...","sort":1,"roles":["DEV_AUTO", ...]},
    "commonCodes": [{"clsId":"...","clsNm":"...","codes":[{"codeCd":"S01","codeNm":"..."}]}], // SPEC #10.3 있을 때만
    "pgmUrl": "pages/edu/pondg/cpmsEduPondgLst/index.vue"   // FE 경로에서, 앞 슬래시 없음(§16.1)
  },
  "bindings": {                              // [2]가 결정론으로 채움
    "statementIds": ["selectCpmsEduPondgLstList", ...],
    "daoMethods":   ["selectCpmsEduPondgLstList", ...],   // == statementIds
    "namespace": "biz.edu.dao.CpmsEduPondgLstDaoImpl",
    "packages": {"dto_request":"biz.edu.dto.request", "...": "..."},
    "auditMap": {"fstCrtrId":"insert_uid","fstCretDtm":"insert_dt","lastMdfrId":"update_uid","lastMdfcDtm":"update_dt"},
    "paths": {"dto_request":"src/main/java/biz/edu/dto/request/CpmsEduPondgLstReqDto.java", "...":"..."},
    "files": [{"type":"...","path":"...","layer":"..."}]
  }
}
```

---

## 4. 규칙 & 경로 소싱 (가이드 수정 0)

### 4.1 파싱 가능 → config 로더 (read-only)
- **BackendGuide**: §11.4 경로표, §4.2 패키지표, §4.4.3 DAO 패턴표, §4.7 감사 매핑, §3.x 네이밍, §11.2/§11.5/§11.6, `테이블정보.md`(6열 표).
- **DataGuide**: §5 Natural Key 표, §3/§14 시드 순서, §2 시드 테이블, §3 타입맵, §5 감사, §6 soft-delete, §10 기본값.
- 로더는 가이드의 표/번호목록을 파싱해 dict로. 가이드 스왑 시 코드 수정 없이 반영.

### 4.2 prose → 컨텍스트 주입
- BE §4.3/§4.4/§4.5/§4.8/§8.1(try-catch·2-arg HscException·flat DTO·bare-CRUD 금지 등), FE 전반, DataGuide §16.x 는 prose → 해당 생성 노드 프롬프트에 레이어 가이드로 주입(현 `load_guide_for_file_type` 계승, file_type별 `##`/`###` 선별 검토).
- **FE §13 공통컴포넌트 카탈로그는 "가이드보다 우선"** → 항상 주입.

### 4.3 경로 resolver (코드)
- 입력 `(module, category, screenId, className)`.
- **백엔드/데이터**: §11.4 표 파싱 결과 + `{module}`/`{ClassName}` 치환.
- **프론트**: 코드 resolver — `[x]`/`{x}` 토큰 정규화 + camelCase→PascalCase 파일명 변환 + 소문자 예외(`index.vue`, `utils/index.ts`, `types.ts`) + `api/pages/.../types.ts`(카테고리 공유)·`api/pages/.../[screenId].ts` 분리.
- 가이드 예시(`pmdp020`, `spov010`, `cpmsEduPondgLst`)를 **golden test**로 고정.

### 4.4 `CODEGEN_RULES.md` 삭제
- 경로 → resolver/§11.4 파싱. 스파인 → 레이어 가이드 통째 주입(이미 동작). 수기 중복본 제거.

---

## 5. 레이어별 생성 설계

### 5.1 백엔드 (순서 BE §11.3, staged)
DTOs → **Mapper(키스톤: statement-id 집합 + `AS "camel"` 매핑 정의)** → DAO → Service.
- **DTO**: Req(`extends SearchBaseDto`)+Res(`extends AuditBaseDto`) 한 패스. page/size·감사필드 재선언 금지, 날짜=String, flat-only, no-UUID/array.
- **Mapper**: 5필수 statement, namespace=bindings, PostgreSQL(ILIKE/COALESCE/LIMIT..OFFSET), CDATA, `AS "camel"`, `<if test>` 필드는 DTO 존재 보장.
- **DAO(템플릿)**: §4.4.3 표 기반 **결정론 템플릿 생성**(메서드=statement-id, `super.xxx` 위임). LLM 최소화/불필요.
- **Service**: `@ServiceId/@ServiceName/@Transactional/@PreAuthorize`, try/catch + `HscException.systemError(msg,e)`(2-arg), throw 전 log 금지, DaoImpl wrapper만 호출, GridStatus 필터.
- **jakarta** import (Boot3). bindings의 package/namespace로 grounding.

### 5.2 프론트 (types-first, index.vue-last, plan-driven)
types.ts → API `[screenId].ts` → {DataTable(utils+vue+scss), SearchForm(vue+scss), SumGrid?} → **index.vue 마지막**(실제 자식 props/emits에 바인딩).
- 파일세트는 [2]의 file plan이 결정(SumGrid 조건부, ProgressList는 명시 요청시만).
- DataTable2 `:columns`+`TableColumn`(objectId=field, visible, width px), `scrollHeight="540px"`+virtualScroller, 날짜 `getRows()` 전처리, no alert/confirm, i18n 2단계 `t('{대컴포넌트}.{라벨}')`, watch `!== undefined`, ref `.value.form`, provide/inject(searchParams), `api.post`.

### 5.3 데이터 (DDL 먼저 / SEED 맨 뒤 / 결정론 조립)
- **DDL(cptb_*)**: 이른 단계. PostgreSQL 타입(BIGSERIAL/boolean/timestamptz), `del_yn`(§6), 감사컬럼 강제, `*_nm` 미저장(JOIN), FK는 맨끝 ALTER, CASCADE 금지.
- **SEED(cmn_*)**: **프론트 뒤.** Natural Key upsert(MERGE 금지), 시드 7표 고정순서, `lbl_cd={programId}.{component}.{labelId}`, **`pgm_url`은 실제 FE 경로에서, 앞 슬래시 없음(§16.1)**, menu_id/menu_sort 공식, DEV_AUTO 항상, ROOT98 fallback, cmn_class/code는 SPEC #10.3 있을 때만.
- **assemble_sql(결정론)**: DDL → seed(순서) → FK ALTER 로 한 파일 조립.

---

## 6. 검증 / 컴파일 루프 / 리뷰어

- **[4] 결정론 검증**: 가이드 static-check 목록을 1:1 구현 — BE §11.5(UUID/bare-CRUD/HscException/log-before-throw/DTO array/Mapper UUID), FE 에러패턴(scrollHeight flex/Column children/objectId/alert/confirm/script-setup/primevue 직접 import/t 2단계/api.post), data §12(pgm_url 앞슬래시 없음 등). **cross-file 바인딩**: statement-id↔DAO 메서드, namespace, props↔index.vue usage, URL↔ServiceId, types import 경로.
- **[5] compile-in-the-loop**: backend `mvn compile` + frontend `vite build` → 실제 에러 파싱 → fix 노드(gpt55) → 재시도(`DOCKER_MAX_FIX_RETRIES`). 프론트는 기존 `frontend_build_fix.py` 계승, 백엔드용 신설.
- **[6] reviewer(선택)**: 현 빈 껍데기 폐기. 대신 **Contract+가이드 체크리스트**를 주입해 [4][5]가 못 잡는 *의미* 불일치(라벨↔컴포넌트, 권한 누락 등)만 검토. 없어도 [4][5]로 정합성 보장.

---

## 7. skeleton Boot3 업그레이드

- `pom.xml`: parent `spring-boot-starter-parent` 3.x, `java.version` 21, `javax.*`→`jakarta.*` 의존(validation 등), WAR/포트 등 §1.1 정렬.
- vendored 프레임워크(`aondev.framework.*`, `com.common.*`)를 jakarta로 정렬, `javax.*` import 제거.
- `application.yml`/Dockerfile JDK21 베이스.
- 기존 PostgreSQL/`biz.*` 정렬은 유지. 목표: assembled skeleton + 생성물 → `mvn compile` BUILD SUCCESS (jakarta).

---

## 8. 확정된 결정 (2026-06-05 승인)

1. **Soft-delete** = `del_yn CHAR(1) NOT NULL DEFAULT 'N' CHECK (del_yn IN ('Y','N'))` (BE §11.6 + DataGuide §6). `cmn_role_menu`/`cmn_role_pgm` 매핑표는 하드삭제 예외(§6). `deleted_at`(§4.8)·하드DELETE(§4.5)는 **비채택**.
2. **pgm_url** = 앞 슬래시 없는 `pages/...` (가이드 §16.1 승). 현 `cpms_checks.py:49`의 `/pages/` 요구는 **버그 → 수정**.
3. **DAO 생성** = §4.4.3 표 기반 **순수 결정론 템플릿**(LLM 미사용). 매핑 불가한 예외 op만 LLM fallback.
4. **DataGuide 검증기**: pgm_url 포함, 시드 검증 전반을 §12/§16에 맞춰 재작성.

---

## 9. 빌드 & 테스트 전략 (TDD)

- 전면 재작성이지만 **항상 그린 유지**: 노드 단위 RED→GREEN, 그래프 통합 테스트, e2e(real gpt-5.5 1회 스모크 + assembled `mvn compile`/`vite build`).
- 경로 resolver는 가이드 예시 golden test로 고정.
- Contract 스키마는 JSON Schema로 검증(생성 노드 입력 계약).
- 기존 232 테스트 중 재사용 가능한 것 이식, 나머지 신규.

## 10. 리스크
- gpt-5.5 거부/비코드 출력 → sanity 가드(빈/너무짧음/거부 감지 → 재생성) 필요.
- 테이블정보.md PK 부재 → PK 추론 품질이 Mapper/DAO 정확도 좌우.
- Boot3 업그레이드가 vendored 클래스/스켈레톤 회귀 유발 가능 → 컴파일 게이트로 차단.
- prose 파싱 의존부는 가이드 스왑 시 취약 → 가능한 한 §표 파싱 + golden test로 방어.

## 11. 아웃 오브 스코프
- spec 파이프라인(요구사항 추출·spec 생성)은 변경 없음.
- 런타임 부팅 검증(`docker compose up`)은 별도(컴파일/빌드까지만 본 설계 범위).

## 12. Phase-1 완료 & Phase-2 입력 (2026-06-05)

**Phase-1 DONE** (브랜치 `feat/codegen-rewrite`, 커밋 `2f79a49`..`30dfde8`): `guide_config.py`(고정 가이드 read-only 파서: §11.4 경로표·DataGuide §5 Natural Key·시드 순서) + `paths.py`(`Identity` + 백엔드 경로[§11.4 템플릿] + 프론트 경로 resolver[golden test] + `data_path`). 순수 추가, 라이브 그래프 미변경, 전체 비-LLM 테스트 259 green.

**Phase-2 착수 전 결정/주의 (final review 도출):**
- **O1 (결정 필요):** `Identity`는 `module`·`category`를 명시 입력으로 요구하는데, 현 `CONTRACT_SYSTEM`은 `screen:{id,name,type}`만 추출함. Phase-2 Contract Resolver가 (a) 계약 JSON에 `module`/`category`를 LLM이 출력하게 하거나 (b) 화면코드 prefix에서 결정론 파생(구 `naming.screen_segments` 류)할지 정해야 함.
- **O2:** `ProgressList`는 12개 FrontendGuide 문서엔 없고 `cursor/rules/MigFrontend.mdc`에만 있음 → Phase-2 fixture가 항상 등장한다고 가정 금지(명시 요청 시만).
- **O3:** 신·구 경로 시스템 공존. 구 `naming.file_path`(CODEGEN_RULES.md `{Screen}`, `screen_segments` 기반 FE 경로)는 라이브 파이프라인용으로 Phase-6까지 잔존. **Phase-2 신규 노드는 오직 `paths.*`만 호출**하고, 구 시스템과 섞지 말 것. FE 경로는 구(`{module}/{screen}/{Pascal}`) vs 신(`{module}/{category}/{camel}`)이 구조적으로 다르며 **신 시스템이 정답**.

## 13. Phase-2 완료 & Phase-3/4 입력 (2026-06-05)

**Phase-2 DONE** (커밋 `b43a16f`..`4e471fb`): `contract_schema.py`(pydantic Contract, archetype/filter Literal 제약), `contract_resolve.py`(LLM 노드 — 검증+1회 재시도, page_type override 검증前·schema-derived 유효집합, 거부 진단, module/category O1), `plan_and_bind.py`(결정론 bindings: 경로/statement-id·dao(1:1)/namespace/package/file-plan; unknown-op 거부; files 리스트 aliasing 수정). 순수 추가, 라이브 그래프 미변경. 전체 비-LLM **289 green**(29 Phase-2 신규).

**Phase-3 readiness:** Phase-3(skeleton Boot3/Java21/jakarta)는 contract를 소비하지 않음 → Phase-2 블로커 없음.

**Phase-4 착수 전 보완 (final review 도출 — Phase-4 백엔드 생성기가 bindings/contract 소비 시 반영):**
- **ApiSig에 `service_name` 부재.** §8.1은 모든 public 메서드에 `@ServiceName("한글설명")` 필수 → `ApiSig.service_name: str` 추가 또는 spec/service_id에서 파생 결정 필요(service_impl 생성기 작성 전).
- **`FrontendPlan.columns: list[dict]`(무타입)** → 컬럼 dict 형태(header/field/sortable…)를 Phase-4 프론트 생성기가 알아야 함. `FrontendColumn` 모델화하면 후속 스키마 마이그레이션 회피.
- **`popup` archetype이 `naming._SCREEN_OPS`에 없음** → ops=[] + popup이면 fallback이 `["selectList","count"]` 생성(아마 CPMS 팝업=읽기전용 그리드로 맞지만 미문서화). `_SCREEN_OPS`에 popup 명시 또는 주석.
- **확정 지연 갭(정상):** `bindings.audit_map`=Phase-4(Mapper 생성), `seed.pgm_url`=Phase-6(프론트 산출물 필요).
- **I3(지연):** `Contract.ops`는 Literal 미제약 — 잘못된 op는 `plan_and_bind`가 `naming._OP_TABLE` 단일출처로 거부(중복 회피 위해 schema Literal 미적용). 그래프 배선(Phase-6) 시 SSE 이벤트 순서와 함께 재검토.
- **잔여 노트:** `plan_and_bind`의 file-plan 리스트는 복사하지만 내부 **dict 엔트리는 공유 참조** — 현재 in-place 변경 노드 없어 무해, Phase-6 배선 시 엔트리 변경하면 복사 필요.
