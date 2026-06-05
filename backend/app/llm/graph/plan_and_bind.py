"""File-Plan + Bindings — deterministic derivation from the resolved Contract.

Replaces the blind planner + path-rewriting derive_contract. From the contract it
computes: target paths (Phase-1 paths resolver, guide-driven), the statement-id /
dao-method set (naming, 1:1), Java packages + Mapper namespace, and the concrete
file plan (every artifact with path/file_type/layer). Pure — no LLM, no I/O beyond
reading the fixed guide via the path resolver.
"""

from __future__ import annotations

from app.llm.graph import naming, paths

# Generated backend/data file types (interfaces are NOT generated; see BackendGuide §4.4).
_BACKEND_TYPES = ("dto_request", "dto_response", "mapper_xml", "dao_impl", "service_impl")
_DATA_TYPES = ("db_init_sql",)
_LAYER = ({t: "backend" for t in _BACKEND_TYPES}
          | {t: "data" for t in _DATA_TYPES})


def _identity(contract: dict) -> paths.Identity:
    i = contract["identity"]
    return paths.Identity(module=i["module"], category=i["category"],
                          screen_id=i["screen_id"], class_name=i["class_name"])


def _ops(contract: dict) -> list[str]:
    ops = contract.get("ops") or []
    if ops:
        return ops
    return naming.ops_for_screen_type(contract.get("archetype", "list"))


def plan_and_bind(state: dict) -> dict:
    """Contract -> {contract (with bindings), plan}. Deterministic."""
    contract = dict(state["contract"])
    ident = _identity(contract)
    screen = ident.class_name

    # 1) paths (backend/data from §11.4 templates; frontend from resolver)
    path_map: dict[str, str] = {}
    files: list[dict] = []
    for ft in _BACKEND_TYPES + _DATA_TYPES:
        p = paths.backend_path(ft, ident)
        if p:
            path_map[ft] = p
            files.append({"file_path": p, "file_type": ft, "layer": _LAYER[ft]})
    fe = paths.frontend_paths(ident, contract.get("frontend", {}).get("components", []))
    for ft, p in fe.items():
        path_map[ft] = p
        files.append({"file_path": p, "file_type": ft, "layer": "frontend"})

    # 2) statement ids == dao methods (1:1), from ops
    stmt_ids = [naming.statement_id(op, screen) for op in _ops(contract)]

    # 3) packages (from the java paths) + mapper namespace
    pkgs: dict[str, str] = {}
    for ft in _BACKEND_TYPES:
        p = path_map.get(ft)
        if p and p.endswith(".java"):
            pkg = naming.package_from_java_path(p)
            if pkg:
                pkgs[ft] = pkg
    dao_pkg = pkgs.get("dao_impl", f"biz.{ident.module}.dao")
    namespace = f"{dao_pkg}.{screen}DaoImpl"

    contract["bindings"] = {
        **contract.get("bindings", {}),
        "statement_ids": stmt_ids,
        "dao_methods": list(stmt_ids),
        "namespace": namespace,
        "packages": pkgs,
        "paths": path_map,
        "files": files,
    }
    return {"contract": contract,
            "plan": {"files": files},
            "events": [{"type": "plan", "files": files}]}
