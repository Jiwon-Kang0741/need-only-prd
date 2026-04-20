# Need Only PRD

LLM 기반 PRD(Product Requirements Document) 자동 생성기 + 원본 pfy-front MockupBuilder 통합 + 멀티에이전트 코드 생성 시스템

**두 가지 경로**로 스펙을 만들 수 있습니다:
1. **텍스트 입력**: 비정형 텍스트(회의록, 이메일, 채팅 로그) → 스펙
2. **Mockup 생성**: 원본 pfy-front MockupBuilder를 iframe으로 임베드하여 스펙 정의 → Vue 목업 → 인터뷰 → 스펙

어느 경로든 최종 `spec.md`가 생성되면 동일한 코드 생성 파이프라인으로 Spring Boot + Vue3 소스 코드를 자동 생성해 Docker로 실행할 수 있습니다.

## 주요 기능

### Spec 생성 파이프라인 (2가지 경로)

**텍스트 입력 경로**
- 비정형 텍스트에서 구조화된 요구사항 자동 추출
- 요구사항 기반 기술 스펙(Markdown) 실시간 스트리밍 생성
- 채팅 기반 스펙 반복 수정 (히스토리 자동 요약)
- 요구사항 커버리지 검증 (점수 + 누락 항목)

**Mockup 생성 경로** (원본 pfy-front MockupBuilder iframe 통합)
1. **MockupBuilder UI**: 페이지 타입/페이지명/검색필드/테이블컬럼/버튼 액션 구조화 폼 입력
2. **AI 자동생성**: 화면 제목·설명 기반으로 필드 자동 추천 (LLM)
3. **페이지 생성**: Vue SFC 생성 + 라우터 자동 등록 + UI 주석 자동 삽입 → iframe이 자동으로 생성된 페이지로 전환
4. **인터뷰 진행**: 생성된 페이지 우측 사이드 패널의 질문 10개에 답변 작성 (또는 인터뷰 전문 붙여넣기)
5. **자동 spec.md 생성**: 인터뷰 결과 제출 → `postMessage`로 React에 전달 → 우리 백엔드가 masterPrompt 기반 spec.md 생성 → SpecViewer 자동 전환

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
| Backend | FastAPI, Python 3.11+, sse-starlette, pydantic-settings, httpx |
| LLM (spec/QA) | Azure OpenAI gpt-5.4 |
| LLM (Mockup) | Azure OpenAI gpt-5.4 (프록시) 또는 사내 게이트웨이 gpt-5.2 (직접) |
| LLM (코드 생성) | Azure OpenAI gpt-5.3-codex |
| Mockup 런타임 | pfy-front (Vue 3 + PrimeVue + CPMS 공통 컴포넌트) |
| Mockup API | pfy-front scaffolding (Express + ts-node) |
| 코드 생성 대상 | Spring Boot 2.7 + MyBatis + Vue3 + PrimeVue (CPMS 프레임워크) |
| 배포 | Docker Compose (MariaDB + Spring Boot + Vue3) |
| UI 디자인 | Material Design 3 색상 체계 + MockupBuilder 다크 테마 (주황 포인트) |

## 시작하기

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- Docker (코드 생성 배포 기능 사용 시)
- (선택) 사내 VPN (gpt-5.2 직접 호출 시)

### 환경 설정

```bash
cp .env.example .env
# .env에 API 키 설정
```

`.env` 주요 설정 (프로젝트 루트에서 모든 LLM 설정을 통합 관리):

```env
LLM_PROVIDER=azure_openai

# Azure OpenAI — 텍스트 spec 생성 + Mockup 프록시 fallback + QA
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_MODEL_NAME=gpt-5.4

# Azure OpenAI Codex — 코드 생성 전용
CODEX_AZURE_OPENAI_ENDPOINT=https://your-codex-resource.cognitiveservices.azure.com
CODEX_AZURE_OPENAI_API_KEY=your-codex-key
CODEX_AZURE_OPENAI_MODEL_NAME=gpt-5.3-codex

# MockupBuilder scaffolding 서버가 호출할 LLM 선택
# - USE_LLM_PROXY=true  → 우리 FastAPI /api/llm/chat-completion 경유 (gpt-5.4, VPN 불필요)
# - USE_LLM_PROXY=false → 사내 AOAI 게이트웨이(gpt-5.2) 직접 호출 (VPN 필요)
USE_LLM_PROXY=false
AOAI_ENDPOINT=https://ito-ax.apps.dev.honecloud.co.kr/api/hub/v1/models/gpt-5.2/invoke
AOAI_API_KEY=your-aoai-key
AOAI_DEPLOYMENT=gpt-5.2
```

### 실행 (원클릭)

```bash
./start.sh     # 의존성 자동 설치 + 4개 서버 기동 + 브라우저 자동 오픈
./stop.sh      # 모두 종료
```

`start.sh`가 자동으로 수행:
- Backend `.venv` 없으면 생성 + `pip install -e ".[dev]"`
- Frontend / pfy-front / scaffolding `node_modules` 없으면 `npm install` (사내 registry 실패 시 public으로 자동 fallback, `--legacy-peer-deps`)
- 포트 8001/5173/8085/4000 점유 프로세스 정리
- 4개 서버 동시 기동 → Frontend 준비되면 브라우저 자동 오픈

실행 후 접속:

| 서버 | 주소 | 역할 |
|------|------|------|
| **Frontend (React)** | `http://localhost:5173` | **메인 애플리케이션** |
| Backend (FastAPI) | `http://localhost:8001` | 세션/스펙/코드 생성 API |
| pfy-front (Vue) | `http://localhost:8085` | Mockup 렌더링 런타임 (iframe 안에서만 사용) |
| scaffolding (Express) | `http://localhost:4000` | MockupBuilder API (iframe이 호출) |

로그 확인:
```bash
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/pfy-front.log
tail -f logs/scaffolding.log
```

### 테스트

```bash
cd backend
source .venv/bin/activate
pytest                         # 전체 테스트
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
          ┌────────────────────┐         ┌───────────────────────────┐
          │ Text Input → Spec  │         │ iframe 임베드              │
          │   (LLM, streaming) │         │ pfy-front MockupBuilder    │
          │                    │         │ (1600×1000 + 자동 scale)   │
          │                    │         │ postMessage 기반 자동 전환 │
          └──────────┬─────────┘         └──────────┬────────────────┘
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

### Mockup Spec Pipeline (iframe 통합)

```
[React Frontend :5173]                    [pfy-front :8085 iframe]
Mockup 탭 선택 → iframe 로드 ───────────→ MockupBuilder UI
                                            │
                                            ▼
                                   사용자 폼 입력 + AI 자동생성
                                            │
                                            ▼
                              [scaffolding :4000] /api/generate
                                            │
                                            ▼
                             Vue 파일 생성 + 라우터 등록
                             + UI 주석 자동 삽입
                                            │
                              postMessage('pfy-page-generated')
[React]                 ◀────────────────── │
iframe src를 생성된 페이지로 전환            │
                                            ▼
                                   생성된 페이지 로드
                                   (우측 사이드 패널: 인터뷰 질문 10개)
                                            │
                                            ▼
                              인터뷰 답변 → [scaffolding] /api/generate-interview-result
                                            │
                                            ▼
                              src/spec-source/{screen}/InterviewNote.md 저장
                              postMessage('pfy-interview-result-success')
[React]                 ◀────────────────── │
POST /api/mockup/generate-spec-from-builder (screen_name)
  → 백엔드가 spec-source 파일들 읽기
  → masterPrompt + LLM으로 spec.md 생성
  → session.spec_markdown 저장
                                            │
                                            ▼
                                   SpecViewer 자동 전환
```

### LLM 프록시 구조

scaffolding(Express)는 원래 사내 AOAI 게이트웨이(`X-Api-Key` 헤더, gpt-5.2)를 직접 호출하지만, VPN 없는 환경에서도 동작하도록 **우리 FastAPI 백엔드 프록시** (`/api/llm/chat-completion`, gpt-5.4)를 선택할 수 있습니다.

```
USE_LLM_PROXY=true  (기본, VPN 불필요)
  scaffolding → FastAPI /api/llm/chat-completion → llm_client → gpt-5.4

USE_LLM_PROXY=false (VPN 필요)
  scaffolding → ito-ax.apps.dev.honecloud.co.kr → gpt-5.2
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

### Mockup UI 테마

원본 pfy-front MockupBuilder가 iframe으로 임베드될 때 **검은 배경 + 주황 포인트 컬러**로 메인 React 앱과 일관된 다크 테마를 적용합니다.

- 배경: `#0f0f0f` / 카드: `#1a1a1a` / 입력: `#242424`
- 텍스트: `#fff` / 보조: `#c0c0c0` / 비활성: `#606060`
- 포인트 컬러: `#f4821f` (주황)
- PrimeVue 컴포넌트(Select/InputText/Button/Checkbox) `:deep()`으로 다크 톤 오버라이드
- 버튼 활성/비활성: 투명+주황 테두리 vs 회색+opacity 0.6+`not-allowed` 커서로 구분

## 프로젝트 구조

```
need-only-prd/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 앱 + 9개 라우터
│   │   ├── config.py               # pydantic-settings (.env 로딩)
│   │   ├── session.py              # 인메모리 + 디스크 세션 관리
│   │   ├── models.py               # Session, CodeGen, MockupState 등
│   │   ├── docker_manager.py       # Docker workspace 관리 + 빌드/실행
│   │   ├── llm/
│   │   │   ├── client.py           # LLMClient (gpt-5.4) + CodexLLMClient (codex)
│   │   │   ├── mockup_client.py    # MockupLLMClient (gpt-5.2 fallback → llm_client)
│   │   │   ├── pipeline.py         # SpecPipeline (텍스트 경로)
│   │   │   ├── mockup_pipeline.py  # MockupPipeline (brief/mockup/interview → spec)
│   │   │   ├── prompts.py          # 텍스트 스펙 프롬프트
│   │   │   ├── mockup_prompts.py   # Mockup 파이프라인 프롬프트 (masterPrompt 로딩)
│   │   │   ├── agents.py           # 코드 생성 7 에이전트 + static_check()
│   │   │   ├── orchestrator.py     # CodeGenOrchestrator
│   │   │   ├── codegen_context.py  # 가이드 파일 로더
│   │   │   └── codegen_prompts.py  # 코드 생성 프롬프트
│   │   └── routers/                # input, spec, chat, validate, export,
│   │                               # session, codegen, mockup, llm_proxy
│   └── tests/                      # pytest
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # 루트 레이아웃 (탭 전환)
│   │   ├── index.css               # M3 색상 테마
│   │   ├── api/client.ts           # API 클라이언트 + consumeSSE() + getSessionId()
│   │   ├── store/sessionStore.ts   # Zustand 중앙 상태
│   │   ├── types/index.ts          # TypeScript 타입
│   │   └── components/
│   │       ├── InputPanel.tsx      # 텍스트 입력 탭
│   │       ├── SpecModeSelector.tsx # 탭 전환 컨테이너
│   │       ├── mockup/
│   │       │   └── MockupPipeline.tsx  # iframe 임베드 + postMessage 리스너
│   │       └── ...                 # SpecViewer, ChatPanel, CodeGenPanel 등
│   └── package.json
├── pfy-front/                      # Mockup 런타임 (Vue + PrimeVue)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── mockup/MockupBuilder.vue  # 다크 테마 오버라이드 + postMessage
│   │   │   └── generated/              # scaffolding이 생성한 Vue 파일
│   │   ├── components/             # CPMS 공통 컴포넌트 (SearchForm, DataTable 등)
│   │   ├── spec-source/            # interview-result 산출물 (InterviewNote.md 등)
│   │   └── router/
│   │       ├── index.ts            # 라우터 가드 완화 (NotFound fallback)
│   │       └── staticRoutes.ts     # scaffolding이 자동 등록하는 라우트 파일
│   ├── scaffolding/                # Express 서버 (MockupBuilder API)
│   │   └── src/
│   │       ├── server.ts           # 루트 .env 우선 로드
│   │       ├── utils/llmClient.ts  # USE_LLM_PROXY 분기 (gpt-5.4 프록시 or gpt-5.2 직접)
│   │       └── routes/             # ai-generate, scaffold, ai-annotate, interview-result
│   └── package.json
├── pfy_prompt/                     # LLM 참조 가이드
│   ├── BackendGuide/               # CPMS Spring Boot 가이드 (7 docs)
│   ├── FrontendGuide/              # CPMS Vue3 가이드 (12 docs)
│   ├── masterPrompt.md             # Mockup → Spec 생성 마스터 프롬프트
│   ├── namebook.md / CPMS_namebook.md
│   └── componentCatalog.md         # pfy-front 컴포넌트 목록
├── skeleton/                       # Docker 프로젝트 템플릿
│   ├── backend/ frontend/ db/
│   └── docker-compose.yml
├── docs/superpowers/
│   ├── specs/                      # 설계 스펙 문서
│   └── plans/                      # 구현 계획 문서
├── logs/                           # 실행 로그 (gitignored)
├── .env.example / .env             # LLM/게이트웨이 설정 (루트 통합)
├── start.sh / stop.sh              # 4개 서버 기동/종료
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
| POST | `/api/mockup/brief` | Brief 저장 (4단계 플로우 진입점, 현재 미사용) | JSON |
| POST | `/api/mockup/generate-mockup` | Vue SFC 스트리밍 생성 (현재 미사용) | SSE |
| POST | `/api/mockup/parse-interview` | 인터뷰 원문 → InterviewNote (현재 미사용) | JSON |
| POST | `/api/mockup/generate-spec` | spec.md 스트리밍 (현재 미사용) | SSE |
| **POST** | **`/api/mockup/generate-spec-from-builder`** | **MockupBuilder spec-source 파일 → spec.md (실제 사용)** | JSON |
| POST | `/api/mockup/reset` | MockupState 초기화 | JSON |

### LLM Proxy (scaffolding용)

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| POST | `/api/llm/chat-completion` | OpenAI chat 포맷 프록시 → llm_client(gpt-5.4) | JSON |

### 공통 / Code Generation

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| GET | `/api/session` | 세션 상태 조회 | JSON |
| POST | `/api/codegen/generate` | 코드 생성 | SSE |
| POST | `/api/codegen/deploy` | Docker 빌드 & 실행 | SSE |
| POST | `/api/codegen/stop` | 컨테이너 중지 | JSON |
| GET | `/api/codegen/download` | 코드 ZIP 다운로드 | File |
| GET | `/api/codegen/files` | 생성된 파일 목록 | JSON |

### MockupBuilder scaffolding API (port 4000, iframe이 직접 호출)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/ai-generate` | 화면 제목 → 필드 자동 추천 |
| POST | `/api/scaffold` | Page Spec JSON → Vue 파일 생성 + 라우터 등록 |
| POST | `/api/generate` | MockupBuilder의 통합 생성 엔드포인트 |
| POST | `/api/ai-interview-questions` | 인터뷰 질문 10개 생성 |
| POST | `/api/ai-annotate` | UI 요소별 구조화 주석 삽입 |
| POST | `/api/generate-interview-result` | 답변 → InterviewNote.md + Component.vue + metadata.json |

## 설정값

| 환경변수 | 기본값 | 설명 |
|---------|--------|------|
| `LLM_PROVIDER` | azure_openai | LLM 제공자 (anthropic/azure_openai/openai) |
| `AZURE_OPENAI_MODEL_NAME` | gpt-5.4 | 텍스트 스펙 생성/QA 모델 |
| `CODEX_AZURE_OPENAI_MODEL_NAME` | gpt-5.3-codex | 코드 생성 모델 |
| `USE_LLM_PROXY` | false | scaffolding의 LLM 호출 경로 선택 (true=백엔드 프록시, false=직접) |
| `AOAI_ENDPOINT` | (사내 gpt-5.2 URL) | scaffolding이 직접 호출할 LLM 엔드포인트 |
| `AOAI_API_KEY` | - | scaffolding용 AOAI 키 |
| `AOAI_DEPLOYMENT` | gpt-5.2 | scaffolding이 사용할 모델 이름 |
| `MOCKUP_AOAI_ENDPOINT` | - | 백엔드 mockup_client 전용 게이트웨이 (설정 없으면 llm_client로 fallback) |
| `MAX_LLM_CALLS_PER_SESSION` | 200 | 세션당 최대 LLM 호출 수 |
| `SESSION_TTL_HOURS` | 2 | 세션 만료 시간 |
| `CODEGEN_MAX_TOKENS` | 16384 | 코드 생성 최대 출력 토큰 |
| `DOCKER_WORKSPACE_DIR` | /tmp/codegen_workspaces | Docker 작업 디렉토리 |
| `DOCKER_TIMEOUT_SECONDS` | 300 | Docker 빌드 타임아웃 |
| `DOCKER_MAX_FIX_RETRIES` | 3 | 컴파일 에러 자동 수정 최대 시도 |

## 변경 이력 (최근)

- **원본 pfy-front MockupBuilder iframe 통합**: 자체 구현 6단계 스텝퍼를 버리고 원본 MockupBuilder.vue를 iframe으로 임베드. 페이지 생성 → 자동 iframe 전환 → 인터뷰 → 자동 spec.md 생성까지 `postMessage` 기반으로 원활하게 연결
- **scaffolding Express 서버(:4000) 추가**: MockupBuilder의 AI 기능(`ai-generate`, `ai-annotate`, `ai-interview-questions`, `generate-interview-result`) 지원. `start.sh`가 4개 서버 동시 기동
- **LLM 프록시(`/api/llm/chat-completion`)**: scaffolding이 사내 게이트웨이 대신 우리 백엔드(gpt-5.4)를 경유하도록 선택 가능 → VPN 없어도 동작
- **루트 `.env`로 통합**: scaffolding `.env` 제거, 모든 LLM 설정을 프로젝트 루트 `.env`에서 관리
- **포트 정렬**: pfy-front Vue dev 서버 8081 → 8085 (main vite.config에 맞춤)
- **다크 테마**: MockupBuilder에 CSS variables + PrimeVue `:deep()` 오버라이드로 메인 앱 스타일(검은 배경 + 주황 포인트) 적용. 버튼 활성/비활성 명확히 구분
- **라우터 가드 완화**: 존재하지 않는 경로로 이동 시 bootstrap crash 문제 수정 → NotFound 라우트로 fallback
