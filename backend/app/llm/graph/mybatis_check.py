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


def check_binding(files: dict) -> list[dict]:
    """Detect namespace mismatch, missing statements, unused statements."""
    pairs, issues = match_pairs(files)
    issues = list(issues)  # copy unpaired issues

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])

        # 1. namespace must equal DaoImpl FQCN
        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            issues.append({
                "file_path": mapper_gf["file_path"],
                "issue": (f"Mapper namespace '{mapper['namespace']}' != DaoImpl FQCN "
                          f"'{dao['expected_namespace']}'"),
                "severity": "error",
            })

        # 2. DAO calls an id the Mapper does not define (runtime binding failure)
        for sid in sorted(dao["statement_ids"] - mapper["ids"]):
            issues.append({
                "file_path": mapper_gf["file_path"],
                "issue": (f"DAO calls statement '{sid}' but Mapper has no matching "
                          f"<statement id=\"{sid}\">"),
                "severity": "error",
            })

        # 3. Mapper defines an id no DAO calls (warning only)
        for sid in sorted(mapper["ids"] - dao["statement_ids"]):
            issues.append({
                "file_path": mapper_gf["file_path"],
                "issue": f"Mapper statement '{sid}' is not called by any DAO method",
                "severity": "warning",
            })
    return issues


_EDIT_DISTANCE_THRESHOLD = 0.3  # normalized; ≤ this is "obvious variant"


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _normalized_distance(a: str, b: str) -> float:
    m = max(len(a), len(b))
    return _edit_distance(a, b) / m if m else 0.0


def autofix_binding(files: dict) -> tuple[dict, list[str]]:
    """Apply deterministic fixes for obvious mismatches. DAO is source of truth.

    Returns (fixed_files_copy, log_lines). Ambiguous mismatches are left untouched
    for the reviewer.
    """
    fixed = {p: dict(gf) for p, gf in files.items()}
    logs: list[str] = []
    pairs, _ = match_pairs(fixed)

    for dao_gf, mapper_gf in pairs:
        dao = parse_dao(dao_gf["content"])
        mapper = parse_mapper(mapper_gf["content"])
        content = mapper_gf["content"]

        # (a) namespace → DaoImpl FQCN (always obvious)
        if dao["expected_namespace"] and mapper["namespace"] != dao["expected_namespace"]:
            content = re.sub(
                r'(<mapper\b[^>]*\bnamespace\s*=\s*")[^"]+(")',
                lambda m: m.group(1) + dao["expected_namespace"] + m.group(2),
                content, count=1,
            )
            logs.append(f"{mapper_gf['file_path']}: namespace → {dao['expected_namespace']}")

        # (b) greedy 1:1 close-variant id rename (mapper id → dao id)
        missing = sorted(dao["statement_ids"] - mapper["ids"])   # dao wants, mapper lacks
        unused = sorted(mapper["ids"] - dao["statement_ids"])    # mapper has, dao ignores
        used_have: set[str] = set()
        for want in missing:
            best, best_d = None, 1.0
            for have in unused:
                if have in used_have:
                    continue
                d = _normalized_distance(want, have)
                if d < best_d:
                    best, best_d = have, d
            if best is not None and best_d <= _EDIT_DISTANCE_THRESHOLD:
                used_have.add(best)
                content = re.sub(
                    rf'(\bid\s*=\s*"){re.escape(best)}(")',
                    lambda m, w=want: m.group(1) + w + m.group(2),
                    content, count=1,
                )
                logs.append(f"{mapper_gf['file_path']}: statement id '{best}' → '{want}'")

        fixed[mapper_gf["file_path"]] = {**mapper_gf, "content": content}

    return fixed, logs
