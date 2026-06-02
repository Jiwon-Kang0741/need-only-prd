"""Guide markdown loader with mtime-based freshness.

Reads BackendGuide/FrontendGuide md from PROMPT_REFERENCE_DIR. Re-reads a file
whenever its mtime changes, so editing a guide is reflected on the next codegen
run without a server restart.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.config import settings

# path -> (mtime, text). Per-file cache keyed by absolute path.
_FILE_CACHE: dict[str, tuple[float, str]] = {}
# (dir, prefix) -> (dir_mtime, [Path]). Avoids re-globbing the guide dir on every
# generate_file call in a wave fan-out; invalidated when the directory changes.
_GLOB_CACHE: dict[tuple[str, str], tuple[float, list]] = {}


def _reset_cache_for_test() -> None:
    _FILE_CACHE.clear()
    _GLOB_CACHE.clear()


def _read_fresh(path: Path) -> str:
    """Return file text, re-reading only if mtime changed since last read."""
    key = str(path)
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        _FILE_CACHE.pop(key, None)
        return ""
    cached = _FILE_CACHE.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]
    text = path.read_text(encoding="utf-8")
    _FILE_CACHE[key] = (mtime, text)
    return text


def _split_by_headings(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "_preamble"
    parts: list[str] = []
    for line in text.splitlines(keepends=True):
        m = re.match(r"^#{2,3}\s+(.+)", line)
        if m:
            sections[current] = "".join(parts)
            current = m.group(1).strip()
            parts = [line]
        else:
            parts.append(line)
    sections[current] = "".join(parts)
    return sections


# file_type -> [(guide filename prefix, layer)]; 개선3: 넉넉히 주입(매핑 누락 위험↓)
_FILE_TYPE_GUIDES: dict[str, list[tuple[str, str]]] = {
    "dto_request":   [("표준", "backend")],
    "dto_response":  [("표준", "backend")],
    "dao":           [("표준", "backend")],
    "dao_impl":      [("표준", "backend")],
    "service":       [("표준", "backend")],
    "service_impl":  [("표준", "backend")],
    "mapper_xml":    [("표준", "backend")],
    "db_init_sql":   [("표준", "backend"), ("02-", "backend")],
    "vue_page":      [("00_", "frontend"), ("02_", "frontend"), ("03_", "frontend"),
                      ("04_", "frontend"), ("07_", "frontend")],
    "vue_types":     [("06_", "frontend")],
}

_LAYER_DIR = {"backend": "BackendGuide", "frontend": "FrontendGuide"}


def _guide_files(layer: str, prefix: str) -> list[Path]:
    base = Path(settings.PROMPT_REFERENCE_DIR) / _LAYER_DIR[layer]
    try:
        dir_mtime = base.stat().st_mtime
    except FileNotFoundError:
        return []
    key = (str(base), prefix)
    cached = _GLOB_CACHE.get(key)
    if cached is not None and cached[0] == dir_mtime:
        return cached[1]
    files = [f for f in sorted(base.glob("*.md")) if f.name.startswith(prefix)]
    _GLOB_CACHE[key] = (dir_mtime, files)
    return files


def load_guide_for_file_type(file_type: str) -> str:
    """Concatenate all guide sections relevant to a file type (fresh)."""
    entries = _FILE_TYPE_GUIDES.get(file_type, [])
    parts: list[str] = []
    for prefix, layer in entries:
        for f in _guide_files(layer, prefix):
            parts.append(f"=== {f.name} ===\n{_read_fresh(f)}")
    return "\n\n".join(parts)


def lookup_guide(layer: str, topic: str) -> str:
    """Return guide sections whose heading contains `topic` (fresh). Tool #5."""
    base = Path(settings.PROMPT_REFERENCE_DIR) / _LAYER_DIR.get(layer, "BackendGuide")
    if not base.exists():
        return ""
    out: list[str] = []
    for f in sorted(base.glob("*.md")):
        sections = _split_by_headings(_read_fresh(f))
        for heading, body in sections.items():
            if topic.lower() in heading.lower():
                out.append(body)
    return "\n".join(out)


def load_table_info() -> str:
    """Load 테이블정보.md (real DB columns/types) fresh."""
    base = Path(settings.PROMPT_REFERENCE_DIR)
    for candidate in (base / "BackendGuide" / "테이블정보.md", base / "테이블정보.md"):
        if candidate.exists():
            return _read_fresh(candidate)
    return ""
