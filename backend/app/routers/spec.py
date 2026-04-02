import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.llm.pipeline import spec_pipeline
from app.models import ExtractedRequirements
from app.session import get_session_id, session_store

router = APIRouter(prefix="/spec", tags=["spec"])


@router.post("/generate")
async def generate_spec(
    request: Request,
    session_id: str = Depends(get_session_id),
):
    session = session_store.get_or_create(session_id)
    if session.raw_input is None:
        raise HTTPException(status_code=400, detail="No input found. Submit input first.")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Analyzing requirements..."})}

            session_store.increment_llm_calls(session_id)
            requirements = await spec_pipeline.extract_requirements(session.raw_input.text)
            session.extracted_requirements = ExtractedRequirements(**requirements)

            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Generating technical specification..."})}
            yield {"event": "message", "data": json.dumps({"type": "requirements", "content": json.dumps(requirements)})}

            session_store.increment_llm_calls(session_id)
            full_spec = ""
            async for chunk in spec_pipeline.generate_spec(requirements, session.raw_input.text):
                full_spec += chunk
                yield {"event": "message", "data": json.dumps({"type": "chunk", "content": chunk})}

            session.spec_markdown = full_spec
            session.spec_version += 1

            yield {"event": "message", "data": json.dumps({"type": "complete", "spec_version": session.spec_version})}

        except HTTPException as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": e.detail})}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_generator())


@router.get("")
async def get_spec(
    request: Request,
    session_id: str = Depends(get_session_id),
):
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "spec_markdown": session.spec_markdown,
        "spec_version": session.spec_version,
        "extracted_requirements": session.extracted_requirements.model_dump() if session.extracted_requirements else None,
    }
