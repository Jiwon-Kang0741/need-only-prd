from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import InputRequest, RawInput
from app.session import get_session_id, session_store
from app.utils.text import extract_text_from_file

router = APIRouter(prefix="/input", tags=["input"])


@router.post("")
async def submit_input(
    request: Request,
    text: str | None = None,
    file: UploadFile | None = File(default=None),
    session_id: str = Depends(get_session_id),
):
    if file is not None:
        content = await extract_text_from_file(file)
        source_type = "file"
    elif text is not None:
        content = text
        source_type = "text"
    else:
        raise HTTPException(status_code=422, detail="Either text or file is required")

    if len(content) > settings.MAX_INPUT_CHARS:
        raise HTTPException(status_code=413, detail="Input exceeds maximum character limit")

    session = session_store.get_or_create(session_id)
    session.raw_input = RawInput(
        text=content,
        source_type=source_type,
        uploaded_at=datetime.now(timezone.utc),
    )

    return {"status": "ok", "chars": len(content)}
