# Need Only PRD

LLM 기반 PRD(Product Requirements Document) 자동 생성기 + 실시간 Mockup 미리보기 + 멀티에이전트 코드 생성 시스템

**두 가지 경로**로 스펙을 만들 수 있습니다:
1. **텍스트 입력**: 비정형 텍스트(회의록, 이메일, 채팅 로그) → 스펙
2. **Mockup 생성**: AI가 설계한 화면 Mockup + 인터뷰 질문/답변 → 스펙

어느 경로든 최종 `spec.md`가 생성되면 동일한 코드 생성 파이프라인으로 Spring Boot + Vue3 소스 코드를 자동 생성해 Docker로 실행할 수 있습니다.

## 주요 기능

### Spec 생성 파이프라인 (2가지 경로)

**텍스트 입력 경로**
- 비정형 텍스트에서 구조화된 요구사항 자동 추출
- 요구사항 기반 기술 스펙(Markdown) 실시간 스트리밍 생성
- 채팅 기반 스펙 반복 수정 (히스토리 자동 요약)
- 요구사항 커버리지 검증 (점수 + 누락 항목)

**Mockup 생성 경로** (6단계 스텝퍼)
1. **AI Generate**: 화면 제목 → AI가 검색필드/테이블컬럼/Mock 데이터 자동 설계
2. **Scaffold**: 필드 정의 → 결정적 Python 템플릿으로 Vue SFC 생성 (LLM 미사용)
3. **Mockup 미리보기**: 생성된 Vue 파일을 pfy-front에 저장 → iframe 실시간 렌더링 (ResizeObserver 기반 자동 스케일)
4. **AI Annotate**: Vue `<template>` 분석 → UI 요소별 주석 자동 삽입
5. **AI Interview**: 주석 + Mockup → 고객 인터뷰 질문 10개 생성
6. **Interview Result → Spec**: 답변 수집(개별 / 전문 붙여넣기) → masterPrompt 기반 최종 spec.md 생성

### 멀티에이전트 코드 생성
- 7단계 에이전트 파이프라인으로 Spring Boot + Vue3 코드 자동 생성
- CPMS 프레임워크 코딩 가이드 기반 코드 품질 보장
- 3단계 방어 체계: 생성 시 DO NOT 규칙 / 정적 검사 / LLM QA 검증
- 생성된 코드를 Docker 컨테이너로 즉시 빌드 & 실행
- 컴파일 에러 자동 수정 (최대 3회 재시도)

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS v4, Zustand, react-markdown |
| Backend | FastAPI, Python 3.11+, sse-starlette, pydantic-settings |
| LLM | Azure OpenAI (gpt-5.4, gpt-5.3-codex), Anthropic, OpenAI 지원 |
| Mockup 렌더러 | pfy-front (Vue 3 + PrimeVue + CPMS 공통 컴포넌트) |
| 코드 생성 대상 | Spring Boot 2.7 + MyBatis + Vue3 + PrimeVue (CPMS 프레임워크) |
| 배포 | Docker Compose (MariaDB + Spring Boot + Vue3) |
| UI 디자인 | Material Design 3 색상 체계, Manrope + Inter 폰트 |

## 시작하기

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- Docker (코드 생성 배포 기능 사용 시)

### 환경 설정

```bash
cp .env.example .env
# .env에 API 키 설정
```

`.env` 주요 설정:

```env
LLM_PROVIDER=azure_openai

# Azure OpenAI (스펙 생성 + Mockup 파이프라인 + QA)
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_MODEL_NAME=gpt-5.4

# Azure OpenAI Codex (코드 생성 전용)
CODEX_AZURE_OPENAI_ENDPOINT=https://your-codex-resource.cognitiveservices.azure.com
CODEX_AZURE_OPENAI_API_KEY=your-codex-key
CODEX_AZURE_OPENAI_MODEL_NAME=gpt-5.3-codex
```

### 실행 (원클릭)

```bash
./start.sh     # 의존성 자동 설치 + 3개 서버 기동 + 브라우저 자동 오픈
./stop.sh      # 모두 종료
```

`start.sh`가 자동으로 수행:
- Backend `.venv` 없으면 생성 + `pip install -e ".[dev]"`
- Frontend/pfy-front `node_modules` 없으면 `npm install` (사내 registry 실패 시 public으로 자동 fallback)
- 포트 8001/5173/8081 점유 프로세스 정리
- 세 서버 동시 기동 → Frontend 준비되면 브라우저 자동 오픈

실행 후 접속:
- **`http://localhost:5173`** — 메인 애플리케이션
- `http://localhost:8001` — Backend API
- `http://localhost:8085` — pfy-front (Mockup 렌더링 런타임, iframe 내부에서만 사용)

로그 확인:
```bash
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/pfy-front.log
```

### 테스트

```bash
cd backend
source .venv/bin/activate
pytest                         # 전체 테스트 (47개)
pytest tests/test_routers.py   # 라우터 테스트
pytest -k "test_name"          # 단일 테스트

cd frontend
npm run build                  # 타입 체크 + 프로덕션 빌드
npm run lint                   # ESLint
```

## 아키텍처

### 전체 흐름

```
                        ┌─────────────────────────┐
                        │   사용자가 탭 선택       │
                        └─────┬─────────────┬─────┘
              [텍스트 입력]    │             │    [Mockup 생성]
                               ▼             ▼
          ┌────────────────────┐         ┌────────────────────────┐
          │ Text Input → Spec  │         │ Mockup Pipeline (6단계)│
          │   (LLM, streaming) │         │ AI Generate → Scaffold │
          │                    │         │ → Annotate → Interview │
          │                    │         │ → Result → Spec        │
          └──────────┬─────────┘         └──────────┬─────────────┘
                     │                              │
                     └──────────┬───────────────────┘
                                ▼
                     session.spec_markdown
                                │
                                ▼
                  ┌──────────────────────────┐
                  │  Chat Refine + Validate  │
                  └────────────┬─────────────┘
                               ▼
              ┌───────────────────────────────┐
              │ Code Generation (7 phases)    │
              │ codex_client (gpt-5.3-codex)  │
              │ llm_client   (gpt-5.4 for QA) │
              └────────────┬──────────────────┘
                           ▼
                  Docker Deploy (3 containers)
```

### Text Spec Pipeline

```
POST /api/input (텍스트 제출)
  → POST /api/spec/generate (SSE: 요구사항 추출 → 스펙 생성)
  → POST /api/chat (SSE: 채팅으로 스펙 수정)
  → POST /api/validate (커버리지 검증)
  → GET /api/export (Markdown 다운로드)
```

### Mockup Spec Pipeline

```
POST /api/mockup/ai-generate      → searchFields/tableColumns JSON (gpt-5.4)
  → POST /api/mockup/scaffold     → Vue SFC 생성 (Python 템플릿, LLM 미사용)
                                    + pfy-front/src/pages/generated/에 저장
                                    + staticRoutes.ts에 라우트 등록
                                    → Vue dev server가 hot-reload → iframe 렌더링
  → POST /api/mockup/ai-annotate  → UI 요소별 주석 삽입 (gpt-5.4)
  → POST /api/mockup/ai-interview → 인터뷰 질문 10개 (gpt-5.4)
  → POST /api/mockup/interview-result → InterviewNote + spec.md (gpt-5.4)
```

### 코드 생성 파이프라인 (7단계)

```
Phase 1: Planner .............. 스펙 분석 → 파일 생성 계획 (codex)
Phase 2: Data Engineer ........ SQL 스키마 + TypeScript 타입 (codex)
Phase 3: Backend Engineer ..... DTO, DAO, Service, Mapper XML (codex)
         Frontend Engineer .... 단일 Vue3 페이지 (codex)
Phase 3.5: Static Check ....... 정규식 기반 즉시 검사 (LLM 호출 0회)
Phase 4: Backend QA ........... BackendGuide 기반 검증 (gpt-5.4)  ← 병렬
         Frontend QA .......... FrontendGuide 기반 검증 (gpt-5.4) ← 병렬
Phase 5: Fix Agent ............ QA 이슈 수정 (gpt-5.4, 이슈 있을 때만)
```

### 생성 파일 구성 (10개)

| # | 파일 타입 | 레이어 | 설명 |
|---|-----------|--------|------|
| 1 | db_init_sql | backend | MariaDB 스키마 |
| 2 | vue_types | frontend | TypeScript 인터페이스 |
| 3 | dto_request | backend | 요청 DTO |
| 4 | dto_response | backend | 응답 DTO |
| 5 | dao | backend | DAO 인터페이스 |
| 6 | dao_impl | backend | DAO 구현체 |
| 7 | service | backend | Service 인터페이스 |
| 8 | service_impl | backend | Service 구현체 |
| 9 | mapper_xml | backend | MyBatis Mapper |
| 10 | vue_page | frontend | 통합 Vue3 페이지 (검색폼+테이블+API 인라인) |

### 3단계 코드 품질 방어

1. **생성 시 방지**: 에이전트 프롬프트에 DO NOT 규칙 주입 (UUID 금지, scrollHeight="flex" 금지 등)
2. **정적 검사**: 정규식으로 알려진 에러 패턴 즉시 검출 (LLM 호출 없음)
3. **LLM QA 검증**: BackendGuide/FrontendGuide 전문 대조 + 스펙 준수 여부 검사

### Mockup 렌더링 원리 (Vue 코드는 LLM이 만들지 않음)

- **LLM(gpt-5.4)**: 화면에 필요한 필드 **구조**만 JSON으로 생성 (`searchFields`, `tableColumns` 등)
- **Python 템플릿** (`vue_generator.py`): 구조 JSON을 받아 결정적으로 Vue SFC를 조립 — 문법 오류 0, 토큰 비용 0
- **pfy-front**: 조립된 Vue 파일이 저장되면 Vue dev server가 hot-reload → iframe(1440×900 고정 렌더 후 ResizeObserver로 컨테이너에 맞춰 자동 축소)에 표시

## 프로젝트 구조

```
need-only-prd/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 앱 + 8개 라우터
│   │   ├── config.py               # pydantic-settings (.env 로딩)
│   │   ├── session.py              # 인메모리 + 디스크 세션 관리
│   │   ├── models.py               # Session, CodeGen, MockupState 등
│   │   ├── docker_manager.py       # Docker workspace 관리 + 빌드/실행
│   │   ├── llm/
│   │   │   ├── client.py           # LLMClient (gpt-5.4) + CodexLLMClient (codex)
│   │   │   ├── pipeline.py         # SpecPipeline (텍스트 경로)
│   │   │   ├── mockup_pipeline.py  # MockupPipeline (Mockup 경로, 6단계)
│   │   │   ├── prompts.py          # 텍스트 스펙 프롬프트
│   │   │   ├── mockup_prompts.py   # Mockup 파이프라인 프롬프트 7종
│   │   │   ├── vue_generator.py    # Vue SFC 템플릿 생성기 (LLM 미사용)
│   │   │   ├── agents.py           # 코드 생성 7 에이전트 + static_check()
│   │   │   ├── orchestrator.py     # CodeGenOrchestrator
│   │   │   ├── codegen_context.py  # 가이드 파일 로더
│   │   │   └── codegen_prompts.py  # 코드 생성 프롬프트
│   │   └── routers/                # input, spec, chat, validate, export, session, codegen, mockup
│   └── tests/                      # pytest (47 tests)
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # 루트 레이아웃
│   │   ├── index.css               # M3 색상 테마 (53 토큰)
│   │   ├── api/client.ts           # API 클라이언트 + consumeSSE()
│   │   ├── store/sessionStore.ts   # Zustand 중앙 상태 (text + mockup)
│   │   ├── types/index.ts          # TypeScript 타입
│   │   └── components/
│   │       ├── InputPanel.tsx      # 텍스트 입력 탭
│   │       ├── SpecModeSelector.tsx # 탭 전환 컨테이너
│   │       ├── mockup/             # Mockup 경로 6단계 UI
│   │       │   ├── MockupPipeline.tsx
│   │       │   ├── StepIndicator.tsx
│   │       │   └── Step1~6*.tsx
│   │       └── ...                 # SpecViewer, ChatPanel, CodeGenPanel 등
│   └── package.json
├── pfy-front/                      # Mockup 렌더링 런타임 (Vue + PrimeVue)
│   ├── src/
│   │   ├── components/             # CPMS 공통 컴포넌트 (SearchForm, DataTable 등)
│   │   ├── pages/generated/        # 백엔드가 생성한 Vue 파일 저장 위치
│   │   └── router/staticRoutes.ts  # 백엔드가 자동 등록하는 라우트 파일
│   └── package.json
├── pfy_prompt/                     # LLM 참조 가이드
│   ├── BackendGuide/               # CPMS Spring Boot 가이드 (7 docs)
│   ├── FrontendGuide/              # CPMS Vue3 가이드 (12 docs)
│   ├── masterPrompt.md             # Mockup → Spec 생성 마스터 프롬프트
│   ├── namebook.md
│   └── CPMS_namebook.md
├── skeleton/                       # Docker 프로젝트 템플릿
│   ├── backend/ frontend/ db/
│   └── docker-compose.yml
├── docs/
│   └── superpowers/
│       ├── specs/                  # 설계 스펙 문서
│       └── plans/                  # 구현 계획 문서
├── logs/                           # 실행 로그 (gitignored)
├── .env.example
├── start.sh / stop.sh
└── CLAUDE.md
```

## API 엔드포인트

모든 요청에 `X-Session-ID` 헤더 필요 (UUID, sessionStorage 저장)

### Text Spec Pipeline

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| POST | `/api/input` | 원문 텍스트 제출 | JSON |
| POST | `/api/spec/generate` | 스펙 생성 | SSE |
| GET | `/api/spec` | 현재 스펙 조회 | JSON |
| POST | `/api/chat` | 채팅으로 스펙 수정 | SSE |
| POST | `/api/validate` | 커버리지 검증 | JSON |
| GET | `/api/export` | spec.md 다운로드 | File |

### Mockup Spec Pipeline

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| POST | `/api/mockup/ai-generate` | 화면 제목 → 필드 설계 JSON | JSON |
| POST | `/api/mockup/scaffold` | Vue SFC 생성 + pfy-front에 저장 | JSON |
| POST | `/api/mockup/ai-annotate` | UI 주석 삽입 | JSON |
| POST | `/api/mockup/ai-interview` | 인터뷰 질문 10개 생성 | JSON |
| POST | `/api/mockup/interview-result` | 답변 → InterviewNote + spec.md | JSON |
| POST | `/api/mockup/generate-spec` | spec.md 스트리밍 재생성 | SSE |
| POST | `/api/mockup/annotate-constraints` | 제약조건 보강 (선택) | JSON |

### 공통 / Code Generation

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| GET | `/api/session` | 세션 상태 조회 | JSON |
| POST | `/api/codegen/generate` | 코드 생성 | SSE |
| POST | `/api/codegen/deploy` | Docker 빌드 & 실행 | SSE |
| POST | `/api/codegen/stop` | 컨테이너 중지 | JSON |
| GET | `/api/codegen/download` | 코드 ZIP 다운로드 | File |
| GET | `/api/codegen/files` | 생성된 파일 목록 | JSON |

## 설정값

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `LLM_PROVIDER` | azure_openai | LLM 제공자 (anthropic/azure_openai/openai) |
| `MAX_LLM_CALLS_PER_SESSION` | 200 | 세션당 최대 LLM 호출 수 |
| `SESSION_TTL_HOURS` | 2 | 세션 만료 시간 |
| `CODEGEN_MAX_TOKENS` | 16384 | 코드 생성 최대 출력 토큰 |
| `DOCKER_WORKSPACE_DIR` | /tmp/codegen_workspaces | Docker 작업 디렉토리 |
| `DOCKER_TIMEOUT_SECONDS` | 300 | Docker 빌드 타임아웃 |
| `DOCKER_MAX_FIX_RETRIES` | 3 | 컴파일 에러 자동 수정 최대 시도 |
