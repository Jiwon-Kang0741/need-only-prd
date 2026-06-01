"""Reviewer ReAct loop: tool-calling until convergence or hard cap."""

from __future__ import annotations

import json

from app.llm.graph.config import REVIEWER_HARD_CAP
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import REVIEWER_SYSTEM
from app.llm.graph.tools import TOOL_SPECS, cross_check_impl, dispatch_tool


def _extract_function_calls(resp) -> list:
    return [item for item in getattr(resp, "output", [])
            if getattr(item, "type", "") == "function_call"]


async def reviewer(state: dict) -> dict:
    """Run the reviewer ReAct loop over all generated files."""
    files = dict(state.get("files", {}))
    contract = state.get("contract", {})
    iterations = state.get("review_iterations", 0)
    events: list[dict] = []

    user = (
        "Review all generated files for cross-file consistency and guide "
        "violations. Files:\n"
        + "\n".join(f"- {p} ({gf['file_type']})" for p, gf in files.items())
    )

    while iterations < REVIEWER_HARD_CAP:
        iterations += 1
        resp = await gpt55_client.complete_with_tools(REVIEWER_SYSTEM, user, TOOL_SPECS)
        calls = _extract_function_calls(resp)

        if not calls:
            # no tool calls -> model is done (text like "DONE")
            events.append({"type": "react_converged", "iterations": iterations})
            break

        # execute each tool call, feed results back into next turn's prompt
        observations: list[str] = []
        for call in calls:
            args = json.loads(call.arguments) if isinstance(call.arguments, str) else call.arguments
            events.append({"type": "tool_call", "tool": call.name, "args": args})
            try:
                result = dispatch_tool(call.name, args, files, contract)
            except Exception as exc:  # tool error becomes observation (self-recovery)
                result = {"error": str(exc)}
            events.append({"type": "tool_result", "tool": call.name})
            observations.append(f"{call.name} -> {json.dumps(result, ensure_ascii=False)[:1000]}")

        user = (user + "\n\n=== TOOL RESULTS ===\n" + "\n".join(observations)
                + "\n\nFix any offending files, or respond DONE if clean.")

    # recompute open issues via cross_check as the convergence signal
    open_issues = cross_check_impl(files, contract)
    return {"files": files, "review_iterations": iterations,
            "open_issues": open_issues, "events": events}
