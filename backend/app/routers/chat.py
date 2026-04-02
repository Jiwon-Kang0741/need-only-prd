import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.llm.pipeline import spec_pipeline
from app.models import ChatMessage, ChatRequest
from app.session import get_session_id, session_store

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat_feedback(
    body: ChatRequest,
    request: Request,
    session_id: str = Depends(get_session_id),
):
    session = session_store.get_or_create(session_id)
    if session.spec_markdown is None:
        raise HTTPException(status_code=400, detail="No spec generated yet. Generate a spec first.")

    user_message = ChatMessage(
        role="user",
        content=body.message,
        timestamp=datetime.now(timezone.utc),
    )
    session.chat_history.append(user_message)

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Applying feedback..."})}

            session_store.increment_llm_calls(session_id)
            full_spec = ""
            async for chunk in spec_pipeline.refine_spec(
                session.spec_markdown,
                session.chat_history,
                body.message,
            ):
                full_spec += chunk
                yield {"event": "message", "data": json.dumps({"type": "chunk", "content": chunk})}

            session.spec_markdown = full_spec
            session.spec_version += 1

            assistant_message = ChatMessage(
                role="assistant",
                content=f"Spec updated to v{session.spec_version}",
                timestamp=datetime.now(timezone.utc),
            )
            session.chat_history.append(assistant_message)

            yield {"event": "message", "data": json.dumps({"type": "complete", "spec_version": session.spec_version})}

        except HTTPException as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": e.detail})}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_generator())
