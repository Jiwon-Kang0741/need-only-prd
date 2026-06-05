"""Phase-5 integration smoke: contract -> bindings -> frontend file set -> validation.

Scripted LLM (no real creds). Confirms the frontend generators produce a file at
every frontend bindings path and a clean <script setup> set passes validate_frontend.
"""

import pytest

from app.llm.graph import gen_frontend as gf
from app.llm.graph.contract_schema import parse_contract
from app.llm.graph.plan_and_bind import plan_and_bind
from app.llm.graph.frontend_validate import validate_frontend

pytestmark = pytest.mark.asyncio

_CLEAN_VUE = ('<script setup lang="ts">\nconst cols = []\n</script>\n'
              '<template><DataTable :columns="cols"/></template>\n')


class _Scripted:
    async def complete(self, system, user, max_tokens=16384):
        return _CLEAN_VUE


async def test_frontend_pipeline_produces_all_paths_and_validates(monkeypatch):
    monkeypatch.setattr(gf, "gpt55_client", _Scripted())
    contract = plan_and_bind({"contract": parse_contract({
        "identity": {"module": "edu", "category": "pondg", "screen_id": "cpmsEduPondgLst",
                     "class_name": "CpmsEduPondgLst", "program_id": "CPMSEDUPONDGLST"},
        "archetype": "list-detail",
        "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
        "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"], "columns": []},
        "frontend": {"components": ["SearchForm", "DataTable"]},
    }).model_dump()})["contract"]

    produced = {}
    produced.update(await gf.gen_types(contract, guide="G"))
    produced.update(await gf.gen_api(contract, guide="G", types="t"))
    for comp in contract["frontend"]["components"]:
        produced.update(await gf.gen_component(contract, guide="G", comp=comp, types="t"))
    produced.update(await gf.gen_index(contract, guide="G",
                                       components={"CpmsEduPondgLstSearchForm": "<template/>"},
                                       types="t"))

    paths = contract["bindings"]["paths"]
    # every frontend bindings path (vue_*) has a produced file
    for key, path in paths.items():
        if key.startswith("vue_"):
            assert path in produced, f"missing {key} -> {path}"

    # the generated .vue files (clean <script setup> + :columns) pass validation
    files = {p: {"file_path": p, "file_type": key, "layer": "frontend", "content": produced[p]}
             for key, p in paths.items()
             if key.startswith("vue_") and p.endswith(".vue")}
    assert validate_frontend(files, contract) == []
