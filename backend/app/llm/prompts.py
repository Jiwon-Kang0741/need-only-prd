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
    system = (
        "You are a senior software architect creating a technical specification that an AI coding agent "
        "can implement directly. The spec must be detailed enough that an AI can generate working code "
        "from it without further clarification. Use markdown format. Include these sections: "
        "1. Overview, 2. Architecture, 3. Data Models, 4. API Design, 5. Component Breakdown, "
        "6. Error Handling, 7. Implementation Steps."
    )
    user = (
        f"Requirements JSON:\n{requirements_json}\n\n"
        f"Original source text for context:\n{raw_text}\n\n"
        "Generate a complete technical specification based on the requirements above."
    )
    return system, user


def refinement_prompt(current_spec: str, chat_history: str, new_message: str) -> tuple[str, str]:
    system = (
        "You are revising a technical specification based on user feedback. Apply the requested changes "
        "while maintaining consistency with the rest of the document. Return the COMPLETE updated "
        "specification — not a diff or partial update."
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
