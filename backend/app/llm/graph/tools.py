"""Code-generation tools: deterministic core functions + @tool wrappers.

Core functions (_impl) are called directly by graph nodes (no LLM).
@tool wrappers (Task 6) expose the same logic to the Reviewer's tool-calling loop.
"""

from __future__ import annotations

import re

# ── static_check rules (layer-scoped) ──
_BACKEND_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"import\s+java\.util\.UUID"),
     "java.util.UUID import found — use String for ID fields"),
    (re.compile(r"@Service\s*\(\s*\"[^\"]+\"\s*\)"),
     "@Service with bean name — use bare @Service"),
    (re.compile(r"UUID\s*\.\s*randomUUID\s*\("),
     "UUID.randomUUID() found — IDs come from DB sequence or DTO"),
    (re.compile(r"LoggerFactory\.getLogger\s*\("),
     "LoggerFactory.getLogger() — use @Slf4j (lombok) instead"),
]

_FRONTEND_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"scrollHeight\s*=\s*[\"']flex[\"']"),
     'scrollHeight="flex" — use scrollHeight="540px" + virtualScrollerOptions'),
    (re.compile(r"<script(?!\s+setup)[\s>]"),
     '<script> without setup — use <script setup lang="ts">'),
    (re.compile(r"\balert\s*\("), "alert() found — use Toast component"),
    (re.compile(r"\bconfirm\s*\("), "confirm() found — use ConfirmDialog"),
]


def static_check_impl(file_path: str, content: str, file_type: str, layer: str) -> list[dict]:
    """Single-file regex validation, scoped to the file's layer."""
    rules = _BACKEND_RULES if layer == "backend" else _FRONTEND_RULES
    issues: list[dict] = []
    for pattern, msg in rules:
        if pattern.search(content):
            issues.append({"file_path": file_path, "issue": msg})
    return issues


def validate_sql_impl(sql: str) -> list[dict]:
    """Validate db_init_sql: each non-empty statement line group must end with ';'."""
    issues: list[dict] = []
    # crude: count CREATE/INSERT/ALTER statements vs semicolons
    statements = re.findall(r"\b(CREATE|INSERT|ALTER|UPDATE|DELETE)\b", sql, re.IGNORECASE)
    semicolons = sql.count(";")
    if statements and semicolons < len(statements):
        issues.append({
            "file_path": "db_init.sql",
            "issue": f"SQL missing semicolon: {len(statements)} statement(s) but {semicolons} ';'",
        })
    return issues


# ── DTO field parsing (generated files only) ──
_GETTER_RE = re.compile(r"(\w+)\.get([A-Z]\w*)\s*\(")


def _dto_field_names(content: str) -> list[dict]:
    out = []
    for m in re.finditer(r"private\s+(\S+(?:<[^>]+>)?)\s+(\w+)\s*(?:=[^;]+)?;", content):
        out.append({"name": m.group(2), "type": m.group(1)})
    return out


def get_dto_fields_impl(dto_name: str, files: dict) -> list[dict]:
    """Tool #4: fields of a generated DTO (name+type)."""
    for gf in files.values():
        cls = gf["file_path"].split("/")[-1].replace(".java", "")
        if cls == dto_name:
            return _dto_field_names(gf["content"])
    return []


def lookup_class_impl(class_name: str, files: dict) -> dict | None:
    """Tool #3: lookup a class in generated files only."""
    for gf in files.values():
        cls = gf["file_path"].split("/")[-1].replace(".java", "")
        if cls == class_name:
            methods = re.findall(r"public\s+\S+\s+(\w+)\s*\(", gf["content"])
            return {"class_name": class_name, "file_path": gf["file_path"],
                    "fields": _dto_field_names(gf["content"]), "methods": methods}
    return None


def cross_check_impl(files: dict, contract: dict) -> list[dict]:
    """Tool #2: cross-file consistency. getter calls must reference real DTO fields."""
    # build dto -> set(field names)
    dto_fields: dict[str, set[str]] = {}
    for gf in files.values():
        cls = gf["file_path"].split("/")[-1].replace(".java", "")
        if "Dto" in cls:
            dto_fields[cls] = {f["name"] for f in _dto_field_names(gf["content"])}

    issues: list[dict] = []
    for gf in files.values():
        if not gf["file_path"].endswith(".java") or "Dto" in gf["file_path"]:
            continue
        # map: var name -> dto type   (e.g. "CpmsEduResDto d;")
        var_types: dict[str, str] = {}
        for m in re.finditer(r"(\w+(?:Dto\w*))\s+(\w+)\s*[;=:)]", gf["content"]):
            if m.group(1) in dto_fields:
                var_types[m.group(2)] = m.group(1)
        for m in _GETTER_RE.finditer(gf["content"]):
            var, prop = m.group(1), m.group(2)
            dto = var_types.get(var)
            if not dto:
                continue
            field = prop[0].lower() + prop[1:]
            if field not in dto_fields.get(dto, set()):
                issues.append({
                    "file_path": gf["file_path"],
                    "issue": f"{gf['file_path']} calls get{prop}() but {dto} has no field '{field}'",
                })
    return issues


def list_generated_files_impl(files: dict) -> list[dict]:
    """Tool #7: current generation status summary."""
    return [{"file_path": gf["file_path"], "file_type": gf["file_type"],
             "layer": gf["layer"], "status": gf["status"]} for gf in files.values()]


# ── Responses API tool specs (gpt-5.5 tool-calling) ──
TOOL_SPECS: list[dict] = [
    {"type": "function", "name": "static_check",
     "description": "Validate a single file against CPMS regex rules. Returns issues.",
     "parameters": {"type": "object",
                    "properties": {"file_path": {"type": "string"},
                                   "content": {"type": "string"},
                                   "file_type": {"type": "string"},
                                   "layer": {"type": "string"}},
                    "required": ["file_path", "content", "file_type", "layer"]}},
    {"type": "function", "name": "cross_check",
     "description": "Cross-file consistency check against contract. Returns mismatches.",
     "parameters": {"type": "object", "properties": {}, "required": []}},
    {"type": "function", "name": "lookup_class",
     "description": "Look up a class in generated files (fields, methods).",
     "parameters": {"type": "object",
                    "properties": {"class_name": {"type": "string"}},
                    "required": ["class_name"]}},
    {"type": "function", "name": "get_dto_fields",
     "description": "Get fields (name+type) of a generated DTO.",
     "parameters": {"type": "object",
                    "properties": {"dto_name": {"type": "string"}},
                    "required": ["dto_name"]}},
    {"type": "function", "name": "lookup_guide",
     "description": "Fetch the latest standard guide sections by topic.",
     "parameters": {"type": "object",
                    "properties": {"layer": {"type": "string"},
                                   "topic": {"type": "string"}},
                    "required": ["layer", "topic"]}},
    {"type": "function", "name": "validate_sql",
     "description": "Validate db_init SQL syntax/rules.",
     "parameters": {"type": "object",
                    "properties": {"sql": {"type": "string"}},
                    "required": ["sql"]}},
    {"type": "function", "name": "list_generated_files",
     "description": "List current generated files (path/type/layer/status).",
     "parameters": {"type": "object", "properties": {}, "required": []}},
]

# apply_fix mutates the file set; it is handled directly by the reviewer loop
# (not dispatch_tool, which is read-only). Exposed only to the reviewer.
_APPLY_FIX_SPEC = {
    "type": "function", "name": "apply_fix",
    "description": "Overwrite a generated file with corrected content. "
                   "Pass the COMPLETE file content, not a diff.",
    "parameters": {"type": "object",
                   "properties": {"file_path": {"type": "string"},
                                  "content": {"type": "string"}},
                   "required": ["file_path", "content"]},
}

# The reviewer gets the read-only diagnostic tools plus the mutating apply_fix.
REVIEWER_TOOL_SPECS: list[dict] = TOOL_SPECS + [_APPLY_FIX_SPEC]


def dispatch_tool(name: str, args: dict, files: dict, contract: dict) -> object:
    """Execute a tool call by name. Used by the Reviewer ReAct loop (Plan 2)."""
    from app.llm.graph import guides
    if name == "static_check":
        return static_check_impl(args["file_path"], args["content"],
                                 args["file_type"], args["layer"])
    if name == "cross_check":
        return cross_check_impl(files, contract)
    if name == "lookup_class":
        return lookup_class_impl(args["class_name"], files)
    if name == "get_dto_fields":
        return get_dto_fields_impl(args["dto_name"], files)
    if name == "lookup_guide":
        return guides.lookup_guide(args["layer"], args["topic"])
    if name == "validate_sql":
        return validate_sql_impl(args["sql"])
    if name == "list_generated_files":
        return list_generated_files_impl(files)
    raise ValueError(f"unknown tool: {name}")
