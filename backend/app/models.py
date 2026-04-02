from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RawInput(BaseModel):
    text: str
    source_type: str = "text"
    uploaded_at: datetime


class ExtractedRequirements(BaseModel):
    functional_requirements: list[dict] = Field(default_factory=list)
    non_functional_requirements: list[dict] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime


class ValidationResult(BaseModel):
    score: float
    covered: list[dict]
    missing: list[dict]
    suggestions: list[str]


class SessionState(BaseModel):
    session_id: str
    created_at: datetime
    raw_input: RawInput | None = None
    extracted_requirements: ExtractedRequirements | None = None
    spec_markdown: str | None = None
    spec_version: int = 0
    chat_history: list[ChatMessage] = Field(default_factory=list)
    validation_result: ValidationResult | None = None
    llm_call_count: int = 0


class InputRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    message: str


class SessionRestoreRequest(BaseModel):
    session_state: dict
