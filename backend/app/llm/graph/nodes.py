"""Code-generation graph nodes (pure async functions)."""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath

from app.llm.graph import guides
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import CONTRACT_SYSTEM, GENERATOR_SYSTEM, PLANNER_SYSTEM
from app.llm.graph.waves import wave_for_file_type, files_in_wave
from app.llm.graph.tools import static_check_impl, validate_sql_impl
from app.llm.graph.config import GATE_MAX_REGEN
from app.llm.graph._text import strip_fences as _strip_fences
from app.llm.graph import naming
from app.llm.graph.cpms_checks import extract_markdown_section


def _parse_json(text: str) -> dict:
    return json.loads(_strip_fences(text))


# File types that live in the Vue frontend; everything else is backend. Used to
# enforce the layer deterministically (DockerManager routes by layer).
_FRONTEND_FILE_TYPES = {"vue_page", "vue_types"}


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


def _db_seed_prompt_block(spec_markdown: str) -> str:
    """Build focused DB-seed guidance from SPEC Section 7 + CPMS seed rules.

    Ported from agents._build_section7_extract_block. Injected into db_init_sql
    prompts so the generator follows the seed standard up front (paired with the
    db_seed validator in cpms_checks)."""
    if not spec_markdown:
        return ""
    sec7 = extract_markdown_section(spec_markdown, "## 7.")
    return (
        "\n=== DB SEED RULES (SPEC Section 7 priority) ===\n"
        f"{sec7 or '(Section 7 not found; follow global DB seed rules strictly)'}\n\n"
        "MUST APPLY to db_init_sql:\n"
        "- Required seed tables: cmn_lbl, cmn_pgm, cmn_menu, cmn_role_pgm, cmn_role_menu\n"
        "- Optional (only if SPEC §10.3 has rows): cmn_class, cmn_code — if seeded, BOTH must appear\n"
        "- Insert order: cmn_class -> cmn_code -> cmn_lbl -> cmn_pgm -> cmn_menu -> "
        "cmn_role_pgm -> cmn_role_menu\n"
        "- PostgreSQL upsert only: INSERT ... ON CONFLICT ... DO UPDATE (never MERGE)\n"
        "- cmn_lbl.lang_cd default 'ko-KR'\n"
        "- Include DEV_AUTO role in cmn_role_pgm and cmn_role_menu; ROOT98 fallback parent\n"
        "- cmn_lbl label IDs: {화면코드}.{대컴포넌트명}.{라벨ID} (e.g. SearchForm.*, DataTable.*)\n"
        "=== END DB SEED RULES ===\n"
    )


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


_PACKAGE_DECL_RE = re.compile(r"^\s*package\s+[\w.]+\s*;", re.MULTILINE)


def _enforce_java_package(content: str, file_path: str) -> str:
    """Force a .java file's `package` declaration to match its on-disk path.

    Paths are derived deterministically (naming.file_path); the generator LLM may
    still declare a different package (e.g. com.example.*). Rewriting it here keeps
    package==path, which in turn fixes the Mapper namespace (autofix_binding derives
    it from the DaoImpl package). No-op for non-Java paths."""
    expected = naming.package_from_java_path(file_path)
    if not expected:
        return content
    if _PACKAGE_DECL_RE.search(content):
        return _PACKAGE_DECL_RE.sub(f"package {expected};", content, count=1)
    return f"package {expected};\n\n{content}"


# Default `import Name from './path.vue'` — a LOCAL (relative) child component.
# Alias imports (@/...) are skeleton-provided and intentionally NOT matched.
_VUE_LOCAL_VUE_IMPORT_RE = re.compile(
    r"""import\s+(\w+)\s+from\s+['"](\.\.?/[^'"]+\.vue)['"]""")


def _frontend_guide_prefix_for(comp_name: str) -> str:
    """Pick the focused FrontendGuide file prefix for a child component by name."""
    if "SearchForm" in comp_name:
        return "03_"
    if "DataTable" in comp_name:
        return "04_"
    if "SumGrid" in comp_name or "ProgressBar" in comp_name:
        return "05_"
    return "02_"  # generic component structure


async def _expand_vue_components(index_content: str, index_path: str, spec: dict) -> dict:
    """Generate the local child components that index.vue imports.

    The guide mandates a multi-file vue page (index.vue + components/SearchForm,
    DataTable, ...). The planner only produces index.vue, so its `./components/*.vue`
    imports would dangle. Here we generate exactly those imported files (at the
    path the import resolves to) so the multi-file structure is real and the
    frontend builds. Returns {path: GeneratedFile-dict}."""
    base = PurePosixPath(index_path).parent
    rules = guides.load_codegen_rules()
    out: dict = {}
    for comp_name, rel in _VUE_LOCAL_VUE_IMPORT_RE.findall(index_content):
        comp_path = base.joinpath(rel).as_posix()
        if comp_path in out:
            continue
        guide = guides.load_named_frontend_guide(_frontend_guide_prefix_for(comp_name))
        user = (
            (f"=== CODE GENERATION RULES (반드시 준수) ===\n{rules}\n\n" if rules else "")
            + f"=== PAGE index.vue (imports <{comp_name}>) ===\n{index_content}\n\n"
            + f"=== GUIDE ===\n{guide}\n\n"
            + f"Generate the Vue3 child component `{comp_name}` (file: {comp_path}).\n"
            + "- Use <script setup lang=\"ts\">.\n"
            + f"- defineProps/defineEmits MUST match EXACTLY how index.vue uses "
            + f"<{comp_name}> (the props bound and events listened above).\n"
            + "- Follow the guide (DataTable2 :columns prop, scrollHeight=\"540px\", "
            + "date pre-format in getRows(), no alert()/confirm()).\n"
            + "- Import shared types from the same @/api/pages/... path index.vue uses.\n"
            + "Output ONLY the .vue file content, no markdown fences."
        )
        content = _strip_fences(await gpt55_client.complete(GENERATOR_SYSTEM, user))
        issues = static_check_impl(comp_path, content, "vue_component", "frontend")
        out[comp_path] = {
            "file_path": comp_path, "file_type": "vue_component", "layer": "frontend",
            "wave": spec["wave"], "content": content,
            "status": "failed" if issues else "ok",
            "status_log": [f"vue component (gate issues={len(issues)})"],
        }
    return out


async def generate_file(state: dict) -> dict:
    """Generate ONE file (single-shot) + static_check gate (1 regen). For Send fan-out."""
    spec = state["_file_spec"]
    guide = guides.load_guide_for_file_type(spec["file_type"])
    req_ids = _contract_section_for(spec["file_type"], state["contract"])
    # db_init_sql gets SPEC Section-7 seed rules up front. The DataGuide itself is
    # injected in full via the layer guide (load_guide_for_file_type → DataGuide/),
    # so no separate excerpt is added here (would be redundant).
    seed_block = ""
    if spec["file_type"] == "db_init_sql":
        seed_block = _db_seed_prompt_block(state.get("spec_markdown", ""))
    # vue files get the inferred frontend archetype + reference context.
    elif spec["file_type"] in ("vue_page", "vue_types"):
        from app.llm.graph.frontend_ctx import archetype_prompt_block
        seed_block = archetype_prompt_block(state.get("spec_markdown", ""),
                                            state.get("plan", {}))
    # Ground the generator in the deterministic target location so it declares the
    # right package and imports siblings via their hsc.tomms.web.* packages.
    pkg = naming.package_from_java_path(spec["file_path"])
    target_block = ""
    if pkg:
        target_block = (
            "=== TARGET LOCATION (deterministic — declare EXACTLY) ===\n"
            f"Java package: {pkg}\n"
            "Import sibling classes via their hsc.tomms.web.* packages "
            "(see DEPENDENCY FILES). Do NOT use com.example.* or any other root.\n\n"
        )
    # Spine: the distilled must-follow rules, injected into EVERY generate_file
    # prompt on top of the layer-specific guide (CODEGEN_RULES.md).
    rules_spine = guides.load_codegen_rules()
    base_user = (
        (f"=== CODE GENERATION RULES (반드시 준수) ===\n{rules_spine}\n\n"
         if rules_spine else "")
        + f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n\n"
        + (f"=== REQUIRED IDENTIFIERS (use EXACTLY, do not rename) ===\n{req_ids}\n\n"
           if req_ids else "")
        + target_block
        + (f"{seed_block}\n" if seed_block else "")
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

    # Deterministic package enforcement: the file path is canonical, so the Java
    # `package` must match it (the LLM occasionally declares com.example.*).
    if spec["file_path"].endswith(".java"):
        content = _enforce_java_package(content, spec["file_path"])

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

    # vue_page is multi-file: generate the local child components it imports so the
    # ./components/*.vue references resolve (guide-mandated structure).
    if spec["file_type"] == "vue_page":
        components = await _expand_vue_components(content, spec["file_path"], spec)
        result["files"].update(components)
        for cpath, cgf in components.items():
            result["events"].append({"type": "file_complete", "path": cpath,
                                     "layer": "frontend"})
            if cgf["status"] == "failed":
                result.setdefault("open_issues", [])
                result["open_issues"] = result["open_issues"] + [
                    {"file_path": cpath, "issue": "vue component failed static_check gate"}]
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


_NON_ID_CHARS_RE = re.compile(r"[^A-Za-z0-9$]+")
_SEPARATOR_RE = re.compile(r"[_\s-]+")


def _safe_dto_field_name(raw_name: str) -> str:
    """Convert potentially nested/path-like names to a flat Java field name.

    Examples:
    - searchParams.endYn -> endYn
    - rowItems[].owner_nm -> ownerNm
    """
    text = (raw_name or "").strip()
    if not text:
        return ""
    # DTOs must be flat; keep only the terminal segment of a path-like key.
    leaf = text.replace("[]", "").split(".")[-1].strip()
    if not leaf:
        return ""
    # If separators exist, convert to lowerCamelCase. Otherwise preserve camelCase.
    normalized = _NON_ID_CHARS_RE.sub(" ", leaf).strip()
    if not normalized:
        return ""
    if _SEPARATOR_RE.search(normalized):
        parts = [p for p in _SEPARATOR_RE.split(normalized) if p]
        if not parts:
            return ""
        base = parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:])
    else:
        base = normalized[:1].lower() + normalized[1:]
    # Java identifier guard.
    base = re.sub(r"[^A-Za-z0-9_$]", "", base)
    if not base:
        return ""
    if not re.match(r"[A-Za-z_$]", base[0]):
        base = f"field{base[:1].upper()}{base[1:]}"
    return base


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
                "statement_id": naming.statement_id(op, screen_code),
                "dao_method": naming.dao_method(op, screen_code),
                "param_type": req_dto,
                "return_type": ret,
                "mybatis_tag": naming.mybatis_tag(op),
            })

        def _fields():
            out = []
            seen: set[str] = set()
            for f in contract.get("fields", []):
                name = _safe_dto_field_name(f.get("vue_field", ""))
                if not name or name in seen:
                    continue
                seen.add(name)
                out.append({
                    "name": name,
                    "java_type": naming.java_type(f.get("type", "string")),
                    "db_column": f.get("db_column", ""),
                })
            return out

        dtos = [
            {"name": req_dto, "kind": "request", "fields": _fields()},
            {"name": res_dto, "kind": "response", "fields": _fields()},
        ]
        contract["operations"] = operations
        contract["dtos"] = dtos

        # Subordinate planner to the contract: replace planner's free-form DTO
        # files with exactly the contract's ReqDto/ResDto (non-DTO files kept).
        reconciled_plan, dropped = _reconcile_plan_dtos(plan, req_dto, res_dto, screen_code)
        # Deterministic target paths: derive every file's location from the screen
        # code (hsc.tomms.web.{module}.{screen}, Mapper under mybatis/mappers/)
        # instead of trusting the planner LLM. Unknown types keep their planned path.
        # Layer is also enforced by file_type — a mislabeled mapper in frontend/
        # would never be found by MyBatis at runtime.
        for f in reconciled_plan["files"]:
            canonical = naming.file_path(f["file_type"], screen_code)
            if canonical:
                f["file_path"] = canonical
                f["layer"] = ("frontend" if f["file_type"] in _FRONTEND_FILE_TYPES
                              else "backend")
    except Exception as e:
        return {"events": [{"type": "log", "line": f"[CONTRACT] derive failed: {e}"}]}

    log = (f"[CONTRACT] derived {len(operations)} ops, {len(dtos)} dtos"
           + (f"; reconciled plan DTOs (dropped {dropped})" if dropped else ""))
    return {"contract": contract, "plan": reconciled_plan,
            "events": [{"type": "log", "line": log}]}


def _reconcile_plan_dtos(plan: dict, req_dto: str, res_dto: str,
                         screen_code: str) -> tuple[dict, int]:
    """Force the plan's DTO files to match the contract's ReqDto/ResDto exactly.

    DTO file paths are derived deterministically (naming.file_path) — the old
    'preserve planner dir, else com.example.cpms' fallback is gone. Non-DTO files
    are kept as-is (their paths are normalized later in derive_contract). Returns
    (new_plan, dropped_count)."""
    files = plan.get("files", [])
    kept = [f for f in files if f["file_type"] not in ("dto_request", "dto_response")]
    dropped = len(files) - len(kept)

    new_files = list(kept)
    new_files.append({"file_path": naming.file_path("dto_request", screen_code),
                      "file_type": "dto_request", "layer": "backend",
                      "class_name": req_dto, "description": "Request DTO (contract)",
                      "wave": wave_for_file_type("dto_request")})
    new_files.append({"file_path": naming.file_path("dto_response", screen_code),
                      "file_type": "dto_response", "layer": "backend",
                      "class_name": res_dto, "description": "Response DTO (contract)",
                      "wave": wave_for_file_type("dto_response")})
    new_plan = dict(plan)
    new_plan["files"] = new_files
    # dropped counts original DTO files removed (the 2 we re-added are not "dropped")
    return new_plan, dropped
