"""Frontend validation: per-file static_check (FE rules) + DataTable :columns check.

Deterministic gate over generated frontend files. Per-file rules reuse
tools.static_check_impl (scrollHeight="flex", <script> without setup, alert/confirm).
Plus the DataTable wrapper invariant: columns are passed via the :columns prop, not
<Column> child elements (which the wrapper silently ignores).
"""

from __future__ import annotations

import re

from app.llm.graph import tools

_COLUMN_CHILD = re.compile(r"<Column[\s>]")
_COLUMNS_PROP = re.compile(r":columns\s*=")


def validate_frontend(files: dict, contract: dict) -> list[dict]:
    issues: list[dict] = []
    for gf in files.values():
        if gf.get("layer") != "frontend":
            continue
        issues += tools.static_check_impl(gf["file_path"], gf["content"],
                                          gf["file_type"], "frontend")
        if gf.get("file_type") in ("vue_datatable", "vue_page"):
            content = gf["content"]
            if _COLUMN_CHILD.search(content) and not _COLUMNS_PROP.search(content):
                issues.append({
                    "file_path": gf["file_path"], "severity": "error",
                    "issue": "DataTable must use the :columns prop, not <Column> children "
                             "(the DataTable2 wrapper ignores <Column> children)."})
    return issues
