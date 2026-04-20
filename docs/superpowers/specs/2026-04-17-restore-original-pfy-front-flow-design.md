# 원본 pfy-front 플로우 복원 설계

> 현재 Mockup 탭의 6단계 파이프라인을 원본 pfy-front의 4단계 플로우(Brief → Mockup → Interview → Spec)로 교체한다. LLM이 Vue 코드를 생성하는 방식으로 돌아가고, 하나의 Vue 파일에 v-if 기반 여러 화면을 포함하는 원본 구조를 따른다.

## Context

원본 pfy-front는 "PM이 고객 인터뷰를 준비하는 도구"로 설계되어 있다: 5분 안에 `brief.md` 작성 → LLM이 전체 화면 Mockup 생성 → 고객과 대면 인터뷰 → 녹취를 `interviewNotes.md`로 구조화 → 최종 `spec.md` 생성.

현재 need-only-prd의 Mockup 탭은 단일 화면 중심의 자동화된 6단계 파이프라인으로 구현되어 있어 원본의 맥락 수집력(`brief.md`의 프로젝트 전체 정보, 실제 고객 인터뷰 원천 데이터)을 잃었다. 본 설계는 원본 플로우를 복원하면서 현재 아키텍처(탭 UI, iframe 미리보기, Zustand 스토어)는 유지한다.

## 설계 결정 요약

| 항목 | 결정 |
|------|------|
| 기존 Mockup 탭 처리 | 완전 대체 (6단계 → 4단계) |
| brief 입력 방식 | 템플릿 프리필 textarea (원본 방식 그대로) |
| Mockup 생성 방식 | LLM이 Vue 생성 (`mockupPrompt.md` 준수), Python 템플릿 제거 |
| 인터뷰 방식 | 원본 방식 — 원천 텍스트 붙여넣기만 (AI 질문 자동 생성 제거) |
| UI 단계 수 | 4단계 스텝퍼 (Brief/Mockup/Interview/Spec) |
| 다중 화면 미리보기 | 단일 Vue 파일 + 내부 `v-if` 전환 (원본 mockupPrompt 규칙) |
| 원본 리소스 경로 | `/Users/g1_kang/Downloads/pfy-front/` |

---

## 1. 전체 아키텍처

```
┌─ Frontend (React) ────────────────────────────────────────────┐
│  SpecModeSelector 탭                                            │
│  ├ 텍스트 입력 (기존)                                           │
│  └ Mockup 생성 (4단계 스텝퍼, 원본 복원)                          │
│    ①Brief → ②Mockup → ③인터뷰 → ④Spec                         │
│  공통: SpecViewer → ChatPanel → CoverageScore → CodeGenPanel    │
└────────────────────────────────────────────────────────────────┘
         │
         ▼  /api/*
┌─ Backend (FastAPI) ───────────────────────────────────────────┐
│  신규/대체: /api/mockup/*                                       │
│    POST /brief              — brief.md 세션 저장               │
│    POST /generate-mockup    — SSE: Vue SFC 스트리밍             │
│    POST /parse-interview    — InterviewNote 생성                │
│    POST /generate-spec      — SSE: spec.md 스트리밍             │
│    POST /reset              — MockupState 초기화                │
│  공통: session, llm_client (gpt-5.4)                            │
└────────────────────────────────────────────────────────────────┘
         │
         ▼ 파일 쓰기 (Vue 생성 완료 시)
┌─ pfy-front (Vue Runtime) ─────────────────────────────────────┐
│  src/pages/generated/{PROJECT_ID}/index.vue — v-if 전환 포함    │
│  src/router/staticRoutes.ts — /{PROJECT_ID} 자동 등록           │
│  Vue dev server hot-reload → iframe 미리보기                    │
└────────────────────────────────────────────────────────────────┘
```

**핵심 원칙**:
- 두 탭 모두 최종 결과는 `session.spec_markdown`에 저장 → 기존 SpecViewer/ChatPanel/CodeGenPanel 재사용
- `session.spec_source = "mockup"`, `session.mockup_state`의 내부 구조만 교체
- Mockup은 하나의 Vue 파일에 `v-if` 기반 여러 화면 포함
- iframe 미리보기는 단일 URL 고정 (`/{PROJECT_ID}`), 화면 전환은 Vue 내부 버튼

---

## 2. 백엔드 설계

### 2.1 파일 구조 변경

```
backend/app/
├── llm/
│   ├── mockup_pipeline.py      # [대체] 4단계 오케스트레이션
│   ├── mockup_prompts.py       # [대체] brief/mockupPrompt/InterviewParser 포팅
│   └── vue_generator.py        # [삭제] LLM이 생성하므로 불필요
├── routers/
│   └── mockup.py               # [대체] 5개 엔드포인트로 교체
└── models.py                   # [수정] MockupState 재정의
```

### 2.2 세션 모델 재정의

```python
from pydantic import BaseModel, ConfigDict

class MockupState(BaseModel):
    project_id: str                         # 영문 대문자/숫자/_ (예: ETHICS_REPORT)
    project_name: str                       # 한글명 (예: "윤리경영시스템")
    brief_md: str | None = None             # Step 1 결과
    mockup_vue: str | None = None           # Step 2 결과 (단일 Vue SFC)
    raw_interview_text: str | None = None   # Step 3 입력
    interview_notes_md: str | None = None   # Step 3 결과
    current_step: int = 1                   # 1~4

    model_config = ConfigDict(extra="ignore")  # 구 세션 호환
```

기존 필드(`screen_id`, `screen_name`, `page_type`, `fields`, `tabs`, `vue_code`, `annotations`, `annotation_markdown`, `interview_questions`, `interview_answers`) 제거.
기존 `FieldOption`, `FieldDef`, `TabDef` 모델도 제거.

### 2.3 API 엔드포인트

| # | 엔드포인트 | 입력 | 출력 | LLM |
|---|-----------|------|------|-----|
| 1 | `POST /api/mockup/brief` | `project_id`, `project_name`, `brief_md` | MockupState 초기화 | 미사용 |
| 2 | `POST /api/mockup/generate-mockup` | 세션 brief 사용 | SSE (Vue SFC 청크) | 사용 |
| 3 | `POST /api/mockup/parse-interview` | `raw_interview_text` | `interview_notes_md` | 사용 |
| 4 | `POST /api/mockup/generate-spec` | 세션 전체 | SSE (spec.md 청크) | 사용 |
| 5 | `POST /api/mockup/reset` | - | MockupState 초기화 | 미사용 |

Mockup 생성 완료 시 백엔드는 `pfy-front/src/pages/generated/{project_id}/index.vue`에 Vue 파일 저장 + `staticRoutes.ts`에 라우트 등록 (기존 `_write_vue_to_pfy_front` 로직 재사용).

### 2.4 프롬프트 파일 및 포팅

**`pfy_prompt/`에 원본에서 복사**:
- `brief.md` — 원본 템플릿 (Step 1 프리필용, 프론트엔드에서도 참조)
- `mockupPrompt.md` — Mockup 생성 시스템 프롬프트 원본
- `InterviewParser.md` — 인터뷰 파서 시스템 프롬프트 원본
- `masterPrompt.md` — 이미 복사됨

**`mockup_prompts.py` 함수**:
```python
def brief_template() -> str:
    """brief.md 원본 내용 반환 (Step1 textarea 프리필용, LLM 호출 없음)."""

def mockup_generation_prompt(brief_md: str, component_catalog: str) -> tuple[str, str]:
    """mockupPrompt.md + componentCatalog을 system, brief_md를 user."""

def interview_parser_prompt(mockup_vue: str, raw_interview_text: str) -> tuple[str, str]:
    """InterviewParser.md를 system, mockup + 인터뷰 원문을 user."""

def master_spec_prompt(brief_md: str, mockup_vue: str, interview_notes_md: str) -> tuple[str, str]:
    """기존 함수 수정 — brief 포함."""
```

**제거 함수**: `ai_generate_prompt`, `annotation_prompt`, `interview_prompt`, `interview_notes_prompt`, `extract_structured_data_prompt`, `merge_annotations_prompt`.

### 2.5 componentCatalog 생성

원본 pfy-front의 templates + 공통 컴포넌트 메타를 추출하여 `pfy_prompt/componentCatalog.md` 생성 (일회성 빌드):

- Type{A,B,C,D}_*/index.vue의 `<template>` 섹션 요약 (슬롯 이름, 사용 prop, 구조)
- 자주 쓰는 공통 컴포넌트(SearchForm, DataTable, ContentHeader, Select, InputText 등)의 import 경로 + 핵심 prop 목록

구현: `backend/scripts/build_component_catalog.py` 스크립트가 `/Users/g1_kang/Downloads/pfy-front/`를 읽어 `pfy_prompt/componentCatalog.md` 생성. 한 번 실행 후 결과 파일을 커밋.

### 2.6 mockup_pipeline.py

```python
class MockupPipeline:
    async def generate_mockup_streaming(self, brief_md: str) -> AsyncIterator[str]:
        catalog = _load_component_catalog()
        system, user = mockup_generation_prompt(brief_md, catalog)
        stream = await llm_client.complete(system, user, stream=True)
        async for chunk in stream:
            yield chunk

    async def parse_interview(self, mockup_vue: str, raw_text: str) -> str:
        system, user = interview_parser_prompt(mockup_vue, raw_text)
        return await llm_client.complete(system, user, stream=False)

    async def generate_spec_streaming(
        self, brief_md: str, mockup_vue: str, interview_notes_md: str,
    ) -> AsyncIterator[str]:
        system, user = master_spec_prompt(brief_md, mockup_vue, interview_notes_md)
        stream = await llm_client.complete(system, user, stream=True)
        async for chunk in stream:
            yield chunk


mockup_pipeline = MockupPipeline()
```

---

## 3. 프론트엔드 설계

### 3.1 컴포넌트 구조

```
frontend/src/components/mockup/
├── MockupPipeline.tsx          # [수정] 4단계 스텝퍼
├── StepIndicator.tsx           # [수정] 6 → 4 단계, 라벨 변경
├── Step1Brief.tsx              # [신규]
├── Step2Mockup.tsx             # [신규]
├── Step3Interview.tsx          # [신규]
├── Step4SpecGenerate.tsx       # [신규]
└── (기존 Step1~6)               # [삭제]
```

### 3.2 Step별 기능

**Step1Brief** — brief.md 작성
- `project_id` 입력 (`^[A-Z0-9_]+$` 검증)
- `project_name` 입력 (한글명)
- brief_md textarea (원본 `brief.md` 템플릿 프리필, 자유 편집)
- "다음" 버튼 → `POST /api/mockup/brief` → Step 2

**Step2Mockup** — Vue 생성 + 미리보기
- "Mockup 생성 시작" 버튼 → SSE `/generate-mockup`
- 스트리밍 중: 상태 메시지 + 코드 길이 표시
- 완료: iframe에 `http://localhost:8081/{PROJECT_ID}` 렌더링 (기존 ResizeObserver 재사용)
- "코드 보기" 토글 + "새 탭 열기" 링크
- "재생성" 버튼 (LLM 재호출) + "다음"

**Step3Interview** — 인터뷰 원문 → InterviewNote
- 큰 textarea: "녹취 풀이나 회의록 원문을 붙여넣으세요"
- "InterviewNote 생성" 버튼 → `POST /parse-interview`
- 결과: `interview_notes_md`를 react-markdown 렌더 (Keep/Change/Add/Out/TBD 가시화)
- "재생성" / "다음"

**Step4SpecGenerate** — spec.md 최종 생성
- 입력 요약 (Brief 길이 / Mockup OK / InterviewNote OK)
- "Spec.md 생성" 버튼 → SSE `/generate-spec`
- 스트리밍 청크는 `session.spec_markdown`에 appendSpecChunk
- 완료 시 `isGenerating=false` → App.tsx가 자동으로 SpecViewer 화면으로 전환 (기존 동작)

### 3.3 MockupPipeline 단계 전환

```tsx
function MockupPipeline() {
  const currentStep = useSessionStore(s => s.mockupState?.currentStep ?? 1)
  return (
    <>
      <StepIndicator currentStep={currentStep} />
      {currentStep === 1 && <Step1Brief />}
      {currentStep === 2 && <Step2Mockup />}
      {currentStep === 3 && <Step3Interview />}
      {currentStep === 4 && <Step4SpecGenerate />}
    </>
  )
}
```

StepIndicator 라벨: `① Brief · ② Mockup · ③ 인터뷰 · ④ Spec`

### 3.4 Zustand 스토어 재정의

```typescript
mockupState: {
  projectId: string
  projectName: string
  briefMd: string | null
  mockupVue: string | null
  rawInterviewText: string | null
  interviewNotesMd: string | null
  currentStep: number
} | null

// 액션
setBrief(projectId, projectName, briefMd): Promise<void>
generateMockup(): void    // SSE
parseInterview(rawText): Promise<void>
generateMockupSpec(): void // SSE
mockupGoToStep(step): void
resetMockup(): void
```

제거 액션: `mockupAiGenerate`, `mockupScaffold`, `mockupAiAnnotate`, `mockupAiInterview`, `mockupSubmitInterviewResult`, 기존 `mockupGenerateSpec`.

### 3.5 타입 정리 (`types/index.ts`)

**제거**: `FieldOption`, `FieldDef`, `InterviewQuestion`, `AiGenerateResult`, `ScaffoldResult`, `AnnotateResult`, `InterviewResult`, `InterviewResultResponse`, `SCREEN_ID_INVALID_CHARS`

**추가**: 새 `MockupState`, `BriefRequest`, `ParseInterviewRequest`, `ParseInterviewResponse`, `PROJECT_ID_INVALID_CHARS`

### 3.6 API 클라이언트 (`api/client.ts`)

**제거**: `mockupAiGenerate`, `mockupScaffold`, `mockupAiAnnotate`, `mockupAiInterview`, `mockupInterviewResult`

**추가**:
```typescript
export async function mockupBrief(projectId, projectName, briefMd): Promise<void>
export function mockupGenerateMockup(onEvent): void
export async function mockupParseInterview(rawText): Promise<{interview_notes_md: string}>
export function mockupGenerateSpec(onEvent): void
export async function mockupReset(): Promise<void>
```

---

## 4. 데이터 흐름

```
Step 1: Brief 작성
  POST /api/mockup/brief {project_id, project_name, brief_md}
  → session.mockup_state = MockupState(brief_md=..., current_step=1)

Step 2: Mockup 생성
  POST /api/mockup/generate-mockup (SSE)
  → llm_client(mockupPrompt.md + componentCatalog.md, brief_md)
  → 스트리밍 청크를 mockup_vue로 누적
  → 완료 시 pfy-front/src/pages/generated/{PROJECT_ID}/index.vue 저장
  → staticRoutes.ts에 /{PROJECT_ID} 등록
  → iframe src=http://localhost:8081/{PROJECT_ID} 로 렌더링

Step 3: 인터뷰 파싱
  POST /api/mockup/parse-interview {raw_interview_text}
  → llm_client(InterviewParser.md, mockup_vue + raw_text)
  → interview_notes_md 반환

Step 4: Spec 생성
  POST /api/mockup/generate-spec (SSE)
  → llm_client(masterPrompt.md, brief + mockup + interview)
  → session.spec_markdown 스트리밍
  → 완료 시 App.tsx가 SpecViewer 전환 (기존 로직)
```

---

## 5. 검증 계획

### 5.1 백엔드 테스트
- [ ] `test_mockup_pipeline.py` — 각 단계 mock LLM으로 동작 검증
- [ ] `test_mockup_router.py` — 5개 엔드포인트 상태 전이 검증
- [ ] `test_mockup_models.py` — 새 MockupState 모델 + 구 세션 호환성(`extra='ignore'`) 검증
- [ ] `test_vue_generator.py` — **삭제**
- [ ] 기존 테스트 회귀 — 47개 중 mockup 관련은 재작성, 나머지 유지

### 5.2 프론트엔드 검증
- [ ] `npx tsc --noEmit` 통과
- [ ] `npm run build` 통과
- [ ] E2E 수동: 탭 1 회귀 + 탭 2 4단계 완주 + iframe v-if 전환 동작

### 5.3 컴포넌트 카탈로그
- [ ] `backend/scripts/build_component_catalog.py` 실행 → `pfy_prompt/componentCatalog.md` 생성 + 커밋
- [ ] 카탈로그가 TypeA~D 슬롯/prop, 공통 컴포넌트 import 경로 모두 포함 확인

### 5.4 리스크 대응
- LLM 생성 Vue의 import 오류 → 프롬프트에 componentCatalog + 샘플 주입 + 정규식 사후 검증
- v-if 전환 버튼 누락 → 프롬프트에 규칙 강조 + 생성 결과에 `v-if=` 존재 확인 경고
- LLM 출력 토큰 초과 → `stream=True` 청크 수신
- 구 세션 호환 → MockupState에 `model_config = ConfigDict(extra="ignore")`
- 탭 전환 시 잔여 상태 → reset 시 MockupState 함께 초기화

---

## 6. 제거 대상 정리

### 백엔드
- `backend/app/llm/vue_generator.py` (전체 파일)
- `backend/tests/test_vue_generator.py` (전체 파일)
- `mockup_prompts.py` 함수: `ai_generate_prompt`, `annotation_prompt`, `interview_prompt`, `interview_notes_prompt`, `extract_structured_data_prompt`, `merge_annotations_prompt`
- `mockup.py` 라우터의 기존 7개 엔드포인트 (`/ai-generate`, `/scaffold`, `/ai-annotate`, `/ai-interview`, `/interview-result`, 기존 `/generate-spec`, `/annotate-constraints`)
- `mockup.py`의 `_normalize_ai_result`, `_infer_ui_type`, `_parse_options_text` 헬퍼

### 프론트엔드
- `components/mockup/Step1AiGenerate.tsx`, `Step2Scaffold.tsx`, `Step3Annotate.tsx`, `Step4Interview.tsx`, `Step5InterviewResult.tsx`, `Step6SpecGenerate.tsx`
- `store/sessionStore.ts`의 6개 기존 mockup 액션
- `types/index.ts`의 10개 기존 Mockup 관련 타입 + `SCREEN_ID_INVALID_CHARS`

### 세션 정리
- 브라우저 sessionStorage / 서버 `.sessions/*.json`의 구 포맷은 자연 만료(2h TTL) 또는 수동 reset으로 정리 — 코드에서는 `extra="ignore"`로 무해화
