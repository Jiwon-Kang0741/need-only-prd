"""Backend validation: per-file static_check (§11.5/§11.6) + cross-file binding checks.

Deterministic gate over the generated backend file set. Per-file rules reuse
tools.static_check_impl. Cross-file checks enforce the bindings contract:
Mapper namespace == bindings.namespace; every statement id appears as a Mapper
<...id=> AND as a DAO method (these are the §11.5 cross-file invariants).
"""

from __future__ import annotations

import re

from app.llm.graph import tools


def _find(files: dict, file_type: str) -> dict | None:
    for gf in files.values():
        if gf.get("file_type") == file_type:
            return gf
    return None


def validate_backend(files: dict, contract: dict) -> list[dict]:
    issues: list[dict] = []
    # 1) per-file static checks (backend layer only)
    for gf in files.values():
        if gf.get("layer") != "backend":
            continue
        issues += tools.static_check_impl(gf["file_path"], gf["content"],
                                          gf["file_type"], "backend")

    b = contract.get("bindings", {})
    stmt_ids = b.get("statement_ids", [])
    mapper = _find(files, "mapper_xml")
    dao = _find(files, "dao_impl")

    # 2) Mapper namespace must match bindings.namespace
    if mapper is not None and b.get("namespace"):
        m = re.search(r'namespace\s*=\s*"([^"]+)"', mapper["content"])
        if m and m.group(1) != b["namespace"]:
            issues.append({"file_path": mapper["file_path"], "severity": "error",
                           "issue": f"Mapper namespace '{m.group(1)}' != bindings namespace "
                                    f"'{b['namespace']}'"})

    # 3) each statement id must appear as a Mapper <...id="sid"> and a DAO method sid(
    for sid in stmt_ids:
        if mapper is not None and not re.search(rf'id\s*=\s*"{re.escape(sid)}"', mapper["content"]):
            issues.append({"file_path": mapper["file_path"], "severity": "error",
                           "issue": f"statement id '{sid}' missing in mapper XML"})
        if dao is not None and not re.search(rf'\b{re.escape(sid)}\s*\(', dao["content"]):
            issues.append({"file_path": dao["file_path"], "severity": "error",
                           "issue": f"statement id '{sid}' has no matching dao method"})
    return issues
