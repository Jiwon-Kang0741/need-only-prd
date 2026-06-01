"""Graph assembly tests. Compile test is offline; e2e uses the real gpt-5.5 LLM."""

import pytest

from app.llm.graph import build

pytestmark = pytest.mark.asyncio


async def test_build_graph_compiles():
    """Graph compiles without a checkpointer (offline, no LLM)."""
    graph = build.build_graph(checkpointer=None)
    assert graph is not None


@pytest.mark.llm
async def test_end_to_end_real_llm(guide_stub):
    """Full pipeline: spec+vue+table -> contract -> plan -> waves -> reviewer."""
    spec = ("# 교육 프로그램 목록 (EDU001)\n교육명(eduPgmNm) 텍스트 검색/목록.\n")
    vue = ('<template><DataTable><Column field="eduPgmNm" header="교육명"/>'
           '</DataTable></template>')
    table = ("## TB_EDU_PGM\n| 컬럼 | 타입 | PK |\n|--|--|--|\n"
             "| EDU_PGM_ID | VARCHAR | Y |\n| EDU_PGM_NM | VARCHAR | N |\n")

    graph = build.build_graph(checkpointer=None)
    state = {"session_id": "s1", "spec_markdown": spec, "confirmed_vue": vue,
             "table_info": table, "files": {}}
    final = await graph.ainvoke(state, {"configurable": {"thread_id": "s1"},
                                        "recursion_limit": 60})
    # at least one file generated, reviewer ran
    assert len(final["files"]) >= 1
    assert final.get("review_iterations", 0) >= 1
    # every generated file carries a valid wave + ok status
    for gf in final["files"].values():
        assert gf["wave"] in (1, 2, 3)
        assert gf["status"] == "ok"
