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
    codegen: CodeGenState | None = None
    spec_source: Literal["text", "mockup"] | None = None
    mockup_state: MockupState | None = None


class InputRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    message: str


class SessionRestoreRequest(BaseModel):
    session_state: dict


# --- Code Generation Models ---


class GeneratedFile(BaseModel):
    file_path: str
    file_type: str
    content: str
    layer: str  # "backend" | "frontend"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class CodeGenPlanFile(BaseModel):
    file_path: str
    file_type: str
    layer: str
    description: str
    depends_on: list[str] = Field(default_factory=list)


class CodeGenPlan(BaseModel):
    files: list[CodeGenPlanFile] = Field(default_factory=list)
    module_code: str = ""
    screen_code: str = ""


class DockerConfig(BaseModel):
    docker_compose_yaml: str = ""
    backend_dockerfile: str = ""
    frontend_dockerfile: str = ""
    db_init_sql: str | None = None


class AgentMeta(BaseModel):
    role: str  # planner|backend_engineer|frontend_engineer|data_engineer|qa_engineer
    display_name: str
    description: str


class AgentStatus(BaseModel):
    role: str
    display_name: str
    status: str = "idle"  # idle|running|completed|error
    files_count: int = 0


class CodeGenState(BaseModel):
    status: str = "idle"  # idle|planning|generating|building|running|error
    plan: CodeGenPlan | None = None
    generated_files: list[GeneratedFile] = Field(default_factory=list)
    docker_config: DockerConfig | None = None
    current_file_index: int = 0
    build_logs: list[str] = Field(default_factory=list)
    error: str | None = None
    agents: list[AgentStatus] = Field(default_factory=list)


# --- Mockup Pipeline Models ---


class FieldOption(BaseModel):
    label: str
    value: str
    color: str | None = None


class FieldDef(BaseModel):
    key: str
    label: str
    type: Literal["text", "number", "select", "radio", "badge", "date", "daterange", "textarea", "checkbox"]
    searchable: bool = False
    listable: bool = False
    detailable: bool = False
    editable: bool = False
    required: bool = False
    options: list[FieldOption] | None = None
    width: str | None = None


class TabDef(BaseModel):
    key: str
    label: str
    fields: list[FieldDef]


class MockupState(BaseModel):
    screen_id: str
    screen_name: str
    page_type: Literal["list-detail", "list", "edit", "tab-detail"]
    fields: list[dict] = Field(default_factory=list)
    tabs: list[TabDef] | None = None
    vue_code: str | None = None
    annotations: list[dict] | None = None
    annotation_markdown: str | None = None
    interview_questions: list[dict] | None = None
    interview_answers: list[dict] | None = None
    raw_interview_text: str | None = None
    interview_note_md: str | None = None
    current_step: int = 1
