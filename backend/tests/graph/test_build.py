"""Graph assembly tests. Compile test is offline; e2e uses the real gpt-5.5 LLM."""

import re

import pytest

from app.llm.graph import build
from app.llm.graph.naming import BASE_DAO_METHODS
from app.llm.graph.tools import static_check_impl

pytestmark = pytest.mark.asyncio


async def test_build_graph_compiles():
    """Graph compiles without a checkpointer (offline, no LLM)."""
    graph = build.build_graph(checkpointer=None)
    assert graph is not None


def test_build_graph_has_contract_first_nodes():
    g = build.build_graph(checkpointer=None)
    names = set(g.get_graph().nodes)
    assert {"contract_resolve", "plan_and_bind", "gen_backend",
            "gen_frontend", "gen_data", "validate"} <= names
    assert "generate_file" not in names and "derive_contract" not in names


@pytest.mark.llm
async def test_end_to_end_real_llm(guide_stub):
    """Full pipeline: spec+vue+table -> contract_resolve -> plan_and_bind -> gen_* -> validate."""
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
    assert len(final["files"]) >= 1
    layers = {gf["layer"] for gf in final["files"].values()}
    assert "backend" in layers
    for gf in final["files"].values():
        assert "content" in gf and gf.get("file_type")
