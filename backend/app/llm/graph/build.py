"""Assemble the code-generation StateGraph."""

from __future__ import annotations

import logging
import traceback

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.llm.graph.state import CodeGenState
from app.llm.graph.waves import MAX_WAVE, files_in_wave
from app.llm.graph import nodes, react
from app.llm.graph.mybatis_check import (
    autofix_binding, check_binding, autofix_dto_fields, check_dto_fields,
    autofix_dedupe_dto_fields, autofix_dto_array_fields, check_service_dao_signatures,
)
from app.llm.graph.cpms_checks import (
    check_db_seed_sql, check_frontend_local_imports, check_lv2_whitelist,
    autofix_log_before_throw,
)
from app.llm.graph.tools import check_forbidden_imports

logger = logging.getLogger(__name__)


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
    """Deterministic DAO↔Mapper + DTO-field autofix before the reviewer (no LLM).

    Uses contract.operations/dtos as the source of truth when present; otherwise
    falls back to Phase 1 behavior (DAO super calls).
    """
    files = dict(state.get("files", {}))
    contract = state.get("contract")
    try:
        fixed_files, fix_logs = autofix_binding(files, contract)
        if contract:
            fixed_files, dto_logs = autofix_dto_fields(fixed_files, contract)
            fix_logs = fix_logs + dto_logs
        # Deterministic DTO source fixes (compile-error preventers, no LLM):
        # dedupe duplicate field decls + downgrade banned Java-array fields.
        fixed_files, dedup_logs = autofix_dedupe_dto_fields(fixed_files)
        fixed_files, arr_logs = autofix_dto_array_fields(fixed_files)
        fix_logs = fix_logs + dedup_logs + arr_logs
        # Deterministic CPMS source fix: drop redundant log-before-throw lines.
        fixed_files, log_logs = autofix_log_before_throw(fixed_files)
        fix_logs = fix_logs + log_logs
        remaining = check_binding(fixed_files, contract)
        if contract:
            remaining = remaining + check_dto_fields(fixed_files, contract)
        remaining = remaining + check_service_dao_signatures(fixed_files)
        # Ported CPMS domain checks (whole-file): DB seed + frontend imports + LV2.
        remaining = (remaining + check_db_seed_sql(fixed_files)
                     + check_frontend_local_imports(fixed_files)
                     + check_forbidden_imports(fixed_files))
        screen_code = ((contract or {}).get("screen") or {}).get("id", "")
        remaining = remaining + check_lv2_whitelist(screen_code)
    except Exception as e:  # non-blocking, but must NOT vanish into a single log line
        tb = traceback.format_exc(limit=4)
        logger.exception("mybatis_fix verification crashed: %s", e)
        # Surface as a visible event AND an open_issue so the reviewer knows the
        # deterministic pass did not run for these files (instead of silent skip).
        return {
            "events": [{"type": "log",
                        "line": f"[MYBATIS] verification ERROR ({type(e).__name__}): {e} — "
                                "deterministic autofix/checks skipped; reviewer must verify"}],
            "open_issues": [{
                "file_path": "*",
                "issue": (f"Deterministic mybatis_fix crashed ({type(e).__name__}: {e}); "
                          "DAO↔Mapper binding / DTO fields were NOT auto-verified. "
                          f"Review carefully.\n{tb}"),
                "severity": "warning",
            }],
        }
    events = [{"type": "log", "line": f"[MYBATIS-FIX] {log}"} for log in fix_logs]
    errors = [i for i in remaining if i.get("severity") != "warning"]
    if errors:
        events.append({"type": "log",
                       "line": f"[MYBATIS] {len(errors)} binding issue(s) left for reviewer"})
    return {"files": fixed_files, "events": events, "open_issues": remaining}


def build_graph(checkpointer=None):
    from app.llm.graph import contract_resolve, plan_and_bind, gen_nodes
    g = StateGraph(CodeGenState)
    g.add_node("contract_resolve", contract_resolve.contract_resolve)
    g.add_node("plan_and_bind", plan_and_bind.plan_and_bind)
    g.add_node("gen_backend", gen_nodes.gen_backend_node)
    g.add_node("gen_frontend", gen_nodes.gen_frontend_node)
    g.add_node("gen_data", gen_nodes.gen_data_node)
    g.add_node("validate", gen_nodes.validate_node)
    g.add_edge(START, "contract_resolve")
    g.add_edge("contract_resolve", "plan_and_bind")
    g.add_edge("plan_and_bind", "gen_backend")
    g.add_edge("gen_backend", "gen_frontend")
    g.add_edge("gen_frontend", "gen_data")
    g.add_edge("gen_data", "validate")
    g.add_edge("validate", END)
    return g.compile(checkpointer=checkpointer)


def make_checkpointer(db_path: str = ".sessions/codegen_graph.db"):
    """Async context manager yielding an AsyncSqliteSaver (thread_id=session_id)."""
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    return AsyncSqliteSaver.from_conn_string(db_path)
