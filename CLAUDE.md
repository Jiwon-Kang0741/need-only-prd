# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**need-only-prd** is an LLM-powered PRD generator with multi-agent code generation. Users paste raw requirements → LLM extracts structured requirements → generates technical spec as streaming Markdown → iterative refinement via chat → validates coverage → generates Spring Boot + Vue3 source code → deploys to Docker.

## Development Commands

### Backend (FastAPI + Python 3.11+)

```bash
cd backend
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload  # runs on :8001

pytest                         # all tests (37 tests)
pytest tests/test_routers.py   # single file
pytest -k "test_name"          # single test
```

### Frontend (React 19 + Vite + Tailwind v4)

```bash
cd frontend
npm install
npm run dev    # runs on :5173, proxies /api to :8001
npm run build  # type-check + production build
npm run lint
```

### Quick Start

```bash
./start.sh     # starts backend :8001 + frontend :5173
./stop.sh      # stops both
```

Configuration via `.env` in project root (see `.env.example`). Key vars: `LLM_PROVIDER` (anthropic|azure_openai|openai), `AZURE_OPENAI_*`, `CODEX_AZURE_OPENAI_*`.

## Architecture

### Two Main Pipelines

**1. Spec Pipeline** (`app/llm/pipeline.py` + `app/llm/prompts.py`):
- Input → Extract requirements (non-streaming) → Generate spec (streaming SSE) → Chat refine → Validate coverage
- Uses `llm_client` (gpt-5.4 via Azure OpenAI Chat Completions API)

**2. Code Generation Pipeline** (`app/llm/orchestrator.py` + `app/llm/agents.py`):
- 7-phase async generator yielding SSE events:
  1. **Planner** → file generation plan JSON (codex)
  2. **Data Engineer** → SQL schema + TypeScript types (codex, streaming)
  3. **Backend Engineer** → DTOs, DAOs, Services, Mapper XMLs (codex, streaming)
  4. **Frontend Engineer** → single consolidated Vue3 page (codex, streaming)
  5. **Static Check** → regex-based validation, no LLM (UUID, scrollHeight, etc.)
  6. **Backend QA + Frontend QA** → parallel guide-based review (gpt-5.4)
  7. **Fix Agent** → applies QA fixes (gpt-5.4, only if issues found)
- Uses `codex_client` (gpt-5.3-codex via Azure Responses API) for generation, `llm_client` for QA/fix

### Model Routing

| Purpose | Client | Model | API |
|---------|--------|-------|-----|
| Spec generation, QA, Fix | `llm_client` | gpt-5.4 | Chat Completions |
| Code generation (Planner, Engineers) | `codex_client` | gpt-5.3-codex | Responses API |

### Session Management

- `app/session.py` — In-memory dict + JSON disk persistence (`.sessions/`)
- `X-Session-ID` header on all requests; frontend stores UUID in `sessionStorage`
- Auto-expires after `SESSION_TTL_HOURS` (default 2h), cleanup every 10min
- LLM call counter per session (default max 200)

### Backend Key Files

- `app/llm/client.py` — `LLMClient` (Anthropic/OpenAI/Azure) + `CodexLLMClient` (Responses API); codex falls back to llm_client if keys missing
- `app/llm/agents.py` — All agent classes + `static_check()` regex validator + `AGENT_METAS`
- `app/llm/orchestrator.py` — `CodeGenOrchestrator.run()` async generator, wires all phases
- `app/llm/codegen_context.py` — Loads `pfy_prompt/BackendGuide/` and `FrontendGuide/` markdown files, splits by `##` headings for selective injection (avoids 400KB+ context)
- `app/docker_manager.py` — Copies `skeleton/` → writes generated files → `docker compose up` → port allocation (base 18000 + session offset)
- `app/routers/codegen.py` — SSE endpoints for generate, deploy, stop, download ZIP; auto-fix loop (up to 3 retries on build errors)

### Frontend Key Files

- `src/store/sessionStore.ts` — Zustand store with all app state + SSE event handlers wired into actions
- `src/api/client.ts` — `consumeSSE()` manually parses `data: {JSON}` via ReadableStream reader (not EventSource)
- `src/components/CodeGenPanel.tsx` — Dark terminal-themed panel with 4 status states (idle/generating/generated/error)
- `src/index.css` — Material Design 3 color theme (53 tokens), Manrope + Inter fonts

### SSE Event Types

Spec pipeline: `status`, `chunk`/`text`, `requirements`, `complete`, `error`
Code generation: above + `plan`, `file_start`, `file_complete`, `log`, `agent_start`, `agent_complete`

### Code Generation Constraints

Generated files target CPMS framework (Spring Boot + MyBatis + Vue3 + PrimeVue):

**10 file types**: dto_request, dto_response, dao, dao_impl, service, service_impl, mapper_xml, db_init_sql, vue_types, vue_page

**Critical rules baked into prompts**:
- No `java.util.UUID` (MyBatis has no TypeHandler) — use String
- No `scrollHeight="flex"` — use `scrollHeight="540px"` + virtualScrollerOptions
- No date formatting in template slots — pre-format in watch() + nextTick()
- Vue page must be single file with SearchForm, DataTable, SumGrid inline
- Backend: `@ServiceId("ScreenCode/method")` + `@ServiceName("설명")` on every public method
- Mapper XML: CDATA for `<`/`>`, `<if test>` for optional params

### Docker Deployment

- `skeleton/` contains base Spring Boot + Vue3 project template
- `docker_manager.py` copies skeleton → injects generated files → builds via `docker compose`
- 3 containers per session: MariaDB, Spring Boot backend, Vue3 frontend
- Build errors trigger auto-fix: `QAEngineerAgent.fix_file()` up to `DOCKER_MAX_FIX_RETRIES` (3)

### Reference Guides

- `pfy_prompt/BackendGuide/` — CPMS Spring Boot/MyBatis coding conventions (7 docs)
- `pfy_prompt/FrontendGuide/` — CPMS Vue3/PrimeVue conventions (12 docs + error patterns)
- `pfy_prompt/namebook.md` + `CPMS_namebook.md` — Class/package naming patterns
- These are loaded by `codegen_context.py` and injected into agent prompts
