"""Selective guide loader for code generation.

Loads BackendGuide and FrontendGuide files from pfy_prompt/,
splits them by ## headings, and returns only the sections relevant
to the file type being generated.  This keeps each LLM call within
~15-25 KB of guide context instead of the full ~400 KB.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import settings

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_BACKEND_SECTIONS: dict[str, dict[str, str]] | None = None  # filename -> {heading: content}
_FRONTEND_SECTIONS: dict[str, dict[str, str]] | None = None
_NAMING_CONTEXT: str | None = None


def _split_by_headings(text: str) -> dict[str, str]:
    """Split markdown text into sections keyed by ## heading."""
    sections: dict[str, str] = {}
    current_heading = "_preamble"
    parts: list[str] = []

    for line in text.splitlines(keepends=True):
        m = re.match(r"^##\s+(.+)", line)
        if m:
            sections[current_heading] = "".join(parts)
            current_heading = m.group(1).strip()
            parts = [line]
        else:
            parts.append(line)
    sections[current_heading] = "".join(parts)
    return sections


def _load_guide_dir(dirname: str) -> dict[str, dict[str, str]]:
    base = Path(settings.PROMPT_REFERENCE_DIR) / dirname
    result: dict[str, dict[str, str]] = {}
    if not base.exists():
        return result
    for f in sorted(base.glob("*.md")):
        result[f.name] = _split_by_headings(f.read_text(encoding="utf-8"))
    return result


def _ensure_loaded() -> None:
    global _BACKEND_SECTIONS, _FRONTEND_SECTIONS, _NAMING_CONTEXT
    if _BACKEND_SECTIONS is not None:
        return
    _BACKEND_SECTIONS = _load_guide_dir("BackendGuide")
    _FRONTEND_SECTIONS = _load_guide_dir("FrontendGuide")

    # Always-included naming context
    base = Path(settings.PROMPT_REFERENCE_DIR)
    parts = []
    for fname in ("namebook.md", "CPMS_namebook.md"):
        p = base / fname
        if p.exists():
            parts.append(f"=== {fname} ===\n{p.read_text(encoding='utf-8')}")
    _NAMING_CONTEXT = "\n\n".join(parts)


# ---------------------------------------------------------------------------
# File-type to guide mapping
# ---------------------------------------------------------------------------

# Keys match BackendGuide filenames (prefix matching)
_BACKEND_FILE_MAP: dict[str, list[tuple[str, list[str] | None]]] = {
    # (filename_prefix, section_heading_substrings or None for whole file)
    "dto_request": [("04-", None), ("05-", None)],
    "dto_response": [("04-", None), ("05-", None)],
    "service": [("04-", None), ("05-", None)],
    "service_impl": [("04-", None), ("05-", None)],
    "dao": [("04-", None), ("05-", None)],
    "dao_impl": [("04-", None), ("05-", None)],
    "mapper_xml": [("04-", None), ("05-", None)],
    "db_init_sql": [("02-", None)],
}

_FRONTEND_FILE_MAP: dict[str, list[tuple[str, list[str] | None]]] = {
    "vue_page": [("00_", None), ("02_", None)],
    "vue_search_form": [("02_", None), ("03_", None)],
    "vue_data_table": [("02_", None), ("04_", None)],
    "vue_sum_grid": [("02_", None), ("05_", None)],
    "vue_api": [("06_", None)],
    "vue_types": [("06_", None)],
    "vue_scss": [("07_", None)],
    "pinia_store": [("08_", None)],
}


def _collect_sections(
    sections_db: dict[str, dict[str, str]],
    file_map_entries: list[tuple[str, list[str] | None]],
) -> str:
    parts: list[str] = []
    for prefix, heading_filters in file_map_entries:
        for fname, sections in sections_db.items():
            if not fname.startswith(prefix):
                continue
            if heading_filters is None:
                # Include all sections of this file
                full = "\n".join(sections.values())
                parts.append(f"=== {fname} ===\n{full}")
            else:
                matched = []
                for heading, content in sections.items():
                    if any(h.lower() in heading.lower() for h in heading_filters):
                        matched.append(content)
                if matched:
                    parts.append(f"=== {fname} ===\n{''.join(matched)}")
    return "\n\n".join(parts)


def get_context_for_file_type(file_type: str) -> str:
    """Return guide context appropriate for the given file_type."""
    _ensure_loaded()
    assert _BACKEND_SECTIONS is not None
    assert _FRONTEND_SECTIONS is not None

    parts: list[str] = []

    # Backend guides
    if file_type in _BACKEND_FILE_MAP:
        text = _collect_sections(_BACKEND_SECTIONS, _BACKEND_FILE_MAP[file_type])
        if text:
            parts.append(text)

    # Frontend guides
    if file_type in _FRONTEND_FILE_MAP:
        text = _collect_sections(_FRONTEND_SECTIONS, _FRONTEND_FILE_MAP[file_type])
        if text:
            parts.append(text)

    return "\n\n".join(parts)


def get_naming_context() -> str:
    """Return the always-included naming convention docs."""
    _ensure_loaded()
    return _NAMING_CONTEXT or ""


def get_all_backend_guide() -> str:
    """Return full BackendGuide text (for planning step)."""
    _ensure_loaded()
    assert _BACKEND_SECTIONS is not None
    parts = []
    for fname in sorted(_BACKEND_SECTIONS):
        full = "\n".join(_BACKEND_SECTIONS[fname].values())
        parts.append(f"=== {fname} ===\n{full}")
    return "\n\n".join(parts)


def get_all_frontend_guide() -> str:
    """Return full FrontendGuide text (for planning step)."""
    _ensure_loaded()
    assert _FRONTEND_SECTIONS is not None
    parts = []
    for fname in sorted(_FRONTEND_SECTIONS):
        full = "\n".join(_FRONTEND_SECTIONS[fname].values())
        parts.append(f"=== {fname} ===\n{full}")
    return "\n\n".join(parts)
