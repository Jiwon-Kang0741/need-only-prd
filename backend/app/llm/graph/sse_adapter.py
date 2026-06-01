"""Bridge the LangGraph code-gen graph to the FastAPI SSE layer.

Converts graph state into the existing Pydantic CodeGenState shape (so legacy
/files, /download, /deploy keep working) and streams astream_events as the new
SSE event format.
"""

from __future__ import annotations

from app.llm.graph import guides
from app.llm.graph.build import build_graph, make_checkpointer
from app.llm.graph.config import REVIEWER_HARD_CAP
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


# Only these graph nodes surface as node_start/node_end events.
_PUBLIC_NODES = {"contract_extract", "planner", "generate_file", "reviewer"}

# Nodes whose returned `events` channel we drain to SSE. MUST exclude the
# top-level "LangGraph" wrapper: astream_events fires on_chain_end for the
# wrapper too, carrying the fully-accumulated `events` (add reducer), which
# would re-emit every domain event a second time.
_EMITTING_NODES = {"contract_extract", "planner", "generate_file",
                   "wave_gate", "reviewer"}


def drained_events(ev: dict) -> list[dict]:
    """Return domain events to forward for one astream_events item.

    Only drains on_chain_end from an actual emitting node — never the graph
    wrapper — so each domain event surfaces exactly once.
    """
    if ev.get("event") != "on_chain_end":
        return []
    if ev.get("name") not in _EMITTING_NODES:
        return []
    output = ev.get("data", {}).get("output")
    if isinstance(output, dict) and isinstance(output.get("events"), list):
        return output["events"]
    return []


def langgraph_event_to_sse(ev: dict) -> dict | None:
    """Map a single astream_events item to a new SSE dict, or None to skip."""
    kind = ev.get("event")
    name = ev.get("name", "")
    if kind == "on_chain_start" and name in _PUBLIC_NODES:
        return {"type": "node_start", "node": name}
    if kind == "on_chain_end" and name in _PUBLIC_NODES:
        return {"type": "node_end", "node": name}
    if kind == "on_tool_start":
        return {"type": "tool_call", "tool": name, "args": ev.get("data", {}).get("input", {})}
    if kind == "on_tool_end":
        return {"type": "tool_result", "tool": name}
    return None


async def stream_codegen(session, checkpointer=None):
    """Run the graph for a session, yielding new-format SSE event dicts.

    Yields domain events accumulated by nodes (state['events']) AND structural
    events from astream_events. Final 'graph_complete' includes the file count.
    """
    graph = build_graph(checkpointer=checkpointer)
    state_input = build_graph_input(session)
    config = {"configurable": {"thread_id": session.session_id},
              "recursion_limit": max(60, REVIEWER_HARD_CAP * 10)}

    async for ev in graph.astream_events(state_input, config, version="v2"):
        sse = langgraph_event_to_sse(ev)
        if sse is not None:
            yield sse
        # drain domain events — only from real emitting nodes (not graph wrapper)
        for dom in drained_events(ev):
            yield dom

    final = await graph.aget_state(config) if checkpointer else None
    files = final.values.get("files", {}) if final else {}
    yield {"type": "graph_complete", "total_files": len(files)}
