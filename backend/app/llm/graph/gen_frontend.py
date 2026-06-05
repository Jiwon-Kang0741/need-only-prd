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
