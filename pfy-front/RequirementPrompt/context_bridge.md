# 🌉 Context Bridge — AI-Assisted Development Workflow

> **목적**: 각 개발 단계에서 AI에게 전달할 컨텍스트를 표준화한다.
> 각 단계 시작 시, 해당 섹션의 **"AI에게 전달할 프롬프트"** 를 복사하여 사용한다.

---

## 📋 전체 워크플로우 한눈에 보기

```
[0. Setup] → [1. Draft] → [2. Mockup] → [3. Interview]
                                              ↓
                          [7. Verify] ← [6. Build] ← [5. Design] ← [4. Spec]
```

| 단계 | 주요 활동 | 입력 파일 | 출력 파일 |
| :---: | :--- | :--- | :--- |
| **0. Setup** | 프로젝트 기본 원칙 설정 | - | `tech_stack.md` |
| **1. Draft** | 샘플 화면 기획 | `tech_stack.md` | `brief.md` |
| **2. Mockup** | 시각적 피드백 생성 | `brief.md`, `mockupPrompt.md` | `[Name]Mockup.vue` |
| **3. Interview** | 고객 요구사항 구체화 | Mockup 결과물 | `meeting_notes.md` |
| **4. Spec** | 상세 요구사항 확정 | `meeting_notes.md`, `masterPrompt.md` | `spec.md` |
| **5. Design** | DB·API 인터페이스 설계 | `spec.md` | `schema.md`, `api_spec.md` |
| **6. Build** | 코드 자동 생성 | `spec.md`, `schema.md`, `api_spec.md` | FE/BE Source Code |
| **7. Verify** | 동작 검증 | Source Code | `test_case.md` |

---

## 단계별 Context Bridge

---

### ✅ STAGE 0 — Setup

**목표**: 프로젝트 전반에서 AI가 일관된 기술 스택과 컨벤션을 사용하도록 고정한다.

**산출물**: `tech_stack.md`

```
tech_stack.md 포함 항목:
- Frontend: 프레임워크, UI 라이브러리, 상태관리, 스타일
- Backend: 언어, 프레임워크, ORM, DB
- 공통 컨벤션: 네이밍 룰, 폴더 구조, 코드 스타일
- 사용 금지 패턴
```

**AI 프롬프트 (Setup)**
```
아래 기술 스택과 컨벤션을 기반으로 모든 코드를 생성해야 합니다.
이 규칙은 프로젝트 전체에서 변경 없이 적용됩니다.

[tech_stack.md 전체 내용 붙여넣기]
```

---

### ✅ STAGE 1 — Draft

**목표**: 고객 인터뷰 전, AI와 함께 화면 초안을 빠르게 기획한다.

**입력**: `tech_stack.md`
**산출물**: `brief.md`

**AI 프롬프트 (Draft)**
```
프로젝트 기본 정보를 기반으로 brief.md를 작성해 주세요.

## 프로젝트 정보
- 프로젝트명: [입력]
- 목적: [입력]
- 대상 사용자: [입력]
- 핵심 기능 (아는 만큼): [입력]

## 요청
위 정보를 바탕으로 아래 항목을 채운 brief.md를 작성해 주세요.
- userRoles (역할 정의)
- coreFeatures (핵심 기능 3~5개)
- screenList (예상 화면 목록)
- techConstraints (기술 제약)
```

---

### ✅ STAGE 2 — Mockup

**목표**: `brief.md` 기반으로 고객에게 보여줄 시각적 목업을 생성한다.

**입력**: `brief.md`, `mockupPrompt.md`
**산출물**: `[ProjectName]Mockup.vue`

**AI 프롬프트 (Mockup)**
```
아래 지침과 프로젝트 정보를 기반으로 고객 인터뷰용 Vue.js 목업을 생성해 주세요.

## 생성 지침
[mockupPrompt.md 전체 내용 붙여넣기]

## 프로젝트 정보
[brief.md 전체 내용 붙여넣기]
```

---

### ✅ STAGE 3 — Interview

**목표**: 목업을 고객에게 보여주며 요구사항을 구체화하고 `meeting_notes.md`에 기록한다.

**입력**: `[ProjectName]Mockup.vue` (고객에게 시연)
**산출물**: `meeting_notes.md`

> 이 단계는 사람이 직접 진행합니다.
> `interviewNotes.md` 템플릿을 활용하여 실시간 기록 후 `meeting_notes.md`로 저장하세요.

**인터뷰 후 AI 정리 프롬프트**
```
아래 인터뷰 원본 메모를 분석하여 masterPrompt.md의 Customer Input 섹션에 
바로 사용할 수 있는 구조화된 요구사항 요약본을 작성해 주세요.

포함 항목:
- 확정 기능 (Keep)
- 변경 요구 (Change): 화면명 | 현재 | 변경내용
- 추가 요구 (Add): 우선순위 | 기능 설명
- 제외 기능 (Out of Scope)
- 미결 사항 (TBD)

## 원본 메모
[인터뷰 메모 붙여넣기]
```

---

### ✅ STAGE 4 — Spec

**목표**: 인터뷰 결과를 바탕으로 즉시 개발 가능한 `spec.md`를 생성한다.

**입력**: `meeting_notes.md`, `masterPrompt.md`
**산출물**: `spec.md`

**AI 프롬프트 (Spec)**
```
[masterPrompt.md 전체 내용 붙여넣기]

# Customer Input

## 프로젝트 개요
[meeting_notes.md 요약 내용 붙여넣기]

## 확정된 요구사항
[Keep 목록]

## 변경/추가 요구사항
[Change + Add 목록]

## 제외 사항
[Out of Scope 목록]

## 우선순위
- P1: [필수]
- P2: [중요]
- P3: [선택]
```

---

### ✅ STAGE 5 — Design

**목표**: `spec.md`를 기반으로 DB 스키마와 API 명세를 설계한다.

**입력**: `spec.md`, `tech_stack.md`
**산출물**: `schema.md`, `api_spec.md`

**AI 프롬프트 (Schema)**
```
아래 spec.md의 Domain Modeling 섹션을 기반으로 schema.md를 작성해 주세요.

## 기술 스택
[tech_stack.md의 DB 관련 항목]

## 요구사항
[spec.md의 Section 3 (Domain Modeling) 붙여넣기]

## 출력 형식
- ERD (텍스트 형식 또는 Mermaid)
- 테이블 정의서 (컬럼명, 타입, 제약조건, 설명)
- 인덱스 정의
- 초기 데이터 (필요 시)
```

**AI 프롬프트 (API Spec)**
```
아래 spec.md의 API Specification 섹션을 기반으로 api_spec.md를 작성해 주세요.

## 기술 스택
[tech_stack.md의 Backend 관련 항목]

## 요구사항
[spec.md의 Section 5 (API Specification) 붙여넣기]

## 출력 형식
- OpenAPI 3.0 YAML 또는 상세 API 테이블
- Request/Response Schema
- Error Code 정의
```

---

### ✅ STAGE 6 — Build

**목표**: 설계 산출물을 기반으로 FE/BE 코드를 자동 생성한다.

**입력**: `spec.md`, `schema.md`, `api_spec.md`, `tech_stack.md`
**산출물**: FE/BE Source Code

**AI 프롬프트 (Frontend Build)**
```
## 기술 스택 (준수 필수)
[tech_stack.md 전체]

## 요구사항 명세
[spec.md 전체]

## API 명세
[api_spec.md 전체]

## 요청
위 명세를 기반으로 아래 화면의 FE 코드를 생성해 주세요.
- 대상 화면: [화면명]
- 포함 항목: 컴포넌트, API 연동, 상태관리, 유효성 검사
```

**AI 프롬프트 (Backend Build)**
```
## 기술 스택 (준수 필수)
[tech_stack.md 전체]

## 요구사항 명세
[spec.md 전체]

## DB 스키마
[schema.md 전체]

## API 명세
[api_spec.md 전체]

## 요청
위 명세를 기반으로 아래 도메인의 BE 코드를 생성해 주세요.
- 대상 도메인: [도메인명]
- 포함 항목: Entity, Repository, Service, Controller, DTO
```

---

### ✅ STAGE 7 — Verify

**목표**: 생성된 코드의 동작을 검증할 테스트 케이스를 작성한다.

**입력**: Source Code, `spec.md`의 Business Rules
**산출물**: `test_case.md`

**AI 프롬프트 (Verify)**
```
## 비즈니스 규칙
[spec.md Section 4 (Business Logic Rules) 붙여넣기]

## 대상 코드
[검증할 소스코드 붙여넣기]

## 요청
아래 항목을 포함한 test_case.md를 작성해 주세요.

1. **Happy Path**: 정상 시나리오
2. **Edge Case**: 경계값, 빈값, 최대값
3. **Error Case**: 권한 없음, 잘못된 상태 전이, 존재하지 않는 리소스
4. **Business Rule 검증**: spec.md의 각 규칙이 코드에서 검증되는지 확인

출력 형식:
| TC-ID | 분류 | 시나리오 | 입력 | 기대 결과 | 검증 방법 |
```

---

## 🔁 단계 간 핸드오프 체크리스트

각 단계를 완료하기 전 아래를 확인하세요.

| 단계 완료 후 | 확인 항목 |
| :--- | :--- |
| **Setup → Draft** | `tech_stack.md`에 프레임워크, 컨벤션, 금지 패턴이 명시되어 있는가? |
| **Draft → Mockup** | `brief.md`에 userRoles, coreFeatures, screenList가 모두 있는가? |
| **Mockup → Interview** | 목업이 실제로 클릭/전환 동작하는가? 더미 데이터가 충분한가? |
| **Interview → Spec** | `meeting_notes.md`에 Keep/Change/Add/Out/TBD가 구분되어 있는가? |
| **Spec → Design** | `spec.md`의 모든 Entity에 API가 매핑되어 있는가? Enum이 완전한가? |
| **Design → Build** | `schema.md`의 FK가 `api_spec.md`의 Request/Response와 일치하는가? |
| **Build → Verify** | 모든 Business Rule이 코드에서 구현되었는가? |
| **Verify → Done** | 모든 Error Case 테스트가 통과하는가? |

---

## 📁 파일 구조 참고

```
RequirementPrompt/
├── context_bridge.md     ← 이 파일 (단계별 AI 프롬프트 모음)
├── tech_stack.md         ← [Stage 0] 기술 스택 및 컨벤션
├── brief.md              ← [Stage 1] 프로젝트 초안
├── mockupPrompt.md       ← [Stage 2] 목업 생성 AI 지침
├── interviewNotes.md     ← [Stage 3] 인터뷰 기록 템플릿
├── meeting_notes.md      ← [Stage 3] 인터뷰 결과 (실제 작성)
├── masterPrompt.md       ← [Stage 4] Spec 생성 AI 지침
├── spec.md               ← [Stage 4] 상세 요구사항 명세
├── schema.md             ← [Stage 5] DB 스키마
├── api_spec.md           ← [Stage 5] API 명세
└── test_case.md          ← [Stage 7] 테스트 케이스
```
