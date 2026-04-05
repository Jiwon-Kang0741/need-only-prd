# Need Only PRD

LLM 기반 PRD(Product Requirements Document) 자동 생성기 + 멀티에이전트 코드 생성 시스템

비정형 텍스트(회의록, 이메일, 채팅 로그)를 입력하면 구조화된 기술 스펙을 생성하고, 채팅으로 반복 수정한 뒤, Spring Boot + Vue3 소스 코드까지 자동 생성하여 Docker로 실행할 수 있습니다.

## 주요 기능

### Spec 생성 파이프라인
- 비정형 텍스트에서 구조화된 요구사항 자동 추출
- 요구사항 기반 기술 스펙(Markdown) 실시간 스트리밍 생성
- 채팅 기반 스펙 반복 수정 (히스토리 자동 요약)
- 요구사항 커버리지 검증 (점수 + 누락 항목)
- 스펙 이전/이후 비교 뷰
- Markdown 파일 다운로드

### 멀티에이전트 코드 생성
- 7단계 에이전트 파이프라인으로 Spring Boot + Vue3 코드 자동 생성
- CPMS 프레임워크 코딩 가이드 기반 코드 품질 보장
- 3단계 방어 체계: 생성 시 DO NOT 규칙 / 정적 검사 / LLM QA 검증
- 생성된 코드를 Docker 컨테이너로 즉시 빌드 & 실행
- 컴파일 에러 자동 수정 (최대 3회 재시도)
- ZIP 다운로드 지원

## 기술 스택

| 구분 | 기술 |
|------|------|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS v4, Zustand, react-markdown |
| Backend | FastAPI, Python 3.11+, sse-starlette, pydantic-settings |
| LLM | Azure OpenAI (gpt-5.4, gpt-5.3-codex), Anthropic, OpenAI 지원 |
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
# .env 파일 생성
cp .env.example .env
# .env에 API 키 설정
```

`.env` 주요 설정:

```env
LLM_PROVIDER=azure_openai

# Azure OpenAI (스펙 생성 + QA)
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_MODEL_NAME=gpt-5.4

# Azure OpenAI Codex (코드 생성)
CODEX_AZURE_OPENAI_ENDPOINT=https://your-codex-resource.cognitiveservices.azure.com
CODEX_AZURE_OPENAI_API_KEY=your-codex-key
CODEX_AZURE_OPENAI_MODEL_NAME=gpt-5.3-codex
```

### 실행

```bash
# 간편 실행
./start.sh     # Backend :8001 + Frontend :5173
./stop.sh      # 종료

# 또는 수동 실행
# Backend
cd backend
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8001

# Frontend
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속

### 테스트

```bash
cd backend
source .venv/bin/activate
pytest                         # 전체 테스트 (37개)
pytest tests/test_routers.py   # 라우터 테스트
pytest -k "test_name"          # 단일 테스트

cd frontend
npm run build                  # 타입 체크 + 프로덕션 빌드
npm run lint                   # ESLint
```

## 아키텍처

### 전체 흐름

```
[사용자 입력]
    |
    v
[Spec Pipeline] ---- llm_client (gpt-5.4) ----> 스펙 생성/수정/검증
    |
    v
[Code Generation Pipeline] ---- codex_client (gpt-5.3-codex) ----> 코드 생성
    |                           ---- llm_client (gpt-5.4) --------> QA/Fix
    v
[Docker Deploy] ----> 빌드 & 실행 (MariaDB + Spring Boot + Vue3)
```

### Spec Pipeline

```
POST /api/input (텍스트 제출)
    -> POST /api/spec/generate (SSE: 요구사항 추출 -> 스펙 생성)
    -> POST /api/chat (SSE: 채팅으로 스펙 수정)
    -> POST /api/validate (커버리지 검증)
    -> GET /api/export (Markdown 다운로드)
```

### 코드 생성 파이프라인 (7단계)

```
Phase 1: Planner .............. 스펙 분석 -> 파일 생성 계획 (codex)
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

## 프로젝트 구조

```
need-only-prd/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 앱 + 7개 라우터
│   │   ├── config.py               # pydantic-settings (.env 로딩)
│   │   ├── session.py              # 인메모리 + 디스크 세션 관리
│   │   ├── models.py               # Pydantic 모델 (Session, CodeGen, etc.)
│   │   ├── docker_manager.py       # Docker workspace 관리 + 빌드/실행
│   │   ├── llm/
│   │   │   ├── client.py           # LLMClient (gpt-5.4) + CodexLLMClient (codex)
│   │   │   ├── pipeline.py         # SpecPipeline (extract/generate/refine/validate)
│   │   │   ├── prompts.py          # 스펙 생성 프롬프트
│   │   │   ├── agents.py           # 7개 에이전트 + static_check()
│   │   │   ├── orchestrator.py     # CodeGenOrchestrator (async generator)
│   │   │   ├── codegen_context.py  # 가이드 파일 로더 (섹션별 분할)
│   │   │   └── codegen_prompts.py  # 코드 생성 프롬프트
│   │   └── routers/                # input, spec, chat, validate, export, session, codegen
│   └── tests/                      # pytest (37 tests)
├── frontend/
│   ├── src/
│   │   ├── App.tsx                 # 루트 (입력 화면 / 스펙+코드생성 화면 전환)
│   │   ├── index.css               # M3 색상 테마 (53 토큰)
│   │   ├── api/client.ts           # API 클라이언트 + SSE consumeSSE()
│   │   ├── store/sessionStore.ts   # Zustand 중앙 상태 관리
│   │   ├── types/index.ts          # TypeScript 타입 정의
│   │   └── components/             # 11개 컴포넌트
│   └── package.json
├── pfy_prompt/                     # LLM 참조 가이드
│   ├── BackendGuide/               # CPMS Spring Boot 코딩 가이드 (7 docs)
│   ├── FrontendGuide/              # CPMS Vue3 코딩 가이드 (12 docs)
│   ├── namebook.md                 # 네이밍 컨벤션
│   └── CPMS_namebook.md            # CPMS 클래스/패키지 네이밍
├── skeleton/                       # Docker 프로젝트 템플릿
│   ├── backend/                    # Spring Boot 기본 프로젝트
│   ├── frontend/                   # Vue3 기본 프로젝트
│   ├── db/init.sql                 # MariaDB 초기화
│   └── docker-compose.yml
├── .env.example
├── start.sh / stop.sh
└── CLAUDE.md
```

## API 엔드포인트

모든 요청에 `X-Session-ID` 헤더 필요 (UUID, sessionStorage 저장)

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| POST | `/api/input` | 원문 텍스트 제출 | JSON |
| POST | `/api/spec/generate` | 스펙 생성 | SSE |
| GET | `/api/spec` | 현재 스펙 조회 | JSON |
| POST | `/api/chat` | 채팅으로 스펙 수정 | SSE |
| POST | `/api/validate` | 커버리지 검증 | JSON |
| GET | `/api/export` | spec.md 다운로드 | File |
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
