# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**need-only-prd** is an LLM-powered PRD (Product Requirements Document) generator. Users paste raw requirements text, the app extracts structured requirements via LLM, generates a technical spec as streaming Markdown, then supports iterative refinement through chat and coverage validation.

## Development Commands

### Backend (FastAPI + Python 3.11+)

```bash
cd backend
source .venv/bin/activate      # venv already exists
pip install -e ".[dev]"        # install with dev deps (pytest, etc.)
uvicorn app.main:app --reload  # runs on :8000

# Tests
pytest                         # all tests
pytest tests/test_routers.py   # single test file
pytest -k "test_name"          # single test by name
```

Configuration via `.env` file in project root (see `.env.example`). Key vars: `LLM_PROVIDER` (anthropic|openai), `LLM_MODEL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`.

### Frontend (React 19 + Vite + Tailwind v4)

```bash
cd frontend
npm install
npm run dev    # runs on :5173, proxies /api to :8000
npm run build  # type-check + production build
npm run lint   # eslint
```

## Architecture

### Request Flow

1. User submits raw text via `POST /api/input` (stored in in-memory session)
2. `POST /api/generate` triggers a two-step LLM pipeline via SSE:
   - **Extract**: raw text -> structured requirements JSON (non-streaming)
   - **Generate**: requirements -> Markdown spec (streaming chunks)
3. User refines spec via `POST /api/chat` which streams a full spec rewrite incorporating feedback
4. `GET /api/validate` scores how well the spec covers the original requirements

All endpoints require `X-Session-ID` header. Frontend generates a UUID per browser tab via `sessionStorage`.

### Backend Structure

- **`app/session.py`** — In-memory `SessionStore` (dict-based, no DB). Sessions auto-expire based on `SESSION_TTL_HOURS`. Each session tracks raw input, extracted requirements, spec markdown, chat history, and LLM call count (capped at `MAX_LLM_CALLS_PER_SESSION`).
- **`app/llm/client.py`** — Unified `LLMClient` supporting both Anthropic and OpenAI APIs with streaming/non-streaming modes. Provider selected at startup via config.
- **`app/llm/pipeline.py`** — `SpecPipeline` orchestrates the four LLM operations: extract, generate, refine, validate.
- **`app/llm/prompts.py`** — All LLM prompt templates.
- **`app/routers/`** — FastAPI routers: `input`, `spec` (generate/get), `chat`, `validate`, `export`, `session` (get/restore/delete).

### Frontend Structure

- **`src/store/sessionStore.ts`** — Zustand store. Central state for the entire app: raw input, spec, chat messages, validation, generation status. SSE event handling is wired directly into store actions.
- **`src/api/client.ts`** — API client with SSE consumption helper (`consumeSSE`). All requests include `X-Session-ID` from `sessionStorage`.
- **`src/components/`** — `InputPanel` (initial text entry), `SpecViewer` (rendered Markdown), `ChatPanel` (refinement chat), `CompareView` (side-by-side), `CoverageScore`, `ExportButton`.

### Key Patterns

- **SSE streaming**: Spec generation and chat refinement use SSE (via `sse-starlette`). Event types: `status`, `chunk`, `requirements`, `complete`, `error`. Frontend consumes with a manual `ReadableStream` reader, not `EventSource`.
- **Session lifecycle**: No auth/DB. Sessions are ephemeral in-memory dicts keyed by UUID. A background task cleans expired sessions every 10 minutes.
- **LLM provider abstraction**: `LLMClient` wraps both Anthropic and OpenAI behind `complete(system, user, stream)`. Switching providers only requires changing env vars.
