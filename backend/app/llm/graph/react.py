"""Reviewer ReAct loop: tool-calling until convergence or hard cap.

The reviewer inspects all generated files, calls read-only diagnostic tools
(cross_check, lookup_guide, ...) AND a mutating `apply_fix` tool to write
corrected content back into the file set. It converges when cross_check is clean
or the hard cap is reached.
"""

from __future__ import annotations

import json

from app.llm.graph.config import REVIEWER_HARD_CAP
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import REVIEWER_SYSTEM
from app.llm.graph.tools import REVIEWER_TOOL_SPECS, cross_check_impl, dispatch_tool


def _extract_function_calls(resp) -> list:
    return [item for item in getattr(resp, "output", [])
            if getattr(item, "type", "") == "function_call"]


def _parse_args(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


async def reviewer(state: dict) -> dict:
    """Run the reviewer ReAct loop over all generated files."""
    files = dict(state.get("files", {}))
    contract = state.get("contract", {})
    incoming_issues = list(state.get("open_issues", []))
    iterations = state.get("review_iterations", 0)
    events: list[dict] = []

    def _file_listing() -> str:
        return "\n".join(f"- {p} ({gf['file_type']})" for p, gf in files.items())

    user = (
        "Review all generated files for cross-file consistency and guide "
        "violations. Call cross_check first. When you find a problem, call "
        "apply_fix(file_path, content) with the COMPLETE corrected file content. "
        "Respond DONE when cross_check is clean.\n\nFiles:\n" + _file_listing()
    )

    while iterations < REVIEWER_HARD_CAP:
        iterations += 1
        resp = await gpt55_client.complete_with_tools(REVIEWER_SYSTEM, user, REVIEWER_TOOL_SPECS)
        calls = _extract_function_calls(resp)

        thought = (getattr(resp, "output_text", "") or "").strip()
        events.append({"type": "react_step", "iteration": iterations,
                       "thought": thought[:500]})

        if not calls:
            events.append({"type": "react_converged", "iterations": iterations})
            break

        observations: list[str] = []
        for call in calls:
            try:
                args = _parse_args(call.arguments)
            except (ValueError, TypeError) as exc:
                # malformed/truncated tool args → observation, not a crash
                events.append({"type": "tool_call", "tool": call.name, "args": {}})
                observations.append(f"{call.name} -> ERROR: bad arguments ({exc})")
                continue

            events.append({"type": "tool_call", "tool": call.name, "args": args})

            if call.name == "apply_fix":
                # mutating tool: write corrected content back into the file set
                fp = args.get("file_path", "")
                content = args.get("content", "")
                if fp in files and content:
                    files[fp] = {**files[fp], "content": content,
                                 "status_log": files[fp].get("status_log", [])
                                 + ["reviewer apply_fix"]}
                    events.append({"type": "file_fixed", "path": fp,
                                   "reason": thought[:200]})
                    result = {"applied": True, "file_path": fp}
                else:
                    result = {"applied": False,
                              "error": f"unknown file_path or empty content: {fp!r}"}
            else:
                try:
                    result = dispatch_tool(call.name, args, files, contract)
                except Exception as exc:  # tool error → observation (self-recovery)
                    result = {"error": str(exc)}

            events.append({"type": "tool_result", "tool": call.name})
            observations.append(
                f"{call.name} -> {json.dumps(result, ensure_ascii=False)[:1000]}")

        user = (user + "\n\n=== TOOL RESULTS ===\n" + "\n".join(observations)
                + "\n\nFix any offending files via apply_fix, or respond DONE if clean.")

    # recompute open issues via cross_check as the convergence signal
    cross_issues = cross_check_impl(files, contract)
    # Keep deterministic pre-review findings (mybatis_fix, signature checks, etc.)
    # and merge with reviewer convergence signal.
    seen = set()
    open_issues: list[dict] = []
    for issue in incoming_issues + cross_issues:
        key = (issue.get("file_path"), issue.get("issue"), issue.get("severity"))
        if key in seen:
            continue
        seen.add(key)
        open_issues.append(issue)
    return {"files": files, "review_iterations": iterations,
            "open_issues": open_issues, "events": events}
