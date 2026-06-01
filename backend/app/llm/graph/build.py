"""Assemble the code-generation StateGraph."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.llm.graph.state import CodeGenState
from app.llm.graph.waves import MAX_WAVE, files_in_wave
from app.llm.graph import nodes, react
from app.llm.graph.mybatis_check import autofix_binding, check_binding


def _route_waves(state: dict):
    """Send the current wave's files to generate_file, or go to reviewer.

    Used as the conditional edge after both `planner` (current_wave=1) and
    `wave_gate` (current_wave already bumped). When all waves are exhausted,
    route to the reviewer.
    """
    wave = state.get("current_wave", 1)
    if wave > MAX_WAVE:
        return "mybatis_fix"
    specs = files_in_wave(state["plan"], wave)
    if not specs:
        # empty wave -> bump again via wave_gate (no-op generation)
        return [Send("wave_gate", state)]
    return [Send("generate_file", {**state, "_file_spec": spec}) for spec in specs]


def _wave_gate(state: dict) -> dict:
    """Barrier: increment wave after a wave's files fan in.

    Emits wave_complete for the wave that just finished and wave_start for the
    next wave (if it has files), so the UI can show parallel-wave progress.
    """
    finished = state.get("current_wave", 1)
    nxt = finished + 1
    plan = state.get("plan", {})
    events: list[dict] = []
    # Only emit wave_complete for a wave that actually had files (i.e. a
    # wave_start was emitted for it). Empty intermediate waves are silent.
    if files_in_wave(plan, finished):
        events.append({"type": "wave_complete", "wave": finished})
    if nxt <= MAX_WAVE:
        n = len(files_in_wave(plan, nxt))
        if n:
            events.append({"type": "wave_start", "wave": nxt, "file_count": n})
    return {"current_wave": nxt, "events": events}


def mybatis_fix(state: dict) -> dict:
    """Deterministic DAO↔Mapper binding autofix before the reviewer (no LLM)."""
    files = dict(state.get("files", {}))
    try:
        fixed_files, fix_logs = autofix_binding(files)
        remaining = check_binding(fixed_files)
    except Exception as e:  # verification is a safety net, never a blocker
        return {"events": [{"type": "log", "line": f"[MYBATIS] error: {e}"}]}
    events = [{"type": "log", "line": f"[MYBATIS-FIX] {log}"} for log in fix_logs]
    errors = [i for i in remaining if i.get("severity") != "warning"]
    if errors:
        events.append({"type": "log",
                       "line": f"[MYBATIS] {len(errors)} binding issue(s) left for reviewer"})
    return {"files": fixed_files, "events": events, "open_issues": remaining}


def build_graph(checkpointer=None):
    g = StateGraph(CodeGenState)
    g.add_node("contract_extract", nodes.contract_extract)
    g.add_node("planner", nodes.planner)
    g.add_node("generate_file", nodes.generate_file)
    g.add_node("derive_contract", nodes.derive_contract)
    g.add_node("wave_gate", _wave_gate)
    g.add_node("mybatis_fix", mybatis_fix)
    g.add_node("reviewer", react.reviewer)

    g.add_edge(START, "contract_extract")
    g.add_edge("contract_extract", "planner")
    g.add_edge("planner", "derive_contract")
    g.add_conditional_edges("derive_contract", _route_waves,
                            ["generate_file", "wave_gate", "mybatis_fix"])
    g.add_edge("generate_file", "wave_gate")
    g.add_conditional_edges("wave_gate", _route_waves,
                            ["generate_file", "wave_gate", "mybatis_fix"])
    g.add_edge("mybatis_fix", "reviewer")
    g.add_edge("reviewer", END)

    return g.compile(checkpointer=checkpointer)


def make_checkpointer(db_path: str = ".sessions/codegen_graph.db"):
    """Async context manager yielding an AsyncSqliteSaver (thread_id=session_id)."""
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    return AsyncSqliteSaver.from_conn_string(db_path)
