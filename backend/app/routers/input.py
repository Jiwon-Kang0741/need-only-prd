from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import settings
from app.models import InputRequest, RawInput
from app.session import get_session_id, session_store

router = APIRouter(prefix="/input", tags=["input"])


@router.post("")
async def submit_input(
    body: InputRequest,
    request: Request,
    session_id: str = Depends(get_session_id),
):
    content = body.text
    source_type = "text"

    if len(content) > settings.MAX_INPUT_CHARS:
        raise HTTPException(status_code=413, detail="Input exceeds maximum character limit")

    session = session_store.get_or_create(session_id)
    session.raw_input = RawInput(
        text=content,
        source_type=source_type,
        uploaded_at=datetime.now(timezone.utc),
    )
    session_store.save(session_id)

    return {"status": "ok", "chars": len(content)}
