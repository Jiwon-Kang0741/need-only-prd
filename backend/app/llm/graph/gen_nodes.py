"""LangGraph node wrappers for the contract-first generators.

Each generator returns {path: content} strings; these wrappers wrap them into the
CodeGenState GeneratedFile shape (file_type/layer looked up from contract bindings)
and accumulate into state["files"]. Linear graph: contract_resolve -> plan_and_bind
-> gen_backend -> gen_frontend -> gen_data -> validate.
"""

from __future__ import annotations

from app.llm.graph import guides, gen_backend, gen_frontend, gen_data
from app.llm.graph.gen_backend import render_dao
from app.llm.graph.backend_validate import validate_backend
from app.llm.graph.frontend_validate import validate_frontend
from app.llm.graph.data_validate import validate_data


def _meta_map(contract: dict) -> dict:
    return {f["file_path"]: f for f in contract.get("bindings", {}).get("files", [])}


def _wrap(files: dict, meta: dict) -> dict:
    out = {}
    for path, content in files.items():
        m = meta.get(path, {})
        out[path] = {"file_path": path, "file_type": m.get("file_type", ""),
                     "layer": m.get("layer", ""), "wave": 0, "content": content,
                     "status": "ok", "status_log": []}
    return out


async def gen_backend_node(state: dict) -> dict:
    contract = state["contract"]
    meta = _meta_map(contract)
    guide = guides.load_guide_for_file_type("dao_impl")
    dao_path = contract["bindings"]["paths"]["dao_impl"]
    dtos = await gen_backend.gen_dtos(contract, guide)
    mapper = await gen_backend.gen_mapper(contract, guide, dtos)
    dao_src = render_dao(contract)
    service = await gen_backend.gen_service(contract, guide, dao_src, dtos)
    files = {**dtos, **mapper, dao_path: dao_src, **service}
    return {"files": _wrap(files, meta),
            "events": [{"type": "log", "line": f"[backend] generated {len(files)} files"}]}


async def gen_frontend_node(state: dict) -> dict:
    contract = state["contract"]
    meta = _meta_map(contract)
    guide = guides.load_guide_for_file_type("vue_page")
    paths = contract["bindings"]["paths"]
    types = await gen_frontend.gen_types(contract, guide)
    types_src = next(iter(types.values()), "")
    api = await gen_frontend.gen_api(contract, guide, types_src)
    comp_files: dict = {}
    child_sources: dict = {}
    screen = contract["identity"]["class_name"]
    for comp in contract.get("frontend", {}).get("components", []):
        cf = await gen_frontend.gen_component(contract, guide, comp, types_src)
        comp_files.update(cf)
        vue_path = paths.get(f"vue_{comp.lower()}")
        if vue_path and vue_path in cf:
            child_sources[f"{screen}{comp}"] = cf[vue_path]
    index = await gen_frontend.gen_index(contract, guide, child_sources, types_src)
    files = {**types, **api, **comp_files, **index}
    return {"files": _wrap(files, meta),
            "events": [{"type": "log", "line": f"[frontend] generated {len(files)} files"}]}


async def gen_data_node(state: dict) -> dict:
    contract = state["contract"]
    meta = _meta_map(contract)
    guide = guides.load_guide_for_file_type("db_init_sql")
    ddl = await gen_data.gen_ddl(contract, guide)
    seed = await gen_data.gen_seed(contract, guide)
    files = gen_data.assemble_sql(contract, ddl, seed)
    return {"files": _wrap(files, meta),
            "events": [{"type": "log", "line": "[data] generated db/init.sql"}]}


def validate_node(state: dict) -> dict:
    contract = state["contract"]
    files = state.get("files", {})
    issues = validate_backend(files, contract) + validate_frontend(files, contract)
    db = next((gf["content"] for gf in files.values()
               if gf.get("file_type") == "db_init_sql"), "")
    if db:
        issues = issues + validate_data(db, contract)
    return {"open_issues": issues,
            "events": [{"type": "log", "line": f"[validate] {len(issues)} issue(s)"}]}
