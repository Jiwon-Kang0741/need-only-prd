from pathlib import Path

from app.config import settings

_REFERENCE_CONTEXT: str | None = None


def _load_reference_docs() -> str:
    global _REFERENCE_CONTEXT
    if _REFERENCE_CONTEXT is not None:
        return _REFERENCE_CONTEXT

    base = Path(settings.PROMPT_REFERENCE_DIR)
    files = ["CPMS_namebook.md", "namebook.md", "requirementParser.md"]
    parts = []
    for fname in files:
        path = base / fname
        if path.exists():
            parts.append(f"=== {fname} ===\n{path.read_text(encoding='utf-8')}")
    _REFERENCE_CONTEXT = "\n\n".join(parts) if parts else ""
    return _REFERENCE_CONTEXT


def extraction_prompt(raw_text: str) -> tuple[str, str]:
    system = (
        "You are a senior requirements analyst. Extract structured requirements from unstructured text "
        "such as meeting notes, emails, or chat logs. Be thorough — do not miss any requirement, "
        "constraint, or assumption mentioned in the text. Output valid JSON only."
    )
    user = (
        f"{raw_text}\n\n"
        "Extract all requirements from the text above and output JSON with this exact schema:\n"
        "{\n"
        '  "functional_requirements": [{"id": "FR-001", "description": "...", "priority": "high|medium|low"}],\n'
        '  "non_functional_requirements": [{"id": "NFR-001", "description": "...", "category": "..."}],\n'
        '  "constraints": ["..."],\n'
        '  "assumptions": ["..."],\n'
        '  "ambiguities": ["items that need clarification"]\n'
        "}"
    )
    return system, user


def generation_prompt(requirements_json: str, raw_text: str) -> tuple[str, str]:
    ref_docs = _load_reference_docs()
    system = (
        "You are a senior software architect creating a technical specification (spec.md) "
        "that an AI coding agent can implement directly. "
        "You MUST strictly follow the naming conventions, spec template structure, and domain terminology "
        "defined in the reference documents below. "
        "The output MUST be a complete spec.md in markdown format following the template structure "
        "(Global Rules, Requirement Refinement, Atomic User Stories, Domain Modeling, "
        "Business Logic Rules, API Specification, UI/UX Flow, AI_HINT). "
        "Use the naming conventions from the namebook documents for all class names, method names, "
        "DTO names, and table names. "
        "If information is missing, mark it as [NEEDS CLARIFICATION: description]. "
        "Do NOT invent business logic that is not derived from the requirements.\n\n"
        f"--- REFERENCE DOCUMENTS ---\n{ref_docs}\n--- END REFERENCE DOCUMENTS ---"
    )
    user = (
        f"Requirements JSON:\n{requirements_json}\n\n"
        f"Original source text for context:\n{raw_text}\n\n"
        "Generate a complete technical specification (spec.md) based on the requirements above, "
        "strictly following the template and naming conventions from the reference documents."
    )
    return system, user


def refinement_prompt(current_spec: str, chat_history: str, new_message: str) -> tuple[str, str]:
    ref_docs = _load_reference_docs()
    system = (
        "You are revising a technical specification based on user feedback. "
        "Apply the requested changes while maintaining consistency with the rest of the document. "
        "You MUST continue to follow the naming conventions and spec template structure "
        "defined in the reference documents below. "
        "Return the COMPLETE updated specification — not a diff or partial update.\n\n"
        f"--- REFERENCE DOCUMENTS ---\n{ref_docs}\n--- END REFERENCE DOCUMENTS ---"
    )
    user = (
        f"Current specification:\n{current_spec}\n\n"
        f"Chat history:\n{chat_history}\n\n"
        f"New user message:\n{new_message}\n\n"
        "Return the complete updated specification incorporating the requested changes."
    )
    return system, user


def summarization_prompt(chat_history: str) -> tuple[str, str]:
    system = (
        "You are a concise technical summarizer. Summarize the conversation history below into a brief "
        "paragraph capturing the key decisions, changes requested, and context. Keep only information "
        "relevant to the technical specification being refined. Output plain text only."
    )
    user = (
        f"Conversation history:\n{chat_history}\n\n"
        "Summarize the key points from this conversation in 2-4 sentences."
    )
    return system, user


def validation_prompt(raw_text: str, spec_markdown: str, requirements_json: str) -> tuple[str, str]:
    system = (
        "You are a QA analyst comparing an original requirements source against a technical specification. "
        "For each requirement, determine if it is adequately covered in the spec. Be strict — partial "
        "coverage should be flagged. Output valid JSON only."
    )
    user = (
        f"Original requirements source:\n{raw_text}\n\n"
        f"Technical specification:\n{spec_markdown}\n\n"
        f"Extracted requirements:\n{requirements_json}\n\n"
        "Compare the requirements against the specification and output JSON with this exact schema:\n"
        "{\n"
        '  "score": 85,\n'
        '  "covered": [{"id": "FR-001", "evidence": "Section X addresses..."}],\n'
        '  "missing": [{"id": "FR-005", "reason": "No mention of..."}],\n'
        '  "suggestions": ["Consider adding..."]\n'
        "}"
    )
    return system, user
