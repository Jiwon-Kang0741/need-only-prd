"""Mockup pipeline router: AI-driven mockup → annotation → interview → spec."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.llm.mockup_pipeline import mockup_pipeline
from app.models import MockupState
from app.session import get_session_id, session_store

# pfy-front 프로젝트 경로 (Vue dev server가 hot-reload할 디렉토리)
_PFY_FRONT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "pfy-front"
_PFY_PAGES_GENERATED = _PFY_FRONT_ROOT / "src" / "pages" / "generated"
_PFY_STATIC_ROUTES = _PFY_FRONT_ROOT / "src" / "router" / "staticRoutes.ts"

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


def _infer_ui_type(data_type: str | None) -> str:
    """DB dataType → UI type 매핑 (VARCHAR→text, NUMBER→number, DATETIME→date)."""
    if not data_type:
        return "text"
    dt = data_type.upper()
    if "NUM" in dt or "INT" in dt or "DEC" in dt:
        return "number"
    if "DATE" in dt or "TIME" in dt:
        return "date"
    return "text"


def _parse_options_text(options_text: str | None) -> list[dict] | None:
    """'Y:사용, N:미사용' 형식 → [{label, value}] 변환."""
    if not options_text or not isinstance(options_text, str):
        return None
    items = []
    for pair in options_text.split(","):
        pair = pair.strip()
        if ":" in pair:
            value, label = pair.split(":", 1)
            items.append({"value": value.strip(), "label": label.strip()})
    return items or None


def _normalize_ai_result(result: dict) -> list[dict]:
    """LLM의 searchFields/tableColumns/formFields → FieldDef 리스트로 통합.

    - searchFields → searchable=True
    - tableColumns → listable=True, detailable=True, type은 dataType에서 추론
    - formFields → editable=True, detailable=True
    - 같은 key는 병합 (플래그 합침)
    """
    merged: dict[str, dict] = {}

    for f in result.get("searchFields") or []:
        key = f.get("key")
        if not key:
            continue
        entry = merged.setdefault(key, {"key": key, "label": f.get("label", key)})
        entry["type"] = f.get("type") or entry.get("type") or "text"
        entry["searchable"] = True
        opts = _parse_options_text(f.get("optionsText"))
        if opts:
            entry["options"] = opts

    for f in result.get("tableColumns") or []:
        key = f.get("key")
        if not key:
            continue
        entry = merged.setdefault(key, {"key": key, "label": f.get("label", key)})
        if "type" not in entry:
            entry["type"] = _infer_ui_type(f.get("dataType"))
        entry["listable"] = True
        entry["detailable"] = True

    for f in result.get("formFields") or []:
        key = f.get("key")
        if not key:
            continue
        entry = merged.setdefault(key, {"key": key, "label": f.get("label", key)})
        entry["type"] = f.get("type") or entry.get("type") or "text"
        entry["editable"] = True
        entry["detailable"] = True
        if f.get("required"):
            entry["required"] = True
        opts = _parse_options_text(f.get("optionsText"))
        if opts:
            entry["options"] = opts

    return list(merged.values())


def _write_vue_to_pfy_front(screen_id: str, vue_code: str) -> str | None:
    """pfy-front/src/pages/generated/ 에 Vue 파일 저장 + staticRoutes.ts에 경로 등록."""
    try:
        sid = screen_id.lower()
        page_dir = _PFY_PAGES_GENERATED / sid
        page_dir.mkdir(parents=True, exist_ok=True)

        # Vue 파일 저장
        vue_file = page_dir / "index.vue"
        vue_file.write_text(vue_code, encoding="utf-8")

        # 메타 저장
        meta = {
            "screenId": screen_id.upper(),
            "screenName": screen_id,
            "pageType": "list-detail",
            "routePath": f"/{screen_id.upper()}",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        meta_file = page_dir / "scaffold-meta.json"
        meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        # staticRoutes.ts에 라우트 추가 (NotFound 앞에 삽입)
        route_path = f"/{screen_id.upper()}"
        route_name = screen_id.upper()

        if _PFY_STATIC_ROUTES.exists():
            content = _PFY_STATIC_ROUTES.read_text(encoding="utf-8")
            # 이미 등록되어 있으면 스킵
            if f"name: '{route_name}'" not in content:
                route_entry = (
                    f"    {{\n"
                    f"      path: '{route_path}',\n"
                    f"      name: '{route_name}',\n"
                    f"      meta: {{ menuId: '{route_name}', generated: true }},\n"
                    f"      component: () => import('@/pages/generated/{sid}/index.vue'),\n"
                    f"    }},\n"
                )
                # NotFound 라우트 앞에 삽입
                not_found_marker = "path: '/:pathMatch(.*)*'"
                idx = content.find(not_found_marker)
                if idx != -1:
                    # 해당 객체 시작 위치 (여는 중괄호) 찾기
                    brace_idx = content.rfind("{", 0, idx)
                    if brace_idx != -1:
                        # 앞의 공백 포함하여 삽입
                        line_start = content.rfind("\n", 0, brace_idx) + 1
                        content = content[:line_start] + route_entry + content[line_start:]
                        _PFY_STATIC_ROUTES.write_text(content, encoding="utf-8")

            logger.info("[scaffold] Wrote %s → %s, route: %s", vue_file, route_path, route_name)
        return route_path
    except Exception as e:
        logger.warning("[scaffold] Failed to write to pfy-front: %s", e)
        return None


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

    # Initialise MockupState from AI result — normalize search/table/form into FieldDef list
    normalized_fields = _normalize_ai_result(result)
    tabs = result.get("tabs", None)
    screen_id = result.get("screen_id", body.title.lower().replace(" ", "_"))
    screen_name = result.get("screen_name", body.title)

    session.mockup_state = MockupState(
        screen_id=screen_id,
        screen_name=screen_name,
        page_type=body.page_type,
        fields=normalized_fields,
        tabs=tabs,
        current_step=1,
    )
    session.spec_source = "mockup"
    session_store.save(session_id)

    return {
        "screen_id": screen_id,
        "screen_name": screen_name,
        "page_type": body.page_type,
        "fields": normalized_fields,
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

    # 방어: 필드에 'type' 키가 없으면 dataType으로부터 추론 (정규화되지 않은 필드 방어)
    safe_fields = [
        {
            **f,
            "type": f.get("type") or _infer_ui_type(f.get("dataType")),
        }
        for f in body.fields
    ]

    vue_code = mockup_pipeline.scaffold(
        screen_id=body.screen_id,
        screen_name=body.screen_name,
        page_type=body.page_type,
        fields=safe_fields,
        tabs=body.tabs,
    )

    # Update or create MockupState
    if session.mockup_state is None:
        session.mockup_state = MockupState(
            screen_id=body.screen_id,
            screen_name=body.screen_name,
            page_type=body.page_type,
            fields=safe_fields,
            tabs=None,
            current_step=2,
        )
    else:
        session.mockup_state.screen_id = body.screen_id
        session.mockup_state.screen_name = body.screen_name
        session.mockup_state.page_type = body.page_type
        session.mockup_state.fields = safe_fields
        session.mockup_state.current_step = 2

    session.mockup_state.vue_code = vue_code
    session.spec_source = "mockup"
    session_store.save(session_id)

    # pfy-front에 Vue 파일 저장 + 라우터 등록 (Vue dev server가 hot-reload)
    route_path = None
    if _PFY_FRONT_ROOT.exists():
        route_path = _write_vue_to_pfy_front(body.screen_id, vue_code)

    return {"vue_code": vue_code, "route_path": route_path}


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
