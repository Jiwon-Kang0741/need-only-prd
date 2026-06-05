"""Contract Resolver node — produces the single shared Contract from spec + mockup.

The keystone of the rewrite: one LLM call (gpt-5.5) resolves screen identity
(incl. module/category — decision O1), archetype, ops, target table+columns+PK,
field map, frontend component plan, api/seed metadata. Output is validated against
the pydantic Contract (parse_contract) with one retry, so downstream nodes consume
a guaranteed-shaped artifact. bindings are filled later by plan_and_bind.
"""

from __future__ import annotations

import json
from typing import get_args

from pydantic import ValidationError

from app.llm.graph.llm import gpt55_client
from app.llm.graph.contract_schema import Contract, parse_contract
from app.llm.graph._text import strip_fences as _strip_fences

# Valid archetype values, derived from the schema Literal (no duplicated list).
_VALID_ARCHETYPES = frozenset(get_args(Contract.model_fields["archetype"].annotation))
assert _VALID_ARCHETYPES and all(isinstance(v, str) for v in _VALID_ARCHETYPES), (
    f"_VALID_ARCHETYPES must be a non-empty set of strings; got {_VALID_ARCHETYPES!r}. "
    "Did the Contract.archetype annotation shape change (e.g. wrapped in Optional/Union)?")

CONTRACT_RESOLVER_SYSTEM = """\
You are a requirements analyst for the CPMS framework. From a spec, a confirmed \
Vue mockup, and real DB table info, produce ONE structured CONTRACT as JSON. \
Do NOT generate code.

Output ONLY a JSON object with keys:
  identity: {module, category, screen_id, class_name, program_id, window_id, menu_id, p_menu_id}
  archetype: one of "list" | "list-detail" | "edit" | "popup" | "tab-detail"
  ops: subset of ["selectList","count","selectOne","insert","update","delete"]
  table: {name, pk: [...], columns: [{snake, camel, db_type, java_type, pk, nullable, searchable, audit, code}]}
  fields: {request: [{camel, snake, java_type, optional, filter}], response: [{camel, snake, java_type, is_status}]}
  api: [{method, service_id, url, req_dto, res_dto, authority}]
  frontend: {components: [...], search_fields: [...], columns: [...], common_code_load}
  seed: {labels: [...], menu: {...}, common_codes: [...], pgm_url}

Rules:
- identity.module is the LV1 domain code (e.g. "edu", "sy"); identity.category is the
  LV2 grouping (e.g. "pondg", "ds"). BOTH are required — infer them from the spec /
  screen code / menu context. screen_id is camelCase; class_name is PascalCase.
- program_id is the SPEC Screen Metadata program id, verbatim.
- Map every Vue field to its real DB column using the table info. Dates/IDs are String.
- fields[].filter must be one of "ILIKE", "eq", "range", or "" (empty).
- frontend.components MUST be a subset of ["SearchForm", "DataTable", "SumGrid", "ProgressList"];
  use no other names. Include "SearchForm"/"DataTable" for normal query/list screens.
  Include "SumGrid" ONLY if the screen needs per-status aggregate counts with click-to-filter.
  Never include "ProgressList" unless explicitly requested.
- table.columns[].code: when a column maps to a common code, set it to the common-code
  class id as a STRING (e.g. "riskClsfCd"); OMIT the field otherwise. It is NEVER a boolean.
- frontend.search_fields: an array of camelCase field-NAME STRINGS (the search inputs),
  e.g. ["riskNm","deptNm"] — strings only, NOT objects.
- frontend.columns: an array of camelCase field-NAME STRINGS naming the DataTable
  columns to display, in display order, e.g. ["riskNm","deptNm","idfyDt"] — strings
  only, NOT objects. (Headers come from i18n; types come from table.columns.)
- frontend.common_code_load: a SINGLE string — one of "ensureLoaded" | "ensureLoadedMulti" | "loadMulti".
- Omit any optional field you don't have rather than setting it to null.
- The contract is the single source of truth for all downstream generation.
"""


def _build_user(state: dict) -> str:
    return (
        f"=== SPEC ===\n{state.get('spec_markdown') or ''}\n\n"
        f"=== CONFIRMED VUE ===\n{state.get('confirmed_vue') or ''}\n\n"
        f"=== TABLE INFO ===\n{state.get('table_info') or ''}\n\n"
        f"=== CONFIRMED PAGE TYPE ===\n{state.get('page_type') or ''}\n"
    )


def _drop_nones(obj):
    """Recursively drop null values so pydantic falls back to field defaults.

    Real gpt-5.5 routinely emits `null` for optional fields (e.g. menu_id, seed.menu);
    with `null` present pydantic raises string_type/dict_type errors against the
    schema's typed defaults. Dropping nulls lets defaults apply. A REQUIRED field set
    to null is still dropped -> 'field required' -> caught -> retry (validation intact).
    """
    if isinstance(obj, dict):
        return {k: _drop_nones(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_drop_nones(v) for v in obj]
    return obj


async def contract_resolve(state: dict) -> dict:
    """LLM -> JSON -> pydantic-validated Contract (one retry). Returns {contract, events}."""
    user = _build_user(state)
    page_type = state.get("page_type") or ""
    last_err: Exception | None = None
    last_raw = ""
    for attempt in range(2):
        prompt = user if attempt == 0 else user + "\n\nReturn ONLY valid JSON matching the schema."
        raw = await gpt55_client.complete(CONTRACT_RESOLVER_SYSTEM, prompt)
        last_raw = raw
        try:
            data = _drop_nones(json.loads(_strip_fences(raw)))
            # The confirmed mockup page_type is authoritative over the model's archetype
            # guess — apply it BEFORE validation (so the Literal check still covers it),
            # but only when it is a recognized archetype.
            if isinstance(data, dict) and page_type in _VALID_ARCHETYPES:
                data["archetype"] = page_type
            contract = parse_contract(data)
        except (ValueError, ValidationError) as exc:   # json error or schema violation
            last_err = exc
            continue
        cdict = contract.model_dump()
        return {"contract": cdict,
                "events": [{"type": "contract", "contract": cdict}]}
    raise ValueError(
        f"contract_resolve: invalid contract after retry: {last_err} "
        f"(reply head: {last_raw[:120]!r})")
