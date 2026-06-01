"""Deterministic CPMS identifier derivation (namebook rules, bare statement ids).

Single source of truth for statement ids, DAO method names, DTO class names and
Java types. Because identifiers are derived by code (not the LLM), every file that
references the same contract uses identical names — mismatches become impossible.
"""

from __future__ import annotations

# op → (statement_id / dao_method, mybatis tag). Bare per namebook (one mapper/screen).
_OP_TABLE: dict[str, tuple[str, str]] = {
    "selectList": ("selectList", "select"),
    "selectOne": ("select", "select"),
    "count": ("selectCount", "select"),
    "insert": ("insert", "insert"),
    "update": ("update", "update"),
    "delete": ("delete", "delete"),
}

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


def statement_id(op: str) -> str:
    entry = _OP_TABLE.get(op)
    return entry[0] if entry else op


def dao_method(op: str) -> str:
    return statement_id(op)


def mybatis_tag(op: str) -> str:
    entry = _OP_TABLE.get(op)
    return entry[1] if entry else "select"


def dto_class(screen_code: str, kind: str) -> str:
    suffix = "ReqDto" if kind == "request" else "ResDto"
    return f"{screen_code}{suffix}"


def java_type(contract_type: str) -> str:
    return _TYPE_MAP.get((contract_type or "").lower(), "String")


def ops_for_screen_type(screen_type: str) -> list[str]:
    return list(_SCREEN_OPS.get(screen_type, _SCREEN_OPS["list"]))
