# Dual Spec Pipeline Design

> 텍스트 입력과 Mockup 생성 두 가지 경로를 탭으로 선택하여 spec.md를 생성하고, 동일한 코드 생성 파이프라인으로 연결하는 기능

## Context

현재 need-only-prd는 "비정형 텍스트 → spec.md" 단일 경로만 제공한다. pfy-front 프로젝트에는 "화면 제목 → Mockup → 인터뷰 → spec.md"라는 더 구조화된 경로가 있다. 두 접근법은 상호 보완적이며, 사용자가 상황에 따라 선택할 수 있도록 탭 UI로 통합한다.

## 설계 결정 요약

| 항목 | 결정 |
|------|------|
| 서버 구조 | FastAPI 단일 서버 (Express 로직을 Python으로 포팅) |
| Mockup 워크플로우 | 6단계 전체 유지 (AI Generate → Scaffold → Annotate → Interview → Result → Spec) |
| 코드 생성 연결 | 두 탭 모두 동일한 spec_markdown → 기존 7-phase 코드 생성 파이프라인 |
| 탭 위치 | InputPanel 위치에 탭 배치, 이후 SpecViewer/ChatPanel/CodeGenPanel 공유 |
| 스텝퍼 UI | 상단 6단계 스텝퍼, 각 단계 결과 확인 후 "다음" 버튼으로 진행 |
| 인터뷰 입력 | 질문-답변 폼 + 인터뷰 전문 붙여넣기 두 모드 모두 지원 |

---

## 1. 전체 아키텍처

```
┌─ React Frontend ─────────────────────────────────────────┐
│                                                           │
│  ┌─ SpecModeSelector ────────────────────────────────┐   │
│  │  [텍스트 입력]  |  [Mockup 생성]                    │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  탭1: InputPanel (기존)                                    │
│  탭2: MockupPipeline (신규, 6단계 스텝퍼)                  │
│                                                           │
│  ─── 공통 ───────────────────────────────────────────────  │
│  SpecViewer → ChatPanel → CoverageScore → CodeGenPanel   │
└───────────────────────────────────────────────────────────┘
         │
         ▼  /api/*
┌─ FastAPI Backend ────────────────────────────────────────┐
│  기존: /api/input, /api/spec, /api/chat, /api/validate   │
│  신규: /api/mockup/* (6개 엔드포인트)                     │
│  공통: session, llm_client, codegen orchestrator          │
└───────────────────────────────────────────────────────────┘
```

두 탭 모두 최종 결과를 `session.spec_markdown`에 저장하면, 이후 SpecViewer/ChatPanel/CodeGenPanel이 동일하게 동작한다.

---

## 2. 백엔드 설계

### 2.1 신규 파일 구조

```
backend/app/
├── llm/
│   ├── mockup_pipeline.py      # MockupPipeline 클래스 (6단계 오케스트레이션)
│   ├── mockup_prompts.py       # pfy-front RequirementPrompt 프롬프트 포팅
│   └── vue_generator.py        # VuePageGenerator Python 포팅 (템플릿 기반)
├── routers/
│   └── mockup.py               # /api/mockup/* 엔드포인트
└── models.py                   # MockupState 모델 추가
```

### 2.2 세션 모델 확장

```python
class MockupState(BaseModel):
    screen_id: str
    screen_name: str
    page_type: str                          # list-detail, list, edit, tab-detail
    fields: list[dict]                      # AI Generate 결과
    vue_code: str | None = None             # Scaffold 결과
    annotations: list[dict] | None = None   # Annotate 결과
    annotation_markdown: str | None = None
    interview_questions: list[dict] | None = None
    interview_answers: list[dict] | None = None
    raw_interview_text: str | None = None
    current_step: int = 1

# SessionState 확장
class SessionState:
    ...
    spec_source: str | None = None          # "text" | "mockup"
    mockup_state: MockupState | None = None
```

### 2.3 API 엔드포인트

| # | 엔드포인트 | 입력 | 출력 | LLM |
|---|-----------|------|------|-----|
| 1 | `POST /api/mockup/ai-generate` | title, pageType, description | searchFields, tableColumns, mockRows (또는 formFields) | Yes |
| 2 | `POST /api/mockup/scaffold` | screenId, screenName, pageType, fields | vue_code 문자열 | No |
| 3 | `POST /api/mockup/ai-annotate` | (세션의 vue_code 사용) | annotated_vue_code, annotations, annotation_markdown | Yes |
| 4 | `POST /api/mockup/ai-interview` | (세션의 annotation_markdown, vue_code 사용) | questions (10개) | Yes |
| 5 | `POST /api/mockup/interview-result` | questions+answers 또는 raw_interview_text | interview_note_md, spec_markdown | Yes (2~3회) |
| 6 | `POST /api/mockup/annotate-constraints` | (세션의 annotation_markdown 사용) | 보강된 annotation_markdown | Yes |

### 2.4 interview-result 내부 파이프라인 (5단계)

pfy-front의 `interview-result.ts` 로직 포팅:

1. `generateInterviewNotes` — LLM으로 InterviewNote.md 작성
2. `extractStructuredData` — (rawText 모드) 인터뷰 전문 → keep/change/add/tbd 구조화
3. `mergeInterviewData` — 답변을 구조화 JSON으로 병합
4. `matchAndMergeIntoAnnotations` — LLM으로 @id 주석에 인터뷰 결과 병합
5. `generateSpec` — masterPrompt.md 기반 최종 spec_markdown 생성 → 세션 저장

### 2.5 Vue 코드 생성기 포팅

`VuePageGenerator.ts` → `vue_generator.py`:
- Python f-string 또는 Jinja2로 동일한 Vue SFC 생성
- pageType별 템플릿: list, list-detail, edit, tab-detail
- RouterUpdater는 생략 (need-only-prd에서 불필요)

### 2.6 프롬프트 포팅 매핑

| pfy-front 소스 | 포팅 대상 |
|----------------|----------|
| `ai-generate.ts` buildPrompt() | `mockup_prompts.py` ai_generate_prompt() |
| `ai-annotate.ts` ANNOTATION_SYSTEM_PROMPT | `mockup_prompts.py` annotation_prompt() |
| `ai-interview-questions.ts` INTERVIEW_ROLE_CONTEXT | `mockup_prompts.py` interview_prompt() |
| `interview-result.ts` 5단계 프롬프트들 | `mockup_prompts.py` interview_result_prompts() |
| `RequirementPrompt/masterPrompt.md` | `mockup_prompts.py` master_spec_prompt() |

---

## 3. 프론트엔드 설계

### 3.1 신규 컴포넌트

```
frontend/src/components/
├── SpecModeSelector.tsx          # 탭 전환 컴포넌트
├── mockup/
│   ├── MockupPipeline.tsx        # 6단계 스텝퍼 컨테이너
│   ├── StepIndicator.tsx         # 상단 스텝퍼 바
│   ├── Step1AiGenerate.tsx       # 화면 제목/설명/타입 입력 + 결과 표시
│   ├── Step2Scaffold.tsx         # Vue 코드 미리보기
│   ├── Step3Annotate.tsx         # 주석 삽입 결과 (Before/After)
│   ├── Step4Interview.tsx        # 질문 카드 + 답변 / 전문 붙여넣기
│   ├── Step5InterviewResult.tsx  # InterviewNote 결과 표시
│   └── Step6SpecGenerate.tsx     # spec 생성 스트리밍 → 완료 시 SpecViewer 전환
```

### 3.2 App.tsx 변경

기존: `rawInput ? <SpecViewer/> : <InputPanel/>`

변경: `specMarkdown ? <SpecViewer/> : <SpecModeSelector/>`

`SpecModeSelector`가 내부적으로 탭1(`InputPanel`)과 탭2(`MockupPipeline`)를 전환.

### 3.3 Zustand 스토어 확장 (sessionStore.ts)

```typescript
// 신규 상태
specMode: "text" | "mockup"
mockupState: MockupState | null
currentStep: number

// 신규 액션
setSpecMode(mode: "text" | "mockup")
aiGenerate(title: string, pageType: string, description?: string)
scaffold(screenId: string, screenName: string, pageType: string, fields: FieldDef[])
aiAnnotate()
aiInterview()
submitInterviewResult(answers: Answer[] | rawText: string)
goToStep(step: number)
resetMockup()
```

### 3.4 Step4Interview UI

두 가지 모드를 내부 탭으로 전환:

- **질문별 답변 모드**: 10개 질문을 카드로 표시 (category, priority 뱃지, tip 텍스트), 각 카드 아래 textarea
- **전문 붙여넣기 모드**: 단일 대형 textarea에 인터뷰 회의록 전체 붙여넣기

### 3.5 탭 전환 제약

- spec 생성 진행 중: 탭 전환 비활성화
- Mockup 파이프라인 중간 단계에서 텍스트 탭 전환 시: 확인 다이얼로그 ("진행 중인 작업이 초기화됩니다")
- spec_markdown 존재 시 새로 시작 확인

---

## 4. 데이터 흐름

```
[탭1: 텍스트 입력]                    [탭2: Mockup 생성]
      │                                    │
  텍스트 붙여넣기                    ① POST /api/mockup/ai-generate
      │                                    │
  POST /api/input                   ② POST /api/mockup/scaffold
      │                                    │
  POST /api/spec/generate (SSE)     ③ POST /api/mockup/ai-annotate
      │                                    │
      │                             ④ POST /api/mockup/ai-interview
      │                                    │
      │                             ⑤⑥ POST /api/mockup/interview-result
      │                                    │
      ▼                                    ▼
  session.spec_markdown ◄──────────────────┘
  session.spec_source = "text"|"mockup"
      │
      ▼  (공통)
  SpecViewer → ChatPanel → CoverageScore → CodeGenPanel
```

---

## 5. 검증 계획

### 백엔드 테스트
- [ ] 각 `/api/mockup/*` 엔드포인트 단위 테스트
- [ ] MockupPipeline 6단계 통합 테스트 (mock LLM 응답)
- [ ] vue_generator 페이지 타입별 코드 생성 테스트
- [ ] 세션 저장/복구 시 mockup_state 포함 확인

### 프론트엔드 테스트
- [ ] 탭 전환 동작 확인
- [ ] 6단계 스텝퍼 진행/후퇴 동작
- [ ] Step4 질문별 답변 모드와 전문 붙여넣기 모드 전환
- [ ] spec 생성 완료 후 SpecViewer → ChatPanel → CodeGenPanel 정상 연결
- [ ] 탭 전환 제약 (진행 중 전환 방지) 확인

### E2E 시나리오
- [ ] 탭1: 텍스트 입력 → spec 생성 → 코드 생성 (기존 동작 회귀 확인)
- [ ] 탭2: 화면 제목 입력 → 6단계 완주 → spec 생성 → 코드 생성
- [ ] 탭2: 인터뷰 전문 붙여넣기 모드로 spec 생성
- [ ] 세션 새로고침 후 mockup 상태 복구
