"""Assemble the code-generation StateGraph."""

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from app.llm.graph.state import CodeGenState


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
