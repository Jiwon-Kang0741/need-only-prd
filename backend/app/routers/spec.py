import json
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.llm.pipeline import spec_pipeline
from app.models import ExtractedRequirements
from app.session import get_session_id, session_store

router = APIRouter(prefix="/spec", tags=["spec"])

_PROMPT_DIR = Path(settings.PROMPT_REFERENCE_DIR)
# Last-imported / last-generated spec (session convenience). May be absent on fresh clone.
_SPEC_CACHE_PRIMARY = _PROMPT_DIR / "spec.md"
# Repository-shipped filled example when primary is missing.
_SPEC_CACHE_FALLBACK = _PROMPT_DIR / "spec.example.md"


def _read_spec_cache_file() -> Path:
    """Return path to readable spec cache (primary or example fallback)."""
    if _SPEC_CACHE_PRIMARY.exists():
        return _SPEC_CACHE_PRIMARY
    if _SPEC_CACHE_FALLBACK.exists():
        return _SPEC_CACHE_FALLBACK
    raise FileNotFoundError(
        f"Neither {_SPEC_CACHE_PRIMARY} nor {_SPEC_CACHE_FALLBACK} exists."
    )


class ImportSpecRequest(BaseModel):
    spec_markdown: str


@router.post("/import")
async def import_spec(
    body: ImportSpecRequest,
    session_id: str = Depends(get_session_id),
):
    """붙여넣은 spec.md를 세션에 저장하고 pfy_prompt/spec.md 캐시에도 보존한다."""
    if not body.spec_markdown.strip():
        raise HTTPException(status_code=400, detail="spec_markdown is empty")

    content = body.spec_markdown.strip()
    session = session_store.get_or_create(session_id)
    session.spec_markdown = content
    session.spec_version += 1
    session_store.save(session_id)

    _SPEC_CACHE_PRIMARY.parent.mkdir(parents=True, exist_ok=True)
    _SPEC_CACHE_PRIMARY.write_text(content, encoding="utf-8")

    return {"spec_version": session.spec_version, "length": len(content)}


@router.post("/load-file")
async def load_spec_file(
    session_id: str = Depends(get_session_id),
):
    """pfy_prompt/spec.md(또는 없으면 spec.example.md)를 읽어 세션에 올린다."""
    try:
        path = _read_spec_cache_file()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No spec cache found. Import a spec or ensure {_SPEC_CACHE_FALLBACK.name} exists. ({e})"
            ),
        ) from e

    content = path.read_text(encoding="utf-8")
    session = session_store.get_or_create(session_id)
    session.spec_markdown = content
    session.spec_version += 1
    session_store.save(session_id)

    return {"spec_markdown": content, "spec_version": session.spec_version}


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
            session_store.save(session_id)

            _SPEC_CACHE_PRIMARY.parent.mkdir(parents=True, exist_ok=True)
            _SPEC_CACHE_PRIMARY.write_text(full_spec, encoding="utf-8")

            yield {"event": "message", "data": json.dumps({"type": "complete", "spec_version": session.spec_version})}

        except HTTPException as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": e.detail})}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_generator(), ping=10)


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
