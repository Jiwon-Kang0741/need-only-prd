from fastapi import APIRouter, Depends, Request

from app.models import SessionRestoreRequest, SessionState
from app.session import get_session_id, session_store

router = APIRouter(prefix="/session", tags=["session"])


@router.get("", response_model=SessionState)
def get_session(session_id: str = Depends(get_session_id)):
    return session_store.get_or_create(session_id)


@router.post("/restore", response_model=SessionState)
def restore_session(body: SessionRestoreRequest, request: Request):
    session_id = get_session_id(request)
    session = SessionState(**body.session_state)
    session_store._cache[session_id] = session
    session_store.save(session_id)
    return session
