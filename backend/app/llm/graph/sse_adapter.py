"""Bridge the LangGraph code-gen graph to the FastAPI SSE layer.

Converts graph state into the existing Pydantic CodeGenState shape (so legacy
/files, /download, /deploy keep working) and streams astream_events as the new
SSE event format.
"""

from __future__ import annotations

from app.llm.graph import guides
from app.models import GeneratedFile


def graph_files_to_pydantic(files: dict) -> list[GeneratedFile]:
    """Convert graph files dict[path, TypedDict] -> list[GeneratedFile pydantic]."""
    out: list[GeneratedFile] = []
    for gf in files.values():
        out.append(GeneratedFile(
            file_path=gf["file_path"],
            file_type=gf["file_type"],
            content=gf["content"],
            layer=gf["layer"],
        ))
    return out


def build_graph_input(session) -> dict:
    """Assemble the initial CodeGenState input from a session.

    confirmed Vue comes from the mockup scaffold; table_info from the guides
    loader (fresh). Spec is the session spec markdown.
    """
    mockup = getattr(session, "mockup_state", None)
    confirmed_vue = (mockup.vue_code or "") if mockup and getattr(mockup, "vue_code", None) else ""
    return {
        "session_id": session.session_id,
        "spec_markdown": session.spec_markdown or "",
        "confirmed_vue": confirmed_vue,
        "table_info": guides.load_table_info(),
        "files": {},
    }
