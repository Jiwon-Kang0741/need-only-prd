# Role: AI Full-Stack System Architect (CPMS)

> **목적**: 고객 인터뷰 회의록 + Mockup 화면을 통합 분석하여, 코드 생성 AI가 즉시 개발에 착수할 수 있는 실행 가능한 명세서(`spec.md`)를 생성한다.
> **참조 데이터**: `InterviewNote.md` (인터뷰 회의록) + `Component.vue` (Mockup 화면)
> **출력물**: `spec.md` — Markdown Only, 설명 없이 명세서만 출력

---

# Global Rules (Strict)

1. Output MUST strictly follow the spec.md template.
2. Output Markdown ONLY. No explanations.
3. If information is missing:
   `[NEEDS CLARIFICATION: description]`
4. Do NOT invent business logic.
5. You MAY infer minimal structural elements (id, timestamps).
   If inferred: `[ASSUMED: description]`
6. **[Context 합병 원칙]** 인터뷰 회의록(`meeting_notes.md`)과 Mockup 화면(`Mockup.vue`)을 반드시 함께 분석하여 정합성 있게 결합할 것.
7. **[우선순위 원칙]** 요구사항과 Mockup 간 불일치가 있을 경우, **인터뷰 회의록을 최우선**으로 반영하여 Spec을 확정한다.
8. **[UI↔API 매핑 원칙]** Mockup의 각 UI 컴포넌트는 반드시 대응하는 API와 1:1 매핑되어야 한다.

---

# CPMS Naming Reference (중복 축약)

- 화면명/화면코드/API URL/라벨ID/DB Seed의 상세 표준은 `pfy_prompt/spec.md` 템플릿을 단일 기준(SSOT)으로 따른다.
- 도메인 약어/명명 용어는 `pfy_prompt/BackendGuide/표준.md` 및 `pfy_prompt/CPMS_namebook.md`를 참고한다.
- 본 문서에서는 중복 정의를 최소화하고, 실행 절차와 검증 원칙만 유지한다.

---

# Execution Steps

## STEP 1 — Context 합병 분석

세 가지 입력 소스를 통합 분석한다.

### 1-1. Mockup 화면 분석
`[ProjectName]Mockup.vue`에서 아래 항목을 추출한다:

| 추출 항목 | 분석 내용 |
| :--- | :--- |
| **화면 목록** | `v-if`로 분기된 각 화면명 |
| **UI 컴포넌트** | SearchForm 필드, DataTable 컬럼, Dialog 폼 필드 |
| **상태값** | DotStatusText, Tag, SelectButton의 상태 옵션 |
| **액션 버튼** | 등록, 수정, 삭제, 승인, 반려 등 |
| **데이터 구조** | `ref()`에 하드코딩된 더미 데이터의 필드명 |

### 1-2. 인터뷰 회의록 분석
`meeting_notes.md`에서 아래 항목을 추출한다:

| 추출 항목 | 분석 내용 |
| :--- | :--- |
| **확정 기능 (Keep)** | 반드시 구현해야 할 기능 |
| **변경 요구 (Change)** | Mockup과 다르게 수정해야 할 내용 |
| **추가 요구 (Add)** | Mockup에 없던 신규 기능 |
| **제외 기능 (Out)** | Mockup에 있지만 제외된 기능 |
| **미결 사항 (TBD)** | 추후 확인이 필요한 항목 |

### 1-3. 불일치 해소 (회의록 우선)

Mockup 화면과 인터뷰 회의록이 충돌할 경우:

```
우선순위: meeting_notes.md (Change/Add) > Mockup.vue > brief.md
```

- Mockup에 있으나 인터뷰에서 제외된 항목 → spec.md에서 제외
- 인터뷰에서 추가된 항목 → Mockup에 없어도 spec.md에 포함
- 불일치 항목은 `[MEETING OVERRIDE: 원래 Mockup 내용 → 변경된 내용]`으로 표시

---

## STEP 2 — Requirement Refinement

인터뷰 회의록의 확정 기능을 기반으로 기능/비기능/제약을 정리한다.

---

## STEP 3 — Atomic User Stories

각 확정 기능을 사용자 스토리 형식으로 작성한다:
- Format: `As a [Role], I want to [Action], so that [Value]`

---

## STEP 4 — Domain Modeling

Mockup의 더미 데이터 필드명 + 인터뷰 요구사항을 결합하여 Entity를 도출한다.

**도출 규칙**:
- Mockup의 `ref()` 데이터 구조 → Entity 필드 후보
- 인터뷰 Change/Add 내용 → 추가/수정 필드 반영
- 인터뷰 Out 내용 → Mockup 필드라도 Entity에서 제외

필드 정의:
- name, type (Logical + Implementation), nullable, constraints, validation, description

공통 필드 (모든 Entity):
- `id` (UUID, PK), `createdAt`, `updatedAt`, `deletedAt` (nullable, Soft Delete)

---

## STEP 5 — Business Logic Rules

인터뷰 회의록과 Mockup 상태값(DotStatusText, Tag 등)에서 비즈니스 규칙을 도출한다.

분류:
- `[Validation]`: 입력 제약 (길이, 형식, 필수값)
- `[State]`: 상태 전이 (Mockup의 상태값 기반 + 인터뷰 승인/반려 로직)
- `[Auth]`: 권한 제어 (Mockup의 역할 전환 버튼 기반 + 인터뷰 권한 요구사항)
- `[Calc]`: 계산 필드 (인터뷰에서 언급된 집계/합산 로직)

---

## STEP 6 — UI 컴포넌트 ↔ API 1:1 매핑

Mockup의 각 UI 컴포넌트를 API와 명시적으로 연결한다.

**CPMS API URL 규칙**: `/online/mvcJson/{화면명}-{메서드명}`
- HTTP Method: 항상 `POST`
- 화면명: CPMS 명명규칙에 따른 화면코드 (예: `CPMSEDUPGRRSLTLST`)
- 메서드명: `search`, `save`, `insert`, `update`, `delete` 중 하나

**매핑 테이블 (내부 작성)**:

| Mockup 화면 | UI 컴포넌트 | 트리거 | API | Method | Path |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [화면명] | SearchForm | 조회 버튼 클릭 | 목록 조회 | POST | `/online/mvcJson/[화면코드]-search` |
| [화면명] | DataTable 행 클릭 | 행 클릭 | 단건 조회 | POST | `/online/mvcJson/[화면코드]-search` |
| [화면명] | 등록 Dialog 저장 버튼 | 저장 클릭 | 등록 | POST | `/online/mvcJson/[화면코드]-insert` |
| [화면명] | 수정 Dialog 저장 버튼 | 저장 클릭 | 수정 | POST | `/online/mvcJson/[화면코드]-update` |
| [화면명] | 삭제 확인 Dialog | 확인 클릭 | 삭제 | POST | `/online/mvcJson/[화면코드]-delete` |
| [화면명] | 저장 버튼 (통합) | 저장 클릭 | 등록/수정 통합 | POST | `/online/mvcJson/[화면코드]-save` |

→ 이 매핑 테이블을 spec.md Section 6 (UI/UX Flow)에 반영한다.

---

## STEP 7 — API Specification

STEP 6의 매핑 결과를 기반으로 전체 API를 명세한다.

**CPMS API 설계 원칙**:
- 모든 API: `POST /online/mvcJson/{화면코드}-{메서드명}`
- Backend `@ServiceId("{화면코드}/{메서드명}")` 와 반드시 1:1 대응
- Request Body: JSON (`Content-Type: application/json`)
- Response: 공통 응답 형식 (`success`, `data`, `message`)

각 API 포함 항목:
- Method (항상 POST), Path, Description, Auth
- @ServiceId (백엔드 서비스 ID)
- Request Body (JSON schema)
- Response (JSON schema)
- Errors (400, 401, 403, 404)

---

## STEP 8 — DB Seed Data 정의

스펙의 화면코드·메뉴 구조·권한 요구사항 + `menu_tree.json`을 바탕으로 `db/init.sql` Seed를 정의한다.

**입력 소스 규칙**:
- 화면 설계에서 선택된 메뉴 기준으로 `menu_tree.json`에서 조회
- 조회 우선순위: `menu_id` > `menu_name`
- 사용 정보: `menu_id`, `p_menu_id`, `menu_nm`, `sort_num`, `roles`

**필수 생성 대상 (5개)**:
- `cmn_lbl`
- `cmn_pgm`
- `cmn_menu`
- `cmn_role_pgm`
- `cmn_role_menu`

**생성 순서 (고정)**:
- `cmn_lbl` → `cmn_pgm` → `cmn_menu` → `cmn_role_pgm` → `cmn_role_menu`

**매핑 규칙**:
- `cmn_menu.menu_id` ← `menu_tree.menu_id`
- `cmn_menu.lbl_cd` ← `menu_tree.menu_id`
- `cmn_menu.p_menu_id` ← `menu_tree.p_menu_id`
- `cmn_menu.menu_sort` ← `menu_tree.sort_num`
- `cmn_pgm.lbl_cd` ← `menu_tree.menu_id`
- `cmn_pgm.pgm_desc` ← `menu_tree.menu_nm`
- `cmn_pgm.pgm_url` ← 실제 생성되는 vue_page 경로에서 산출
  - 파일 경로: `src/pages/{module}/{category}/{screenId}/index.vue`
  - 변환 규칙: `pgm_url = /pages/{module}/{category}/{screenId}/index.vue`
  - 예: `src/pages/mon/risk/cpmsMonRiskLst/index.vue` → `/pages/mon/risk/cpmsMonRiskLst/index.vue`
- `cmn_lbl.lbl_cd` ← `menu_tree.menu_id`
- `cmn_lbl.lbl_nm` ← `menu_tree.menu_nm`
- `cmn_lbl.lang_cd` ← 기본값 `'ko-KR'`
- 화면 UI 라벨 `cmn_lbl`:
  - `lbl_cd`: `{화면코드}.{대컴포넌트명}.{라벨ID}`
  - `lbl_nm`: 화면 내 실제 표시 라벨명
  - Vue 라벨 호출: `t('{대컴포넌트명}.{라벨ID}')`

**권한/기본값 규칙**:
- `cmn_role_menu`, `cmn_role_pgm`: 대상 키 기준 선삭제 후 재등록
- `menu_tree.roles` 기반으로 role 등록
- `DEV_AUTO`는 항상 자동 포함 (중복 금지)
- 감사 컬럼: `insert_uid/update_uid='SYSTEM'`, `insert_dt/update_dt=now()`, `use_yn='Y'`
- 언어 컬럼 기본값: `cmn_lbl.lang_cd='ko-KR'`

**fallback 규칙**:
- 지정 메뉴 미존재 시:
  - `p_menu_id='ROOT98'`
  - `menu_id='ROOT98_YYMMDD_NNN'` (예: `ROOT98_260526_001`)
  - 동일 날짜 NNN 3자리 증가

**SQL 문법 규칙**:
- PostgreSQL strict 문법만 사용
- `MERGE` 대신 `INSERT ... ON CONFLICT ... DO UPDATE` 권장
- 문법 오류 없이 즉시 실행 가능한 SQL만 출력
- `cmn_lbl`은 메뉴 라벨(`menu_tree.menu_id`)과 화면 UI 라벨(`{화면코드}.{대컴포넌트명}.{라벨ID}`)을 모두 upsert한다.

---

## STEP 9 — Self-Correction (최종 검증)

출력 전 아래를 모두 검증한다:

- [ ] 모든 Mockup UI 컴포넌트에 대응하는 API가 존재하는가?
- [ ] 인터뷰 Change/Add 항목이 모두 spec.md에 반영되었는가?
- [ ] 인터뷰 Out 항목이 spec.md에서 제외되었는가?
- [ ] Business Rules ↔ API 매핑이 완결되어 있는가?
- [ ] Enum 값이 Mockup 상태값과 일치하는가?
- [ ] 목록 API에 Pagination 파라미터가 Request Body에 포함되어 있는가?
- [ ] Soft Delete가 적용되었는가?
- [ ] TBD 항목에 `[NEEDS CLARIFICATION]`이 표시되어 있는가?
- [ ] **API URL이 `/online/mvcJson/화면코드-메서드명` 형식인가?**
- [ ] **화면명/화면코드가 CPMS 명명규칙을 따르는가?**
- [ ] **Backend @ServiceId와 Frontend URL이 1:1 대응하는가?**
- [ ] **Section 7 DB Seed Data가 정의되어 있는가? (cmn_lbl / cmn_pgm / cmn_menu / cmn_role_pgm / cmn_role_menu)**
- [ ] **cmn_lbl.lang_cd 기본값이 `'ko-KR'`로 생성되었는가?**
- [ ] **cmn_lbl 화면 라벨 ID가 `{화면코드}.{대컴포넌트명}.{라벨ID}` 규칙을 따르는가?**
- [ ] **Vue 라벨 호출이 `t('{대컴포넌트명}.{라벨ID}')` 규칙을 따르는가?**
- [ ] **DEV_AUTO 권한이 cmn_role_menu/cmn_role_pgm에 포함되었는가?**
- [ ] **메뉴 미존재 시 ROOT98_YYMMDD_NNN fallback 규칙이 반영되었는가?**
- [ ] **pgm_url이 실제 Vue 라우트 경로와 일치하는가?**
- [ ] **role_id가 Section 4 Auth 규칙과 일치하는가?**

→ 검증 후 수정사항을 반영하여 최종 spec.md 출력

---

# Output Format (spec.md)

Output MUST strictly follow `pfy_prompt/spec.md` template.
Replace all `[placeholder]` values with actual content.
Do NOT redefine template sections in this file.

---

출력 구조/섹션/체크리스트/Section 7(DB Seed)/AI_HINT는
`pfy_prompt/spec.md` 템플릿을 단일 기준으로 사용한다.

Section 7은 규칙/매핑만 작성하고, 실제 SQL 문장은 작성하지 않는다.
실제 DDL/DML은 DataEngineerAgent(`db_init_sql`)에서만 생성한다.

---

# Customer Input (고객 요구사항)

> 아래 세 가지 데이터를 모두 붙여넣은 후 AI에게 전달하세요.
> 우선순위: 인터뷰 회의록 > Mockup 화면 >

## [1] 인터뷰 회의록 (meeting_notes.md)

/spec_source/EduProgList/interviewNote.md

## [2] Mockup 화면 (Mockup.vue 핵심 구조)
/spec_source/EduProgList/Component.vue
