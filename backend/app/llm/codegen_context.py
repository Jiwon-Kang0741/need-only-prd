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
    """Split markdown text into sections keyed by ## or ### heading.

    Splits on both ## and ### so that subsections like '### 4.3 Service 표준'
    under '## 4. 백엔드 표준' are individually addressable by heading filters.
    """
    sections: dict[str, str] = {}
    current_heading = "_preamble"
    parts: list[str] = []

    for line in text.splitlines(keepends=True):
        m = re.match(r"^#{2,3}\s+(.+)", line)
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


def invalidate_cache() -> None:
    """Force re-read of guide files on next access."""
    global _BACKEND_SECTIONS, _FRONTEND_SECTIONS, _NAMING_CONTEXT
    _BACKEND_SECTIONS = None
    _FRONTEND_SECTIONS = None
    _NAMING_CONTEXT = None


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

# Keys match BackendGuide filenames (prefix matching).
# 표준.md is the single consolidated guide; match its prefix "표준" for all types.
_BACKEND_FILE_MAP: dict[str, list[tuple[str, list[str] | None]]] = {
    "dto_request": [("표준", ["DTO 표준", "DTO", "명명 규칙", "패키지 구조"]), ("04-", None), ("05-", None)],
    "dto_response": [("표준", ["DTO 표준", "DTO", "명명 규칙", "패키지 구조"]), ("04-", None), ("05-", None)],
    "service": [("표준", ["Service 표준", "Service", "명명 규칙", "패키지 구조", "예외 처리", "GridStatus"]), ("04-", None), ("05-", None)],
    "service_impl": [("표준", ["Service 표준", "Service", "명명 규칙", "패키지 구조", "예외 처리", "GridStatus"]), ("04-", None), ("05-", None)],
    "dao": [("표준", ["DAO 표준", "DAO", "명명 규칙", "패키지 구조"]), ("04-", None), ("05-", None)],
    "dao_impl": [("표준", ["DAO 표준", "DAO", "명명 규칙", "패키지 구조"]), ("04-", None), ("05-", None)],
    "mapper_xml": [("표준", ["MyBatis", "Mapper", "DAO 표준", "DAO", "명명 규칙", "DB 컬럼"]), ("04-", None), ("05-", None)],
    "db_init_sql": [("표준", ["프로젝트 구조", "DB"]), ("02-", None)],
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


# ---------------------------------------------------------------------------
# pom.xml dependency extraction
# ---------------------------------------------------------------------------

_POM_DEPENDENCIES: str | None = None
_ALLOWED_PREFIXES: set[str] | None = None

# groupId → actual Java package prefix override.
# Most libraries: groupId == package prefix, but some differ.
_GROUPID_TO_PACKAGES: dict[str, list[str]] = {
    "org.projectlombok": ["lombok"],
    "hone": [],           # legacy — blocked, use aondev
    "hone-starter": [],   # legacy — blocked
    "pfy": ["com.common"],
}

# JDK built-in + project code — always allowed
# hsc.framework.online.error.HscException is a CPMS framework exception class
_ALWAYS_ALLOWED = {"java", "javax", "biz", "hsc"}


def _resolve_pom_path() -> Path:
    """Return the pom.xml that matches the active deploy mode.

    pfy mode  → C:/workspace_pfy/PFY/pfy/pom.xml  (the actual target project)
    docker mode → skeleton/backend/pom.xml          (the Docker skeleton)

    Using the correct pom.xml ensures that the LLM is shown exactly the
    libraries available at compile time, and that import validation is
    accurate — no hardcoded package lists needed.
    """
    if settings.CODEGEN_DEPLOY_MODE == "pfy":
        pfy_pom = Path(settings.PFY_BACKEND_DIR) / "pom.xml"
        if pfy_pom.exists():
            return pfy_pom
    return Path(settings.PROMPT_REFERENCE_DIR).parent / "skeleton" / "backend" / "pom.xml"


def _parse_pom_xml() -> tuple[list[str], set[str]]:
    """Parse pom.xml once, return (dependency_lines, groupId_set)."""
    import xml.etree.ElementTree as ET

    pom_path = _resolve_pom_path()
    if not pom_path.exists():
        return [], set()

    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    tree = ET.parse(pom_path)
    root = tree.getroot()

    lines: list[str] = []
    group_ids: set[str] = set()

    parent = root.find("m:parent", ns)
    if parent is not None:
        g = parent.findtext("m:groupId", "", ns)
        a = parent.findtext("m:artifactId", "", ns)
        v = parent.findtext("m:version", "", ns)
        lines.append(f"parent: {g}:{a}:{v}")
        if g:
            group_ids.add(g)

    for dep in root.findall(".//m:dependencies/m:dependency", ns):
        g = dep.findtext("m:groupId", "", ns)
        a = dep.findtext("m:artifactId", "", ns)
        v = dep.findtext("m:version", "", ns) or "(managed)"
        scope = dep.findtext("m:scope", "", ns)
        entry = f"  - {g}:{a}:{v}"
        if scope:
            entry += f" [{scope}]"
        lines.append(entry)
        if g:
            group_ids.add(g)

    return lines, group_ids


def get_pom_dependencies() -> str:
    """Read the active project pom.xml and return a formatted list of available dependencies.

    In pfy mode reads C:/workspace_pfy/PFY/pfy/pom.xml; in docker mode reads skeleton/backend/pom.xml.
    """
    global _POM_DEPENDENCIES
    if _POM_DEPENDENCIES is not None:
        return _POM_DEPENDENCIES

    lines, _ = _parse_pom_xml()
    _POM_DEPENDENCIES = "\n".join(lines)
    return _POM_DEPENDENCIES


def get_allowed_import_prefixes() -> set[str]:
    """Dynamically determine allowed Java import prefixes from pom.xml groupIds.

    Returns a set of package prefixes (e.g., {"java", "javax", "org.springframework",
    "aondev", "biz", "lombok", "com.common", "com.fasterxml"}).
    Any import not starting with one of these prefixes is from a library NOT in pom.xml.
    """
    global _ALLOWED_PREFIXES
    if _ALLOWED_PREFIXES is not None:
        return _ALLOWED_PREFIXES

    _, group_ids = _parse_pom_xml()
    prefixes: set[str] = set(_ALWAYS_ALLOWED)

    for gid in group_ids:
        if gid in _GROUPID_TO_PACKAGES:
            for pkg in _GROUPID_TO_PACKAGES[gid]:
                if pkg:
                    prefixes.add(pkg)
        else:
            parts = gid.split(".")
            if len(parts) >= 2:
                prefixes.add(f"{parts[0]}.{parts[1]}")
            else:
                prefixes.add(parts[0])

    prefixes.add("aondev")

    _ALLOWED_PREFIXES = prefixes
    return _ALLOWED_PREFIXES


def invalidate_pom_cache() -> None:
    """Force re-read of pom.xml on next access."""
    global _POM_DEPENDENCIES, _ALLOWED_PREFIXES
    _POM_DEPENDENCIES = None
    _ALLOWED_PREFIXES = None


# ---------------------------------------------------------------------------
# Workspace class-to-package map  (STS "Organize Imports" source oracle)
# ---------------------------------------------------------------------------

_CLASS_PACKAGE_MAP: dict[str, str] | None = None

_PACKAGE_RE = re.compile(r'^\s*package\s+([\w.]+)\s*;', re.MULTILINE)
_PUBLIC_TYPE_RE = re.compile(
    r'^\s*public\s+(?:(?:abstract|final|static)\s+)*'
    r'(?:class|interface|enum|@interface)\s+(\w+)',
    re.MULTILINE,
)
_SKIP_DIRS = {"target", "build", ".git", "node_modules", ".settings", ".mvn"}


def _scan_workspace_java_sources() -> dict[str, str]:
    """Walk PFY workspace Java source trees and return {ClassName: fqcn} mapping.

    Scans the directories adjacent to PFY_BACKEND_DIR (i.e., the whole PFY
    multi-module project) and extracts every public class/interface/enum.
    The filename wins when multiple source files declare the same class name.
    This mirrors what STS does: it reads the actual classpath source to know
    the correct package for each class.
    """
    import os

    root = Path(settings.PFY_BACKEND_DIR).parent.parent  # C:/workspace_pfy/PFY
    if not root.exists():
        return {}

    class_map: dict[str, str] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune directories we never need to scan
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]

        for fname in filenames:
            if not fname.endswith(".java"):
                continue

            fpath = Path(dirpath) / fname
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            pkg_m = _PACKAGE_RE.search(text)
            if not pkg_m:
                continue
            pkg = pkg_m.group(1)

            stem = fname[:-5]  # filename without .java
            for cls_m in _PUBLIC_TYPE_RE.finditer(text):
                cls_name = cls_m.group(1)
                fqcn = f"{pkg}.{cls_name}"
                # Prefer the declaration whose filename matches the class name
                if cls_name not in class_map or stem == cls_name:
                    class_map[cls_name] = fqcn

    return class_map


def get_workspace_class_map() -> dict[str, str]:
    """Return cached {ClassName: fqcn} map built from PFY workspace Java sources.

    The map is built once at startup (lazy) and cached for the server lifetime.
    Call invalidate_class_map() to force a rescan (e.g. after source changes).
    """
    global _CLASS_PACKAGE_MAP
    if _CLASS_PACKAGE_MAP is None:
        _CLASS_PACKAGE_MAP = _scan_workspace_java_sources()
    return _CLASS_PACKAGE_MAP


def invalidate_class_map() -> None:
    """Force rescan of workspace Java sources on next access."""
    global _CLASS_PACKAGE_MAP
    _CLASS_PACKAGE_MAP = None
