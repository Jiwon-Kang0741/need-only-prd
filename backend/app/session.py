import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, Request

from app.config import settings
from app.models import SessionState


def get_session_id(request: Request) -> str:
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")
    return session_id


DEFAULT_SESSION_DIR = Path(__file__).parent.parent / ".sessions"


class SessionStore:
    def __init__(self, session_dir: Path | None = None) -> None:
        self._cache: dict[str, SessionState] = {}
        self._dir = session_dir or DEFAULT_SESSION_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        # Load existing sessions from disk
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                state = SessionState(**data)
                self._cache[state.session_id] = state
            except Exception:
                pass  # Skip corrupted files

    def _save(self, session: SessionState) -> None:
        path = self._dir / f"{session.session_id}.json"
        path.write_text(session.model_dump_json(indent=2), encoding="utf-8")

    def get(self, session_id: str) -> SessionState | None:
        if session_id in self._cache:
            return self._cache[session_id]
        # Try loading from disk
        path = self._dir / f"{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                state = SessionState(**data)
                self._cache[session_id] = state
                return state
            except Exception:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "Failed to load session %s from disk — treating as not found", session_id
                )
                return None
        return None

    def create(self, session_id: str) -> SessionState:
        session = SessionState(
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
        )
        self._cache[session_id] = session
        self._save(session)
        return session

    def get_or_create(self, session_id: str) -> SessionState:
        existing = self.get(session_id)
        if existing is not None:
            return existing
        # Only create (and overwrite disk) if there is no file on disk at all.
        # If a file exists but failed to parse, keep it intact and return a
        # transient in-memory session to avoid destroying persisted data.
        path = self._dir / f"{session_id}.json"
        if path.exists():
            import logging as _logging
            _logging.getLogger(__name__).error(
                "Session %s disk file exists but could not be parsed — "
                "using transient in-memory session to preserve data",
                session_id,
            )
            session = SessionState(
                session_id=session_id,
                created_at=datetime.now(timezone.utc),
            )
            self._cache[session_id] = session
            return session
        return self.create(session_id)

    def save(self, session_id: str) -> None:
        """Persist current session state to disk."""
        session = self._cache.get(session_id)
        if session:
            self._save(session)

    def delete(self, session_id: str) -> None:
        self._cache.pop(session_id, None)
        path = self._dir / f"{session_id}.json"
        path.unlink(missing_ok=True)

    def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        ttl_seconds = settings.SESSION_TTL_HOURS * 3600
        expired = [
            sid
            for sid, state in self._cache.items()
            if (now - state.created_at).total_seconds() > ttl_seconds
        ]
        for sid in expired:
            self.delete(sid)

    def increment_llm_calls(self, session_id: str) -> None:
        session = self._cache.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        session.llm_call_count += 1
        if session.llm_call_count > settings.MAX_LLM_CALLS_PER_SESSION:
            raise HTTPException(status_code=429, detail="LLM call limit exceeded for this session")
        self._save(session)


session_store = SessionStore()
