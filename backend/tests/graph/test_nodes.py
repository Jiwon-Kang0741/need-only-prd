"""Node tests using the REAL gpt-5.5 LLM (marked llm; skipped without keys).

Assertions are structure-based, not exact-string, because LLM output varies.
"""

import pytest

from app.llm.graph import nodes

pytestmark = [pytest.mark.asyncio, pytest.mark.llm]

_SPEC = """\
# 교육 프로그램 목록 화면 (EDU001)
교육 프로그램을 조회/등록한다.
- 교육명(eduPgmNm): 텍스트, 검색 가능, 목록 표시
- 정원(capacity): 숫자, 목록 표시
"""

_VUE = """\
<template>
  <SearchForm><InputText v-model="eduPgmNm" label="교육명" /></SearchForm>
  <DataTable :value="rows">
    <Column field="eduPgmNm" header="교육명" />
    <Column field="capacity" header="정원" />
  </DataTable>
</template>
"""

_TABLE = """\
## TB_EDU_PGM (교육프로그램)
| 컬럼 | 타입 | PK |
|------|------|----|
| EDU_PGM_ID | VARCHAR(20) | Y |
| EDU_PGM_NM | VARCHAR(200) | N |
| CAPACITY | INT | N |
"""


async def test_contract_extract_produces_structured_contract():
    state = {"spec_markdown": _SPEC, "confirmed_vue": _VUE, "table_info": _TABLE}
    out = await nodes.contract_extract(state)
    contract = out["contract"]
    # structural assertions — keys present, not exact values
    assert "screen" in contract
    assert "fields" in contract
    assert isinstance(contract["fields"], list) and len(contract["fields"]) >= 1
    # the contract event is emitted
    assert any(e["type"] == "contract" for e in out["events"])


async def test_contract_maps_vue_field_to_db_column():
    state = {"spec_markdown": _SPEC, "confirmed_vue": _VUE, "table_info": _TABLE}
    out = await nodes.contract_extract(state)
    fields = out["contract"]["fields"]
    # somewhere the eduPgmNm field should reference the EDU_PGM_NM column
    joined = str(fields).upper()
    assert "EDU_PGM_NM" in joined or "EDUPGMNM" in joined


async def test_planner_lists_files_and_code_assigns_waves():
    contract = {
        "screen": {"id": "EDU001", "name": "교육 프로그램", "type": "list"},
        "tables": [{"name": "TB_EDU_PGM",
                    "columns": [{"col": "EDU_PGM_ID", "type": "VARCHAR", "pk": True},
                                {"col": "EDU_PGM_NM", "type": "VARCHAR", "pk": False}]}],
        "fields": [{"vue_field": "eduPgmNm", "db_column": "EDU_PGM_NM",
                    "type": "string", "label": "교육명"}],
        "search_conditions": [], "table_columns": [], "api_signatures": [],
    }
    out = await nodes.planner({"contract": contract})
    files = out["plan"]["files"]
    assert len(files) >= 1
    # every file got a wave (1..3) assigned by code, not the LLM
    assert all(f["wave"] in (1, 2, 3) for f in files)
    assert out["current_wave"] == 1
