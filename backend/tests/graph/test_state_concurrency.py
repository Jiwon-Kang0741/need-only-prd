"""Regression: open_issues must tolerate concurrent writes from parallel Send fan-out."""

import asyncio

import pytest
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from app.llm.graph.state import CodeGenState

pytestmark = pytest.mark.asyncio


async def test_open_issues_survives_parallel_writes():
    """Two parallel generate-like nodes both writing open_issues must not crash."""

    async def gen(state):
        return {"open_issues": [{"issue": f"bad {state['_fp']}"}]}

    def route(_state):
        return [Send("gen", {**_state, "_fp": f}) for f in ("a.java", "b.java")]

    g = StateGraph(CodeGenState)
    g.add_node("gen", gen)
    g.add_node("seed", lambda s: {"current_wave": 1})
    g.add_edge(START, "seed")
    g.add_conditional_edges("seed", route, ["gen"])
    g.add_edge("gen", END)
    graph = g.compile()

    out = await graph.ainvoke({"files": {}, "open_issues": [], "events": []})
    issues = {i["issue"] for i in out["open_issues"]}
    assert issues == {"bad a.java", "bad b.java"}
