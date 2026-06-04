"""Deterministic CPMS identifier derivation (namebook rules, bare statement ids).

Single source of truth for statement ids, DAO method names, DTO class names and
Java types. Because identifiers are derived by code (not the LLM), every file that
references the same contract uses identical names — mismatches become impossible.
"""

from __future__ import annotations

import re

# op → (prefix, suffix, mybatis tag). Suffixed naming: {prefix}{ScreenCode}{suffix}.
# Domain-suffixed ids make statement ids unique per screen (better traceability +
# lets static_check distinguish a legit wrapper call from a bare base-class misuse).
_OP_TABLE: dict[str, tuple[str, str, str]] = {
    "selectList": ("select", "List", "select"),
    "selectOne": ("select", "", "select"),
    "count": ("select", "Count", "select"),
    "insert": ("insert", "", "insert"),
    "update": ("update", "", "update"),
    "delete": ("delete", "", "delete"),
}

# Bare base-class method names that must NOT be called directly on a DAO variable
# (they are AbstractSqlSessionDaoSupport internals). Used by static_check.
BASE_DAO_METHODS = ("selectList", "selectOne", "select", "insert", "update", "delete",
                    "batchUpdateReturnSumAffectedRows")

_SCREEN_OPS: dict[str, list[str]] = {
    "list": ["selectList", "count"],
    "list-detail": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "edit": ["selectOne", "insert", "update", "delete"],
    "tab-detail": ["selectList", "count", "selectOne", "insert", "update", "delete"],
}

_TYPE_MAP: dict[str, str] = {
    "string": "String",
    "text": "String",
    "number": "Integer",
    "int": "Integer",
    "long": "Long",
    "decimal": "Double",
    "boolean": "Boolean",
    "date": "String",
    "datetime": "String",
}


def class_name_from_path(file_path: str) -> str:
    """'.../a/FooDaoImpl.java' -> 'FooDaoImpl' (single source for this extraction)."""
    return file_path.split("/")[-1].replace(".java", "")


def statement_id(op: str, screen_code: str) -> str:
    """Suffixed id: {prefix}{ScreenCode}{suffix} (e.g. selectCpmsEduRsltLstList)."""
    entry = _OP_TABLE.get(op)
    if not entry:
        return op
    prefix, suffix, _ = entry
    return f"{prefix}{screen_code}{suffix}"


def dao_method(op: str, screen_code: str) -> str:
    return statement_id(op, screen_code)


def mybatis_tag(op: str) -> str:
    entry = _OP_TABLE.get(op)
    return entry[2] if entry else "select"


def dto_class(screen_code: str, kind: str) -> str:
    suffix = "ReqDto" if kind == "request" else "ResDto"
    return f"{screen_code}{suffix}"


def java_type(contract_type: str) -> str:
    return _TYPE_MAP.get((contract_type or "").lower(), "String")


def ops_for_screen_type(screen_type: str) -> list[str]:
    return list(_SCREEN_OPS.get(screen_type, _SCREEN_OPS["list"]))


# ---------------------------------------------------------------------------
# Target-path derivation
#
# Path TEMPLATES live in the guide (CODEGEN_RULES.md `codegen-paths` block) and are
# read at runtime — NOT hardcoded here — so swapping/editing the guide changes the
# output paths without a code change. This module only applies the templates
# deterministically (substitutes the screen-derived segments).
# ---------------------------------------------------------------------------

_PASCAL_RE = re.compile(r"[A-Z][a-z0-9]*")


def screen_segments(screen_code: str) -> tuple[str, str]:
    """(module, screen) lowercased package segments from a PascalCase screen code.

    'CpmsEduRsltLst' -> ('cpms', 'edursltlst'). The first token is the LV1 module;
    the remainder forms the screen segment. A single-token (or empty) code mirrors
    module to screen so the package never gets a dangling empty segment.
    """
    toks = _PASCAL_RE.findall(screen_code or "")
    if not toks:
        seg = (screen_code or "screen").lower()
        return seg, seg
    module = toks[0].lower()
    screen = "".join(toks[1:]).lower() or module
    return module, screen


def file_path(file_type: str, screen_code: str) -> str | None:
    """Target path for a generated file, driven by the guide's path templates
    (CODEGEN_RULES.md `codegen-paths`) — not hardcoded. Substitutes `{module}` /
    `{screen}` (derived from the screen code) and `{Screen}` (the screen code).
    Returns None when the guide has no template for this file_type (the caller
    then keeps the planner's path).
    """
    from app.llm.graph import guides
    template = guides.load_path_templates().get(file_type)
    if not template:
        return None
    module, screen = screen_segments(screen_code)
    return (template.replace("{module}", module)
                    .replace("{screen}", screen)
                    .replace("{Screen}", screen_code))


def package_from_java_path(file_path: str) -> str | None:
    """Java package implied by a source path (between 'src/main/java/' and the file).

    'src/main/java/hsc/tomms/web/cpms/edursltlst/dao/XxxDaoImpl.java'
        -> 'hsc.tomms.web.cpms.edursltlst.dao'. None for non-Java paths.
    """
    p = (file_path or "").replace("\\", "/")
    marker = "src/main/java/"
    if not p.endswith(".java") or marker not in p:
        return None
    after = p.split(marker, 1)[1]
    parts = after.split("/")[:-1]  # drop the filename
    return ".".join(parts) if parts else None
