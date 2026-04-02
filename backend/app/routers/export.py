from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.session import get_session_id, session_store

router = APIRouter(prefix="/export", tags=["export"])


@router.get("")
async def export_spec(
    request: Request,
    session_id: str = Depends(get_session_id),
):
    session = session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.spec_markdown is None:
        raise HTTPException(status_code=400, detail="No spec generated yet. Generate a spec first.")

    content = session.spec_markdown

    return StreamingResponse(
        iter([content]),
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=\"spec.md\""},
    )
