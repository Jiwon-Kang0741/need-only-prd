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
