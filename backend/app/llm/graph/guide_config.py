"""Read-only parsers over the FIXED guide md files.

The guides (pfy_prompt/{BackendGuide,FrontendGuide,DataGuide}) are immutable
external input — never edited. These parsers read the machine-readable parts
(Markdown tables, ordered lists) so codegen rules come from the guide as-is, with
no hardcoded rule values and no guide annotation. Each loader re-reads the file,
so a guide swap/edit reflects on the next call. `_parse_*(text)` helpers are pure
(unit-testable); `load_*()` read the real guide then parse.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import settings


def _read(relpath: str) -> str:
    p = Path(settings.PROMPT_REFERENCE_DIR) / relpath
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _normalize_label(label: str) -> str:
    """'DAO Impl' -> 'dao_impl' (lower, trim, spaces->underscore)."""
    return re.sub(r"\s+", "_", label.strip().lower())


_TABLE_ROW = re.compile(r"^\|(?P<c1>[^|\n]+)\|(?P<c2>[^|\n]+)\|\s*$", re.MULTILINE)
_BACKTICK = re.compile(r"`([^`]+)`")
_SEP_CHARS = set("-: ")


def _parse_backend_path_templates(text: str) -> dict[str, str]:
    """Parse BackendGuide §11.4 'file path rules' Markdown table -> {file_type: tpl}."""
    sec = re.search(r"###\s*11\.4.*?(?=\n###\s|\Z)", text, re.DOTALL)
    if not sec:
        return {}
    out: dict[str, str] = {}
    for m in _TABLE_ROW.finditer(sec.group(0)):
        label, val = m.group("c1").strip(), m.group("c2").strip()
        if not label or label == "파일 유형" or set(label) <= _SEP_CHARS:
            continue
        bt = _BACKTICK.search(val)
        if bt:
            out[_normalize_label(label)] = bt.group(1).strip()
    return out


def load_backend_path_templates() -> dict[str, str]:
    return _parse_backend_path_templates(_read("BackendGuide/표준.md"))


# ---------------------------------------------------------------------------
# Seed parsers
# ---------------------------------------------------------------------------

# Matches table rows with cmn_* table names; backticks are optional
_NK_ROW = re.compile(
    r"^\|\s*`?(cmn_\w+)`?\s*\|\s*`?([^`|\n]+)`?\s*\|",
    re.MULTILINE,
)
_ORDER_ROW = re.compile(r"^\s*\d+\.\s*`?(cmn_\w+)`?", re.MULTILINE)


def _parse_seed_natural_keys(text: str) -> dict[str, list[str]]:
    """DataGuide §5 'Natural Key' table -> {table: [key columns]}."""
    sec = re.search(
        r"^#+\s+\d+\.\s*Natural\s*Key.*?(?=^#+\s+\d+\.|\Z)",
        text,
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    scope = sec.group(0) if sec else text
    out: dict[str, list[str]] = {}
    for m in _NK_ROW.finditer(scope):
        out[m.group(1)] = re.findall(r"[a-z_]+", m.group(2))
    return out


def _parse_seed_order(text: str) -> list[str]:
    """DataGuide §3/§14 seed generation order (ordered list of cmn_* tables)."""
    sec = re.search(
        r"^#+\s+\d+\.\s*생성\s*순서.*?(?=^#+\s+\d+\.|\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    scope = sec.group(0) if sec else text
    return [m.group(1) for m in _ORDER_ROW.finditer(scope)]


def load_seed_natural_keys() -> dict[str, list[str]]:
    return _parse_seed_natural_keys(_read("DataGuide/01.seed_standard.md"))


def load_seed_order() -> list[str]:
    return _parse_seed_order(_read("DataGuide/01.seed_standard.md"))
