"""Mockup pipeline router (원본 pfy-front 4단계 플로우)."""
from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.llm.mockup_pipeline import mockup_pipeline
from app.models import MockupState
from app.session import get_session_id, session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mockup", tags=["mockup"])

_PFY_FRONT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "pfy-front"
_PFY_PAGES_GENERATED = _PFY_FRONT_ROOT / "src" / "pages" / "generated"
_PFY_STATIC_ROUTES = _PFY_FRONT_ROOT / "src" / "router" / "staticRoutes.ts"
_PFY_SPEC_SOURCE = _PFY_FRONT_ROOT / "src" / "spec-source"

_PROJECT_ID_RE = re.compile(r"^[A-Z0-9_]+$")
_SCREEN_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class BriefRequest(BaseModel):
    project_id: str
    project_name: str
    brief_md: str


class ParseInterviewRequest(BaseModel):
    raw_interview_text: str


class GenerateSpecFromBuilderRequest(BaseModel):
    screen_name: str
    page_name: str
    title: str
    page_type: str | None = None


def _require_mockup_state(session_id: str) -> MockupState:
    s = session_store.get(session_id)
    if s is None or s.mockup_state is None:
        raise HTTPException(400, "No mockup state. Call /api/mockup/brief first.")
    return s.mockup_state


def _write_vue_to_pfy_front(project_id: str, vue_code: str, project_name: str) -> str | None:
    try:
        pid = project_id.lower()
        page_dir = _PFY_PAGES_GENERATED / pid
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.vue").write_text(vue_code, encoding="utf-8")
        meta = {
            "screenId": project_id.upper(),
            "screenName": project_name,
            "pageType": "project-mockup",
            "routePath": f"/{project_id.upper()}",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        (page_dir / "scaffold-meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        route_path = f"/{project_id.upper()}"
        route_name = project_id.upper()
        if _PFY_STATIC_ROUTES.exists():
            content = _PFY_STATIC_ROUTES.read_text(encoding="utf-8")
            if f"name: '{route_name}'" not in content:
                entry = (
                    f"    {{\n"
                    f"      path: '{route_path}',\n"
                    f"      name: '{route_name}',\n"
                    f"      meta: {{ menuId: '{route_name}', generated: true }},\n"
                    f"      component: () => import('@/pages/generated/{pid}/index.vue'),\n"
                    f"    }},\n"
                )
                marker = "path: '/:pathMatch(.*)*'"
                idx = content.find(marker)
                if idx != -1:
                    brace_idx = content.rfind("{", 0, idx)
                    if brace_idx != -1:
                        line_start = content.rfind("\n", 0, brace_idx) + 1
                        content = content[:line_start] + entry + content[line_start:]
                        _PFY_STATIC_ROUTES.write_text(content, encoding="utf-8")
        return route_path
    except Exception as e:
        logger.warning("[mockup] Failed to write pfy-front: %s", e)
        return None


@router.post("/brief")
async def brief(body: BriefRequest, session_id: str = Depends(get_session_id)):
    if not _PROJECT_ID_RE.match(body.project_id):
        raise HTTPException(400, "project_id는 영문 대문자, 숫자, 언더스코어만 허용됩니다.")
    session = session_store.get_or_create(session_id)
    session.mockup_state = MockupState(
        project_id=body.project_id,
        project_name=body.project_name,
        brief_md=body.brief_md,
        current_step=1,
    )
    session.spec_source = "mockup"
    session_store.save(session_id)
    return {"project_id": body.project_id, "project_name": body.project_name, "current_step": 1}


@router.post("/generate-mockup")
async def generate_mockup(session_id: str = Depends(get_session_id)):
    ms = _require_mockup_state(session_id)
    if not ms.brief_md:
        raise HTTPException(400, "brief_md가 없습니다.")

    async def event_gen() -> AsyncGenerator[dict, None]:
        try:
            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Generating Mockup.vue..."})}
            session_store.increment_llm_calls(session_id)
            full = ""
            async for chunk in mockup_pipeline.generate_mockup_streaming(ms.brief_md):
                full += chunk
                yield {"event": "message", "data": json.dumps({"type": "chunk", "content": chunk})}

            cleaned = re.sub(r"^```(?:vue)?\s*", "", full.strip())
            cleaned = re.sub(r"```\s*$", "", cleaned).strip()

            ms.mockup_vue = cleaned
            ms.current_step = 2
            session_store.save(session_id)

            route_path = _write_vue_to_pfy_front(ms.project_id, cleaned, ms.project_name)

            yield {"event": "message", "data": json.dumps({"type": "complete", "route_path": route_path})}
        except HTTPException as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": e.detail})}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_gen(), ping=10)


@router.post("/parse-interview")
async def parse_interview(body: ParseInterviewRequest, session_id: str = Depends(get_session_id)):
    ms = _require_mockup_state(session_id)
    if not ms.mockup_vue:
        raise HTTPException(400, "mockup_vue가 없습니다. /generate-mockup을 먼저 호출하세요.")

    session_store.increment_llm_calls(session_id)
    interview_notes = await mockup_pipeline.parse_interview(ms.mockup_vue, body.raw_interview_text)
    ms.raw_interview_text = body.raw_interview_text
    ms.interview_notes_md = interview_notes
    ms.current_step = 3
    session_store.save(session_id)
    return {"interview_notes_md": interview_notes, "current_step": 3}


@router.post("/generate-spec")
async def generate_spec(session_id: str = Depends(get_session_id)):
    ms = _require_mockup_state(session_id)
    session = session_store.get(session_id)
    if not ms.brief_md or not ms.mockup_vue or not ms.interview_notes_md:
        raise HTTPException(400, "brief / mockup / interview 중 누락된 것이 있습니다.")

    async def event_gen() -> AsyncGenerator[dict, None]:
        try:
            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Generating spec.md..."})}
            session_store.increment_llm_calls(session_id)
            full = ""
            async for chunk in mockup_pipeline.generate_spec_streaming(
                ms.brief_md, ms.mockup_vue, ms.interview_notes_md,
            ):
                full += chunk
                yield {"event": "message", "data": json.dumps({"type": "chunk", "content": chunk})}

            session.spec_markdown = full
            session.spec_version += 1
            ms.current_step = 4
            session_store.save(session_id)

            yield {"event": "message", "data": json.dumps({"type": "complete", "spec_version": session.spec_version})}
        except HTTPException as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": e.detail})}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_gen(), ping=10)


@router.post("/reset")
async def reset(session_id: str = Depends(get_session_id)):
    s = session_store.get(session_id)
    if s:
        s.mockup_state = None
        s.spec_source = None
        session_store.save(session_id)
    return {"reset": True}


@router.post("/generate-spec-from-builder")
async def generate_spec_from_builder(
    body: GenerateSpecFromBuilderRequest,
    session_id: str = Depends(get_session_id),
):
    """scaffolding이 src/spec-source/{screen_name}/에 저장한 InterviewNote.md + Component.vue +
    metadata.json을 읽어 masterPrompt 기반 spec.md 생성 후 세션에 저장."""
    if not _SCREEN_NAME_RE.match(body.screen_name):
        raise HTTPException(400, "screen_name은 영문/숫자/언더스코어/하이픈만 허용됩니다.")

    spec_dir = _PFY_SPEC_SOURCE / body.screen_name
    if not spec_dir.exists():
        raise HTTPException(404, f"spec-source 디렉토리를 찾을 수 없습니다: {spec_dir}")

    interview_note_path = spec_dir / "InterviewNote.md"
    component_vue_path = spec_dir / "Component.vue"
    metadata_path = spec_dir / "metadata.json"

    if not interview_note_path.exists():
        raise HTTPException(404, "InterviewNote.md가 없습니다. 인터뷰결과생성을 먼저 완료하세요.")

    interview_note_md = interview_note_path.read_text(encoding="utf-8")
    component_vue = component_vue_path.read_text(encoding="utf-8") if component_vue_path.exists() else ""

    # metadata.json을 brief 대용으로 사용
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        brief_md = (
            f"# {body.title}\n\n"
            f"- 페이지명: {body.page_name}\n"
            f"- 페이지 타입: {body.page_type or metadata.get('pageType', '')}\n\n"
            f"## Page Spec (from MockupBuilder)\n"
            f"```json\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n```\n"
        )
    else:
        brief_md = f"# {body.title}\n\n- 페이지명: {body.page_name}\n"

    session_store.increment_llm_calls(session_id)

    # 스트리밍 없이 한번에 생성 (프론트는 완료 응답 기다렸다가 SpecViewer로 전환)
    full_spec = ""
    async for chunk in mockup_pipeline.generate_spec_streaming(
        brief_md=brief_md,
        mockup_vue=component_vue,
        interview_notes_md=interview_note_md,
    ):
        full_spec += chunk

    # 세션에 저장 (텍스트 파이프라인과 동일 방식)
    session = session_store.get_or_create(session_id)
    session.spec_markdown = full_spec.strip()
    session.spec_version += 1
    session_store.save(session_id)

    return {"spec_markdown": session.spec_markdown, "spec_version": session.spec_version}
