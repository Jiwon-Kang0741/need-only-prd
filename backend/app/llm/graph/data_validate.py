"""Data (db/init.sql) validation — DataGuide §12/§16.1/§1.2.

Deterministic gate over the assembled SQL. Reuses tools.validate_sql_impl for the
statement-terminator check, then adds: pgm_url must NOT have a leading slash
(§16.1 — value is 'pages/...'), and MERGE is forbidden (§1.2 — use ON CONFLICT).
"""

from __future__ import annotations

import re

from app.llm.graph import tools

_LEADING_SLASH_PGM = re.compile(r"""['"]/pages/""")
_MERGE = re.compile(r"\bMERGE\b", re.IGNORECASE)


def validate_data(sql: str, contract: dict) -> list[dict]:
    issues: list[dict] = list(tools.validate_sql_impl(sql))
    if _LEADING_SLASH_PGM.search(sql):
        issues.append({"file_path": "db/init.sql", "severity": "error",
                       "issue": "pgm_url must not have a leading slash (§16.1: store 'pages/...')"})
    if _MERGE.search(sql):
        issues.append({"file_path": "db/init.sql", "severity": "error",
                       "issue": "MERGE is forbidden — use INSERT ... ON CONFLICT (§1.2)"})
    return issues
