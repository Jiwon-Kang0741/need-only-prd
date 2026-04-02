from datetime import datetime, timezone

from fastapi import HTTPException, Request

from app.config import settings
from app.models import SessionState


def get_session_id(request: Request) -> str:
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")
    return session_id


class SessionStore:
    def __init__(self) -> None:
        self._store: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState | None:
        return self._store.get(session_id)

    def create(self, session_id: str) -> SessionState:
        session = SessionState(
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
        )
        self._store[session_id] = session
        return session

    def get_or_create(self, session_id: str) -> SessionState:
        return self._store.get(session_id) or self.create(session_id)

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        ttl_seconds = settings.SESSION_TTL_HOURS * 3600
        expired = [
            sid
            for sid, state in self._store.items()
            if (now - state.created_at).total_seconds() > ttl_seconds
        ]
        for sid in expired:
            del self._store[sid]

    def increment_llm_calls(self, session_id: str) -> None:
        session = self._store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        session.llm_call_count += 1
        if session.llm_call_count > settings.MAX_LLM_CALLS_PER_SESSION:
            raise HTTPException(status_code=429, detail="LLM call limit exceeded for this session")


session_store = SessionStore()
