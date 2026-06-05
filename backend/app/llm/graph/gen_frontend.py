"""Frontend code generators: TypeScript types and API client.

Consumes the Phase-2 Contract + bindings. Both generators call gpt55_client
and return {bound_path: fence_stripped_content}.
"""

from __future__ import annotations

import json

from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import GENERATOR_SYSTEM
from app.llm.graph._text import strip_fences as _strip_fences


async def gen_types(contract: dict, guide: str) -> dict:
    """Generate the category-shared types.ts (SearchParams + response interfaces).

    Returns {vue_types_path: content} with fences stripped.
    """
    paths = contract["bindings"]["paths"]
    vue_types_path = paths["vue_types"]

    fields_json = json.dumps(contract["fields"], ensure_ascii=False)
    dto_names = ", ".join(
        f"{e['req_dto']} / {e['res_dto']}"
        for e in contract.get("api", [])
    )
    identity = contract["identity"]

    user = (
        f"GUIDE:\n{guide}\n\n"
        f"CONTRACT FIELDS:\n{fields_json}\n\n"
        f"DTO NAMES: {dto_names}\n\n"
        f"TARGET FILE: {vue_types_path}\n\n"
        f"Generate the TypeScript types file for module={identity['module']} "
        f"category={identity.get('category', '')}. "
        f"Define SearchParams and response interfaces in this shared types.ts. "
        f"All field names must be camelCase (e.g. empNm). "
        f"Output ONLY the file content."
    )

    reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    return {vue_types_path: _strip_fences(reply)}


async def gen_api(contract: dict, guide: str, types: str) -> dict:
    """Generate the screen-level API client (vue_api path).

    Returns {vue_api_path: content} with fences stripped.
    """
    paths = contract["bindings"]["paths"]
    vue_api_path = paths["vue_api"]

    urls = "\n".join(e["url"] for e in contract.get("api", []))
    identity = contract["identity"]

    user = (
        f"GUIDE:\n{guide}\n\n"
        f"API ENDPOINTS (one per line):\n{urls}\n\n"
        f"DEPENDENCY TYPES SOURCE:\n{types}\n\n"
        f"TARGET FILE: {vue_api_path}\n\n"
        f"Generate the TypeScript API client for screen={identity['screen_id']}. "
        f"Use api.post() for every call (GET is forbidden); params camelCase. "
        f"Import types from the shared types file. "
        f"Output ONLY the file content."
    )

    reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    return {vue_api_path: _strip_fences(reply)}


async def gen_component(contract: dict, guide: str, comp: str, types: str) -> dict:
    """Generate a single Vue3 component (SearchForm / DataTable / SumGrid).

    Returns {vue_{comp}_path: content, vue_{comp}_scss_path: scss_stub}
    and for DataTable also {vue_datatable_utils_path: utils_content}.
    """
    paths = contract["bindings"]["paths"]
    identity = contract["identity"]
    class_name = identity["class_name"]
    screen_id = identity["screen_id"]
    frontend = contract.get("frontend", {})

    comp_key = f"vue_{comp.lower()}"
    scss_key = f"vue_{comp.lower()}_scss"
    vue_path = paths[comp_key]
    scss_path = paths[scss_key]

    # Build component-specific prompt hints
    if comp == "DataTable":
        columns_json = json.dumps(frontend.get("columns", []), ensure_ascii=False)
        comp_hints = (
            f"Component role: DataTable — renders a PrimeVue DataTable2 wrapper.\n"
            f"REQUIREMENTS:\n"
            f"- Import and use DataTable2 (wrapper) with prop :columns\n"
            f"- Use TableColumn for each column definition\n"
            f"- scrollHeight=\"540px\" (never flex)\n"
            f"- Use virtualScrollerOptions for large datasets\n"
            f"- Columns definition (JSON):\n{columns_json}\n"
            f"- Receive rows data as prop; emit row-select events\n"
            f"- Use <script setup lang=\"ts\">\n"
        )
    elif comp == "SearchForm":
        search_fields = frontend.get("search_fields", [])
        comp_hints = (
            f"Component role: SearchForm — provides search parameter inputs.\n"
            f"REQUIREMENTS:\n"
            f"- Use inject to receive searchParams from parent (index.vue provides it)\n"
            f"- searchParams is a reactive ref; bind input fields to searchParams.value\n"
            f"- Use SearchFormRow layout component for each row of inputs\n"
            f"- Watch searchParams; guard with !== undefined before use\n"
            f"- Search fields: {search_fields}\n"
            f"- Emit 'search' event on button click\n"
            f"- Use <script setup lang=\"ts\">\n"
        )
    elif comp == "SumGrid":
        comp_hints = (
            f"Component role: SumGrid — displays summary/aggregated data.\n"
            f"REQUIREMENTS:\n"
            f"- Receive statusFilter prop from parent\n"
            f"- React to statusFilter changes to recompute displayed rows\n"
            f"- Use <script setup lang=\"ts\">\n"
        )
    else:
        comp_hints = (
            f"Component role: {comp}\n"
            f"REQUIREMENTS:\n"
            f"- Use <script setup lang=\"ts\">\n"
        )

    user = (
        f"GUIDE:\n{guide}\n\n"
        f"DEPENDENCY TYPES SOURCE:\n{types}\n\n"
        f"TARGET FILE: {vue_path}\n"
        f"SCREEN: {screen_id}  CLASS: {class_name}\n\n"
        f"{comp_hints}\n"
        f"Output ONLY the file content."
    )

    result: dict = {scss_path: f"/* {class_name}{comp} styles */\n"}

    # DataTable also needs utils/index.ts — generate BEFORE the .vue so that
    # the .vue call is always last and c.last_user carries the component hints.
    if comp == "DataTable":
        utils_path = paths["vue_datatable_utils"]
        utils_user = (
            f"GUIDE:\n{guide}\n\n"
            f"DEPENDENCY TYPES SOURCE:\n{types}\n\n"
            f"TARGET FILE: {utils_path}\n"
            f"SCREEN: {screen_id}  CLASS: {class_name}\n\n"
            f"Generate a TypeScript utility module for the DataTable component.\n"
            f"REQUIREMENTS:\n"
            f"- Export getColumns(t): returns column definitions array\n"
            f"- Export getRows(data): transforms raw API response to table row format\n"
            f"- Follow the guide conventions for column/row helpers\n"
            f"Output ONLY the file content."
        )
        utils_reply = await gpt55_client.complete(GENERATOR_SYSTEM, utils_user)
        result[utils_path] = _strip_fences(utils_reply)

    vue_reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    result[vue_path] = _strip_fences(vue_reply)

    return result


async def gen_index(contract: dict, guide: str, components: dict, types: str) -> dict:
    """Generate index.vue (the page root) after all child components are ready.

    ``components`` maps component class name → source code so the prompt can
    reference real props/emits.

    Returns {vue_page_path: content, vue_page_scss_path: scss_stub}.
    """
    paths = contract["bindings"]["paths"]
    identity = contract["identity"]
    class_name = identity["class_name"]
    screen_id = identity["screen_id"]
    window_id = identity["window_id"]

    vue_page_path = paths["vue_page"]
    vue_page_scss_path = paths["vue_page_scss"]

    # Build child sources section
    children_section = "\n\n".join(
        f"--- {name} ---\n{source}" for name, source in components.items()
    )
    child_names = ", ".join(components.keys())

    user = (
        f"GUIDE:\n{guide}\n\n"
        f"DEPENDENCY TYPES SOURCE:\n{types}\n\n"
        f"CHILD COMPONENT SOURCES (for reference):\n{children_section}\n\n"
        f"TARGET FILE: {vue_page_path}\n"
        f"SCREEN: {screen_id}  CLASS: {class_name}  WINDOW_ID: {window_id}\n\n"
        f"Generate index.vue — the page root that orchestrates: {child_names}.\n"
        f"REQUIREMENTS:\n"
        f"- Use <script setup lang=\"ts\">\n"
        f"- provide('searchParams', searchParams) so child SearchForm can inject it\n"
        f"- provide('t', t) for i18n injection\n"
        f"- searchParams is a reactive ref initialized with default values\n"
        f"- Call onMounted(() => handleSearch()) to load data on mount\n"
        f"- Include <ContentHeader menuId=\"{window_id}\" />\n"
        f"- Register and use all child components: {child_names}\n"
        f"- Wire child emit events to parent handlers\n"
        f"Output ONLY the file content."
    )

    reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    return {
        vue_page_path: _strip_fences(reply),
        vue_page_scss_path: f"/* {screen_id} page styles */\n",
    }
