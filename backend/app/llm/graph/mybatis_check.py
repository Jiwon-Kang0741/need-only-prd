"""Deterministic MyBatis binding verification (no LLM).

Parses DAO (.java) and Mapper (.xml) to cross-check that every DAO
`super.xxx("id")` call resolves to a Mapper <statement id="id"> and that the
Mapper namespace equals the DaoImpl FQCN. The DAO call string is the source of
truth; obvious 1:1 mismatches are auto-fixed, ambiguous ones are reported.
"""

from __future__ import annotations

import re

# super.{method}("statementId" ...)
_SUPER_CALL_RE = re.compile(
    r'super\s*\.\s*(?:select|selectOne|selectList|insert|update|delete|'
    r'batchUpdate\w*)\s*\(\s*"([A-Za-z0-9_]+)"'
)
_PACKAGE_RE = re.compile(r'\bpackage\s+([a-zA-Z0-9_.]+)\s*;')
_DAO_CLASS_RE = re.compile(r'\bclass\s+(\w*DaoImpl)\b')

_MAPPER_NS_RE = re.compile(r'<mapper\b[^>]*\bnamespace\s*=\s*"([^"]+)"')
_MAPPER_STMT_RE = re.compile(
    r'<(?:select|insert|update|delete)\b[^>]*\bid\s*=\s*"([^"]+)"'
)


def parse_dao(content: str) -> dict:
    """Return {statement_ids: set[str], expected_namespace: str|None}."""
    ids = set(_SUPER_CALL_RE.findall(content))
    pkg_m = _PACKAGE_RE.search(content)
    cls_m = _DAO_CLASS_RE.search(content)
    ns = f"{pkg_m.group(1)}.{cls_m.group(1)}" if pkg_m and cls_m else None
    return {"statement_ids": ids, "expected_namespace": ns}


def parse_mapper(content: str) -> dict:
    """Return {ids: set[str], namespace: str|None}."""
    ns_m = _MAPPER_NS_RE.search(content)
    ids = set(_MAPPER_STMT_RE.findall(content))
    return {"ids": ids, "namespace": ns_m.group(1) if ns_m else None}


def _basename(file_path: str, suffix: str) -> str | None:
    """'.../CpmsEduRsltLstDaoImpl.java' + 'DaoImpl' -> 'CpmsEduRsltLst'."""
    fname = file_path.replace("\\", "/").split("/")[-1]
    stem = fname.rsplit(".", 1)[0]  # drop extension
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return None


def match_pairs(files: dict) -> tuple[list[tuple[dict, dict]], list[dict]]:
    """Pair DaoImpl ↔ Mapper by name rule. Returns (pairs, unpaired_issues)."""
    daos: dict[str, dict] = {}
    mappers: dict[str, dict] = {}
    for gf in files.values():
        fp = gf["file_path"]
        if fp.endswith("DaoImpl.java"):
            base = _basename(fp, "DaoImpl")
            if base:
                daos[base] = gf
        elif fp.endswith("Mapper.xml"):
            base = _basename(fp, "Mapper")
            if base:
                mappers[base] = gf

    pairs: list[tuple[dict, dict]] = []
    unpaired: list[dict] = []
    for base, dao_gf in daos.items():
        if base in mappers:
            pairs.append((dao_gf, mappers[base]))
        else:
            unpaired.append({"file_path": dao_gf["file_path"],
                             "issue": f"{base}DaoImpl has no matching Mapper xml",
                             "severity": "error"})
    for base, mapper_gf in mappers.items():
        if base not in daos:
            unpaired.append({"file_path": mapper_gf["file_path"],
                             "issue": f"{base}Mapper xml has no matching DaoImpl",
                             "severity": "warning"})
    return pairs, unpaired
