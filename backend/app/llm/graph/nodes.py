"""Code-generation graph nodes (pure async functions)."""

from __future__ import annotations

import json

from app.llm.graph import guides
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import CONTRACT_SYSTEM, GENERATOR_SYSTEM, PLANNER_SYSTEM
from app.llm.graph.waves import wave_for_file_type, files_in_wave
from app.llm.graph.tools import static_check_impl, validate_sql_impl
from app.llm.graph.config import GATE_MAX_REGEN
from app.llm.graph._text import strip_fences as _strip_fences
from app.llm.graph import naming


def _parse_json(text: str) -> dict:
    return json.loads(_strip_fences(text))


async def contract_extract(state: dict) -> dict:
    """Extract structured contract from spec + confirmed Vue + table info."""
    user = (
        f"=== SPEC ===\n{state['spec_markdown']}\n\n"
        f"=== CONFIRMED VUE ===\n{state['confirmed_vue']}\n\n"
        f"=== TABLE INFO ===\n{state.get('table_info', '')}\n"
    )
    raw = await gpt55_client.complete(CONTRACT_SYSTEM, user)
    try:
        contract = _parse_json(raw)
    except (ValueError, json.JSONDecodeError):
        # one retry with explicit instruction
        raw = await gpt55_client.complete(
            CONTRACT_SYSTEM, user + "\n\nReturn ONLY valid JSON.")
        try:
            contract = _parse_json(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"contract_extract: model did not return valid JSON after retry: {exc}"
            ) from exc
    # The confirmed mockup page_type is authoritative — override the LLM's guess so
    # a CRUD screen (list-detail) is not silently narrowed to list.
    page_type = state.get("page_type") or ""
    if page_type:
        contract.setdefault("screen", {})
        contract["screen"]["type"] = page_type
    return {"contract": contract,
            "events": [{"type": "contract", "contract": contract}]}


async def planner(state: dict) -> dict:
    """Plan files from contract; wave numbers assigned by code (not LLM)."""
    user = f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n"
    raw = await gpt55_client.complete(PLANNER_SYSTEM, user)
    plan = _parse_json(raw)
    for f in plan.get("files", []):
        f["wave"] = wave_for_file_type(f["file_type"])
    events = [{"type": "plan", "files": plan.get("files", [])}]
    wave1 = len(files_in_wave(plan, 1))
    if wave1:
        events.append({"type": "wave_start", "wave": 1, "file_count": wave1})
    return {"plan": plan, "current_wave": 1, "events": events}


def _gate_check(spec: dict, content: str) -> list[dict]:
    """Run the deterministic gate for a file (static_check, or validate_sql for SQL)."""
    if spec["file_type"] == "db_init_sql":
        return validate_sql_impl(content)
    return static_check_impl(spec["file_path"], content, spec["file_type"], spec["layer"])


# Which earlier-wave file types each file type actually needs as context.
# Avoids dumping ALL earlier files into every prompt (token blowup).
_DEP_FILE_TYPES: dict[str, set[str]] = {
    "dao": {"dto_request", "dto_response"},
    "dao_impl": {"dto_request", "dto_response"},
    "mapper_xml": {"dto_request", "dto_response"},
    "vue_page": {"vue_types"},
    "service": {"dto_request", "dto_response", "dao", "dao_impl"},
    "service_impl": {"dto_request", "dto_response", "dao", "dao_impl"},
}


def _dep_context(state: dict, spec: dict) -> str:
    """Inject only the earlier-wave files this file type actually depends on."""
    wanted = _DEP_FILE_TYPES.get(spec["file_type"])
    if wanted is None:
        return ""
    my_wave = spec["wave"]
    deps = [gf for gf in state.get("files", {}).values()
            if gf["wave"] < my_wave and gf["file_type"] in wanted]
    if not deps:
        return ""
    parts = [f"--- {gf['file_path']} ---\n{gf['content']}" for gf in deps]
    return "\n\n=== DEPENDENCY FILES ===\n" + "\n\n".join(parts)


def _contract_section_for(file_type: str, contract: dict) -> str:
    """Build a 'REQUIRED IDENTIFIERS' prompt section for a file type. '' if N/A."""
    ops = (contract or {}).get("operations") or []
    dtos = {d["name"]: d for d in (contract or {}).get("dtos") or []}

    def _op_lines():
        return "\n".join(
            f"- {o['op']}: dao_method={o['dao_method']}, statement_id={o['statement_id']}, "
            f"param={o['param_type']}, return={o['return_type']}, tag={o['mybatis_tag']}"
            for o in ops)

    def _dto_block(name):
        d = dtos.get(name)
        if not d:
            return ""
        flds = "\n".join(f"  - {f['name']}: {f['java_type']}" for f in d["fields"])
        return f"{name} fields:\n{flds}"

    if file_type == "dao_impl":
        return "DAO methods (implement EXACTLY):\n" + _op_lines() if ops else ""
    if file_type == "mapper_xml":
        return ("Mapper statements (use these EXACT ids/tags; namespace = DaoImpl FQCN):\n"
                + _op_lines()) if ops else ""
    if file_type == "service_impl":
        return "Call these DAO methods:\n" + _op_lines() if ops else ""
    if file_type == "dto_request":
        return _dto_block(next((n for n in dtos if n.endswith("ReqDto")), ""))
    if file_type == "dto_response":
        return _dto_block(next((n for n in dtos if n.endswith("ResDto")), ""))
    if file_type == "vue_types":
        blocks = [_dto_block(n) for n in dtos]
        return "\n\n".join(b for b in blocks if b)
    return ""


async def generate_file(state: dict) -> dict:
    """Generate ONE file (single-shot) + static_check gate (1 regen). For Send fan-out."""
    spec = state["_file_spec"]
    guide = guides.load_guide_for_file_type(spec["file_type"])
    req_ids = _contract_section_for(spec["file_type"], state["contract"])
    base_user = (
        f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n\n"
        + (f"=== REQUIRED IDENTIFIERS (use EXACTLY, do not rename) ===\n{req_ids}\n\n"
           if req_ids else "")
        + f"=== GUIDE ===\n{guide}\n"
        + f"{_dep_context(state, spec)}\n\n"
        + f"Generate file: {spec['file_path']} (type={spec['file_type']}, "
        + f"class={spec.get('class_name', '')})\n{spec.get('description', '')}"
    )
    content = _strip_fences(await gpt55_client.complete(GENERATOR_SYSTEM, base_user))
    issues = _gate_check(spec, content)

    regen = 0
    while issues and regen < GATE_MAX_REGEN:
        fix_user = (base_user + "\n\n=== FIX THESE VIOLATIONS ===\n"
                    + "\n".join(f"- {i['issue']}" for i in issues))
        content = _strip_fences(await gpt55_client.complete(GENERATOR_SYSTEM, fix_user))
        issues = _gate_check(spec, content)
        regen += 1

    # If the gate still reports issues after the allowed regens, mark the file
    # 'failed' so downstream (reviewer, deploy) can distinguish it from a clean
    # one instead of trusting a hardcoded 'ok'.
    status = "failed" if issues else "ok"
    gf = {"file_path": spec["file_path"], "file_type": spec["file_type"],
          "layer": spec["layer"], "wave": spec["wave"], "content": content,
          "status": status, "status_log": [f"gate regen={regen}, issues={len(issues)}"]}
    result = {"files": {spec["file_path"]: gf},
              "events": [{"type": "file_complete", "path": spec["file_path"],
                          "layer": spec["layer"]}]}
    if issues:
        result["open_issues"] = issues  # passed through; reviewer will handle
    return result


def _screen_code_from_plan(plan: dict, fallback: str) -> str:
    """Derive the ScreenCode (e.g. 'CpmsEduRsltLst') from a planned DTO/DAO file name."""
    for f in plan.get("files", []):
        name = f["file_path"].split("/")[-1]
        for suffix in ("ReqDto.java", "ResDto.java", "DaoImpl.java", "Mapper.xml"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
    return fallback


# op → required file_type for that op to be generated (skip op if file absent)
_OP_REQUIRES = {
    "selectList": "dao_impl", "selectOne": "dao_impl", "count": "dao_impl",
    "insert": "dao_impl", "update": "dao_impl", "delete": "dao_impl",
}


def _api_signature_ops(api_signatures: list) -> list[str]:
    """Map api_signatures to standard ops (best-effort)."""
    ops: list[str] = []
    for sig in api_signatures or []:
        path = (sig.get("path") or "").lower()
        if "count" in path:
            ops.append("count")
        elif "list" in path:
            ops.append("selectList")
        elif "save" in path or "insert" in path:
            ops.append("insert")
        elif "update" in path:
            ops.append("update")
        elif "delete" in path:
            ops.append("delete")
    return ops


async def derive_contract(state: dict) -> dict:
    """Augment contract with code-level identifiers (operations + dtos). Code only."""
    contract = dict(state.get("contract") or {})
    plan = state.get("plan") or {}
    screen = contract.get("screen") or {}
    try:
        screen_code = _screen_code_from_plan(plan, screen.get("id", "Screen"))
        req_dto = naming.dto_class(screen_code, "request")
        res_dto = naming.dto_class(screen_code, "response")

        planned_types = {f["file_type"] for f in plan.get("files", [])}
        ops = naming.ops_for_screen_type(screen.get("type", "list"))
        for extra in _api_signature_ops(contract.get("api_signatures", [])):
            if extra not in ops:
                ops.append(extra)

        operations = []
        for op in ops:
            required = _OP_REQUIRES.get(op)
            if required and required not in planned_types:
                continue
            is_list = op == "selectList"
            ret = (f"List<{res_dto}>" if is_list
                   else "int" if op == "count"
                   else res_dto)
            operations.append({
                "op": op,
                "statement_id": naming.statement_id(op),
                "dao_method": naming.dao_method(op),
                "param_type": req_dto,
                "return_type": ret,
                "mybatis_tag": naming.mybatis_tag(op),
            })

        def _fields():
            return [{"name": f["vue_field"],
                     "java_type": naming.java_type(f.get("type", "string")),
                     "db_column": f.get("db_column", "")}
                    for f in contract.get("fields", [])]

        dtos = [
            {"name": req_dto, "kind": "request", "fields": _fields()},
            {"name": res_dto, "kind": "response", "fields": _fields()},
        ]
        contract["operations"] = operations
        contract["dtos"] = dtos
    except Exception as e:
        return {"events": [{"type": "log", "line": f"[CONTRACT] derive failed: {e}"}]}

    return {"contract": contract,
            "events": [{"type": "log",
                        "line": f"[CONTRACT] derived {len(contract.get('operations', []))} ops, "
                                f"{len(contract.get('dtos', []))} dtos"}]}
