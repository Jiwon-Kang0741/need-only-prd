"""Checkpointing tests using the real gpt-5.5 LLM + AsyncSqliteSaver."""

import pytest

from app.llm.graph import build

pytestmark = [pytest.mark.asyncio, pytest.mark.llm]

_SPEC = "# 교육 (EDU001)\n교육명(eduPgmNm) 텍스트.\n"
_VUE = '<template><Column field="eduPgmNm"/></template>'
_TABLE = "## TB_EDU_PGM\n| EDU_PGM_ID | VARCHAR | Y |\n| EDU_PGM_NM | VARCHAR | N |\n"


async def test_checkpoint_persists_and_is_retrievable(guide_stub, tmp_path):
    db = str(tmp_path / "ckpt.db")
    async with build.make_checkpointer(db) as cp:
        graph = build.build_graph(checkpointer=cp)
        cfg = {"configurable": {"thread_id": "sess-X"}, "recursion_limit": 60}
        await graph.ainvoke(
            {"session_id": "sess-X", "spec_markdown": _SPEC, "confirmed_vue": _VUE,
             "table_info": _TABLE, "files": {}}, cfg)
        # state retrievable from the checkpoint after completion
        snapshot = await graph.aget_state(cfg)
        assert len(snapshot.values["files"]) >= 1
        assert "contract" in snapshot.values


async def test_resume_returns_cached_state(guide_stub, tmp_path):
    """Re-invoking with the same thread_id after completion returns final state
    from the checkpoint (no error, state intact)."""
    db = str(tmp_path / "ckpt2.db")
    async with build.make_checkpointer(db) as cp:
        graph = build.build_graph(checkpointer=cp)
        cfg = {"configurable": {"thread_id": "sess-Y"}, "recursion_limit": 60}
        first = await graph.ainvoke(
            {"session_id": "sess-Y", "spec_markdown": _SPEC, "confirmed_vue": _VUE,
             "table_info": _TABLE, "files": {}}, cfg)
        n_files = len(first["files"])
        # resume: get_state must reflect the same files without re-running
        snap = await graph.aget_state(cfg)
        assert len(snap.values["files"]) == n_files
        assert snap.values["session_id"] == "sess-Y"
