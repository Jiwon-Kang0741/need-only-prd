"""LLM Proxy router — scaffolding Express server가 우리 Azure OpenAI(gpt-5.4)를
사내 게이트웨이 없이 사용할 수 있도록 프록시한다. OpenAI chat completions 포맷.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm.client import llm_client

router = APIRouter(prefix="/llm", tags=["llm"])


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[Message]
    temperature: float = 0.35
    max_tokens: int = 3000
    stream: bool = False


@router.post("/chat-completion")
async def chat_completion(body: ChatCompletionRequest):
    """OpenAI chat completions 호환 프록시. system/user 메시지를 우리 llm_client로 전달."""
    if body.stream:
        raise HTTPException(400, "Streaming 미지원. stream=false로 호출하세요.")
    if not body.messages:
        raise HTTPException(400, "messages가 비어있습니다.")

    # 가장 최근의 system/user만 사용 (scaffolding의 호출 패턴과 일치)
    system_parts = [m.content for m in body.messages if m.role == "system"]
    user_parts = [m.content for m in body.messages if m.role == "user"]
    system = "\n\n".join(system_parts) if system_parts else ""
    user = "\n\n".join(user_parts) if user_parts else ""

    if not user:
        raise HTTPException(400, "user 메시지가 필요합니다.")

    response = await llm_client.complete(system, user, stream=False, max_tokens=body.max_tokens)

    # OpenAI chat completions 응답 형식으로 포장
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": str(response)},
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "model": body.model or "proxy",
        "object": "chat.completion",
    }
