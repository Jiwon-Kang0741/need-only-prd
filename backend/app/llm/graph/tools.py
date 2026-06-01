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
