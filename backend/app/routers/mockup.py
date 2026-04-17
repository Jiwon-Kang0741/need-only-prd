"""Mockup pipeline router: AI-driven mockup → annotation → interview → spec."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.llm.mockup_pipeline import mockup_pipeline
from app.models import MockupState
from app.session import get_session_id, session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mockup", tags=["mockup"])


# ------------------------------------------------------------------ request models

class AiGenerateRequest(BaseModel):
    title: str
    page_type: str = "list"
    description: str | None = None


class ScaffoldRequest(BaseModel):
    screen_id: str
    screen_name: str
    page_type: str = "list-detail"
    fields: list[dict]
    tabs: list[dict] | None = None


class InterviewResultRequest(BaseModel):
    answers: list[dict] | None = None
    raw_interview_text: str | None = None


# ------------------------------------------------------------------ helpers

def _get_session(session_id: str):
    session = session_store.get_or_create(session_id)
    return session


def _get_mockup_state(session_id: str) -> MockupState:
    session = session_store.get(session_id)
    if not session or not session.mockup_state:
        raise HTTPException(status_code=400, detail="No mockup state found. Call /ai-generate or /scaffold first.")
    return session.mockup_state


def _sse_msg(type: str, **kwargs) -> dict:
    return {"event": "message", "data": json.dumps({"type": type, **kwargs})}


# ------------------------------------------------------------------ 1. AI Generate

@router.post("/ai-generate")
async def ai_generate(
    body: AiGenerateRequest,
    session_id: str = Depends(get_session_id),
):
    """화면 제목 → AI가 필드/컬럼 설계 JSON 생성 후 세션에 MockupState 초기화."""
    session = _get_session(session_id)

    session_store.increment_llm_calls(session_id)
    result = await mockup_pipeline.ai_generate(
        title=body.title,
        page_type=body.page_type,
        description=body.description,
    )

    # Initialise MockupState from AI result
    fields = result.get("fields", [])
    tabs = result.get("tabs", None)
    screen_id = result.get("screen_id", body.title.lower().replace(" ", "_"))
    screen_name = result.get("screen_name", body.title)

    session.mockup_state = MockupState(
        screen_id=screen_id,
        screen_name=screen_name,
        page_type=body.page_type,
        fields=fields,
        tabs=tabs,
        current_step=1,
    )
    session.spec_source = "mockup"
    session_store.save(session_id)

    return {
        "screen_id": screen_id,
        "screen_name": screen_name,
        "page_type": body.page_type,
        "fields": fields,
        "tabs": tabs,
        **{k: v for k, v in result.items() if k not in ("screen_id", "screen_name", "fields", "tabs")},
    }


# ------------------------------------------------------------------ 2. Scaffold

@router.post("/scaffold")
async def scaffold(
    body: ScaffoldRequest,
    session_id: str = Depends(get_session_id),
):
    """필드 정의 → Vue 코드 생성 (LLM 없음) 후 세션 저장."""
    session = _get_session(session_id)

    vue_code = mockup_pipeline.scaffold(
        screen_id=body.screen_id,
        screen_name=body.screen_name,
        page_type=body.page_type,
        fields=body.fields,
        tabs=body.tabs,
    )

    # Update or create MockupState
    if session.mockup_state is None:
        session.mockup_state = MockupState(
            screen_id=body.screen_id,
            screen_name=body.screen_name,
            page_type=body.page_type,
            fields=body.fields,
            tabs=None,
            current_step=2,
        )
    else:
        session.mockup_state.screen_id = body.screen_id
        session.mockup_state.screen_name = body.screen_name
        session.mockup_state.page_type = body.page_type
        session.mockup_state.fields = body.fields
        session.mockup_state.current_step = 2

    session.mockup_state.vue_code = vue_code
    session.spec_source = "mockup"
    session_store.save(session_id)

    return {"vue_code": vue_code}


# ------------------------------------------------------------------ 3. AI Annotate

@router.post("/ai-annotate")
async def ai_annotate(
    session_id: str = Depends(get_session_id),
):
    """세션의 vue_code → AI 주석 분석 → annotation_markdown 저장."""
    session = session_store.get_or_create(session_id)
    mockup_state = _get_mockup_state(session_id)

    if not mockup_state.vue_code:
        raise HTTPException(status_code=400, detail="No vue_code in mockup state. Call /scaffold first.")

    session_store.increment_llm_calls(session_id)
    annotated_code, annotations, annotation_markdown = await mockup_pipeline.ai_annotate(
        vue_code=mockup_state.vue_code,
    )

    mockup_state.annotations = annotations
    mockup_state.annotation_markdown = annotation_markdown
    mockup_state.vue_code = annotated_code
    mockup_state.current_step = 3
    session_store.save(session_id)

    return {
        "annotation_markdown": annotation_markdown,
        "annotations": annotations,
    }


# ------------------------------------------------------------------ 4. AI Interview

@router.post("/ai-interview")
async def ai_interview(
    session_id: str = Depends(get_session_id),
):
    """annotation_markdown → AI 인터뷰 질문 10개 생성."""
    mockup_state = _get_mockup_state(session_id)

    if not mockup_state.annotation_markdown:
        raise HTTPException(status_code=400, detail="No annotation_markdown. Call /ai-annotate first.")

    session_store.increment_llm_calls(session_id)
    questions = await mockup_pipeline.ai_interview(
        title=mockup_state.screen_name,
        annotation_markdown=mockup_state.annotation_markdown,
        vue_source=mockup_state.vue_code,
    )

    mockup_state.interview_questions = questions
    mockup_state.current_step = 4
    session_store.save(session_id)

    return {"questions": questions}


# ------------------------------------------------------------------ 5. Interview Result

@router.post("/interview-result")
async def interview_result(
    body: InterviewResultRequest,
    session_id: str = Depends(get_session_id),
):
    """인터뷰 답변 → interview_note_md + spec_markdown 생성 후 세션 저장."""
    session = session_store.get_or_create(session_id)
    mockup_state = _get_mockup_state(session_id)

    if not mockup_state.annotation_markdown:
        raise HTTPException(status_code=400, detail="No annotation_markdown. Call /ai-annotate first.")

    session_store.increment_llm_calls(session_id)
    interview_note_md, spec_markdown = await mockup_pipeline.interview_result(
        title=mockup_state.screen_name,
        annotation_markdown=mockup_state.annotation_markdown,
        vue_source=mockup_state.vue_code,
        questions=mockup_state.interview_questions,
        answers=body.answers,
        raw_interview_text=body.raw_interview_text,
    )

    mockup_state.interview_note_md = interview_note_md
    if body.answers:
        mockup_state.interview_answers = body.answers
    if body.raw_interview_text:
        mockup_state.raw_interview_text = body.raw_interview_text
    mockup_state.current_step = 5

    session.spec_markdown = spec_markdown
    session.spec_version += 1
    session_store.save(session_id)

    return {
        "interview_note_md": interview_note_md,
        "spec_version": session.spec_version,
    }


# ------------------------------------------------------------------ 6. Generate Spec (SSE)

@router.post("/generate-spec")
async def generate_spec(
    request: Request,
    session_id: str = Depends(get_session_id),
):
    """interview_note_md + annotation_markdown → spec Markdown SSE 스트리밍."""
    session = session_store.get_or_create(session_id)
    mockup_state = _get_mockup_state(session_id)

    if not mockup_state.annotation_markdown:
        raise HTTPException(status_code=400, detail="No annotation_markdown. Call /ai-annotate first.")
    if not mockup_state.interview_note_md:
        raise HTTPException(status_code=400, detail="No interview_note_md. Call /interview-result first.")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            yield _sse_msg("status", content="Generating spec from mockup interview...")

            session_store.increment_llm_calls(session_id)
            full_spec = ""
            async for chunk in mockup_pipeline.generate_spec_streaming(
                title=mockup_state.screen_name,
                annotation_markdown=mockup_state.annotation_markdown,
                interview_note_md=mockup_state.interview_note_md,
                vue_source=mockup_state.vue_code,
            ):
                full_spec += chunk
                yield _sse_msg("chunk", content=chunk)

            session.spec_markdown = full_spec
            session.spec_version += 1
            mockup_state.current_step = 6
            session_store.save(session_id)

            yield _sse_msg("complete", spec_version=session.spec_version)

        except HTTPException as e:
            yield _sse_msg("error", content=e.detail)
        except Exception as e:
            logger.exception("generate-spec SSE error")
            yield _sse_msg("error", content=str(e))

    return EventSourceResponse(event_generator(), ping=10)


# ------------------------------------------------------------------ 7. Annotate Constraints (optional)

@router.post("/annotate-constraints")
async def annotate_constraints(
    session_id: str = Depends(get_session_id),
):
    """annotation_markdown의 constraints를 LLM으로 보강 (optional step)."""
    mockup_state = _get_mockup_state(session_id)

    if not mockup_state.annotation_markdown:
        raise HTTPException(status_code=400, detail="No annotation_markdown. Call /ai-annotate first.")

    from app.llm.client import llm_client

    system_prompt = (
        "You are a business analyst. Review the mockup annotations below and enrich the constraints column "
        "with specific validation rules, business rules, and UX constraints. "
        "Return the same Markdown table with the constraints column enriched. "
        "Do not add new rows or change other columns."
    )
    user_prompt = f"Annotations:\n\n{mockup_state.annotation_markdown}"

    session_store.increment_llm_calls(session_id)
    enriched_markdown = await llm_client.complete(system_prompt, user_prompt, stream=False)

    mockup_state.annotation_markdown = enriched_markdown
    session_store.save(session_id)

    return {"annotation_markdown": enriched_markdown}
