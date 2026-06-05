"""Regression: domain events must be drained exactly once, not duplicated.

astream_events fires on_chain_end at BOTH the emitting node level AND the top
graph ('LangGraph') level — the latter carries the fully-accumulated `events`
channel (add reducer). Draining on both doubled every domain event.
"""

from app.llm.graph.sse_adapter import drained_events


def _end(name, events):
    return {"event": "on_chain_end", "name": name,
            "data": {"output": {"events": events}}}


def test_drains_emitting_node_events():
    out = drained_events(_end("plan_and_bind", [{"type": "plan"}]))
    assert out == [{"type": "plan"}]


def test_drains_gen_backend_events():
    out = drained_events(_end("gen_backend", [{"type": "log", "line": "[backend] generated 5 files"}]))
    assert out == [{"type": "log", "line": "[backend] generated 5 files"}]


def test_skips_graph_wrapper_to_avoid_duplication():
    # the top-level 'LangGraph' on_chain_end carries the accumulated channel
    out = drained_events(_end("LangGraph", [{"type": "plan"}, {"type": "contract"}]))
    assert out == []


def test_skips_non_chain_end():
    assert drained_events({"event": "on_chain_start", "name": "planner",
                           "data": {}}) == []


def test_skips_output_without_events():
    assert drained_events({"event": "on_chain_end", "name": "planner",
                           "data": {"output": {"files": {}}}}) == []
