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


_TABLE_INFO: str | None = None

# DataGuide 하단 발췌 — DataEngineerAgent DDL·공통 시드 SQL 근거 (토큰 절약을 위해 파일별 시작 마커 이후만 로드)
_DATA_ENGINEER_DATAGUIDE: str | None = None
_DATAGUIDE_DATA_ENGINEER_START: dict[str, str] = {
    "00.data_standard.md": "## 3. Data Type Standard",
    "01.seed_standard.md": "# 12. Validation 규칙",
}


def invalidate_cache() -> None:
    """Force re-read of guide files on next access."""
    global _BACKEND_SECTIONS, _FRONTEND_SECTIONS, _NAMING_CONTEXT, _TABLE_INFO, _DATA_ENGINEER_DATAGUIDE
    _BACKEND_SECTIONS = None
    _FRONTEND_SECTIONS = None
    _NAMING_CONTEXT = None
    _TABLE_INFO = None
    _DATA_ENGINEER_DATAGUIDE = None


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
    "vue_page": [
        ("00_", None),
        ("01_", None),
        ("02_", None),
        ("07_", None),
        ("08_", ["searchParams 패턴", "provide/inject 패턴"]),
        ("11_", ["provide/inject 패턴", "computed로 옵션 정의", "Select 컴포넌트 연결"]),
    ],
    "vue_search_form": [
        ("01_", None),
        ("02_", None),
        ("03_", None),
        ("07_", None),
        ("08_", ["searchParams 패턴", "provide/inject 패턴", "watch 패턴"]),
        ("11_", ["provide/inject 패턴", "computed로 옵션 정의", "options() 메서드 파라미터", "Select 컴포넌트 연결"]),
        ("12_", ["SearchForm", "SearchFormRow", "SearchFormField", "SearchFormLabel", "SearchFormContent", "SearchFormFieldGroup", "Import 패턴", "검색 화면"]),
    ],
    "vue_data_table": [("01_", None), ("02_", None), ("04_", None), ("07_", None)],
    "vue_data_table_utils": [("02_", None), ("04_", None)],
    "vue_sum_grid": [("02_", None), ("05_", None), ("07_", None)],
    "vue_api": [("02_", ["Types.ts 위치"]), ("06_", None)],
    "vue_types": [("02_", ["Types.ts 위치"]), ("06_", None)],
    "vue_scss": [("07_", None)],
}

_FRONTEND_PLANNING_PREFIXES: tuple[str, ...] = (
    "00_",
    "01_",
    "02_",
    "03_",
    "04_",
    "05_",
    "06_",
    "07_",
    "09_",
    "11_",
    "12_",
    "13_",
    "14_",
)

_FRONTEND_QA_PREFIXES: tuple[str, ...] = (
    "00_",
    "01_",
    "02_",
    "03_",
    "04_",
    "05_",
    "06_",
    "07_",
    "09_",
    "11_",
    "12_",
    "13_",
    "14_",
)


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


def _collect_full_files_by_prefixes(
    sections_db: dict[str, dict[str, str]],
    prefixes: tuple[str, ...],
) -> str:
    parts: list[str] = []
    for fname in sorted(sections_db):
        if not any(fname.startswith(prefix) for prefix in prefixes):
            continue
        full = "\n".join(sections_db[fname].values())
        parts.append(f"=== {fname} ===\n{full}")
    return "\n\n".join(parts)


def get_frontend_planning_context() -> str:
    """Return a curated FrontendGuide subset for the planning step.

    This intentionally excludes legacy duplicate markdown files that do not
    follow the numbered guide convention, so the planner sees a single,
    consistent frontend contract.
    """
    _ensure_loaded()
    assert _FRONTEND_SECTIONS is not None
    return _collect_full_files_by_prefixes(_FRONTEND_SECTIONS, _FRONTEND_PLANNING_PREFIXES)


def get_frontend_qa_context() -> str:
    """Return a curated FrontendGuide subset for frontend QA.

    QA should validate against the same numbered guide set used by generation,
    not against stale duplicate docs that may contain conflicting API/style
    conventions.
    """
    _ensure_loaded()
    assert _FRONTEND_SECTIONS is not None
    return _collect_full_files_by_prefixes(_FRONTEND_SECTIONS, _FRONTEND_QA_PREFIXES)


def _safe_read_lines(path: Path, max_lines: int = 120) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append("... (truncated)")
    return "\n".join(lines).strip()


def _resolve_reference_types_path(api_dir: Path, screen_id: str) -> Path | None:
    shared_types = api_dir / "types.ts"
    screen_types = api_dir / f"{screen_id}Types.ts"
    if shared_types.exists():
        return shared_types
    if screen_types.exists():
        return screen_types
    return None


def get_frontend_reference_context(
    module: str,
    category: str,
    screen_id: str,
    *,
    max_screens: int = 2,
) -> str:
    """Load concise PFY reference screen snippets from the active frontend workspace.

    The goal is not to dump entire source files, but to show the generator
    a few real PFY patterns from sibling screens in the same module/category.
    Missing workspaces are treated as a no-op.
    """
    base_front = Path(settings.PFY_FRONT_DIR)
    pages_dir = base_front / "src" / "pages" / module / category
    api_dir = base_front / "src" / "api" / "pages" / module / category
    if not pages_dir.exists():
        return ""

    parts: list[str] = []
    candidates = sorted(
        path for path in pages_dir.iterdir()
        if path.is_dir() and path.name != screen_id and (path / "index.vue").exists()
    )

    for candidate in candidates[:max_screens]:
        sections: list[str] = []

        index_snippet = _safe_read_lines(candidate / "index.vue", max_lines=140)
        if index_snippet:
            sections.append(f"--- index.vue ---\n{index_snippet}")

        search_form = next(candidate.rglob("*SearchForm.vue"), None)
        if search_form is not None:
            snippet = _safe_read_lines(search_form, max_lines=140)
            if snippet:
                sections.append(f"--- {search_form.relative_to(candidate).as_posix()} ---\n{snippet}")

        data_table = next(candidate.rglob("*DataTable.vue"), None)
        if data_table is not None:
            snippet = _safe_read_lines(data_table, max_lines=160)
            if snippet:
                sections.append(f"--- {data_table.relative_to(candidate).as_posix()} ---\n{snippet}")

        api_file = api_dir / f"{candidate.name}.ts"
        if api_file.exists():
            snippet = _safe_read_lines(api_file, max_lines=120)
            if snippet:
                sections.append(f"--- api/{api_file.name} ---\n{snippet}")

        types_file = _resolve_reference_types_path(api_dir, candidate.name)
        if types_file is not None:
            snippet = _safe_read_lines(types_file, max_lines=120)
            if snippet:
                sections.append(f"--- api/{types_file.name} ---\n{snippet}")

        if sections:
            parts.append(
                f"=== PFY REFERENCE SCREEN: {candidate.name} ===\n" + "\n\n".join(sections)
            )

    return "\n\n".join(parts)


def get_table_info() -> str:
    """Return the PFY DB table schema reference (테이블정보.md).

    This file lists all existing PFYDB tables with column definitions.
    Agents that generate SQL (db_init_sql, mapper_xml) must check this
    before creating new tables — if an identical or equivalent table
    already exists, reuse it and write queries against the existing schema.
    """
    global _TABLE_INFO
    if _TABLE_INFO is not None:
        return _TABLE_INFO
    base = Path(settings.PROMPT_REFERENCE_DIR) / "BackendGuide"
    table_file = base / "테이블정보.md"
    if table_file.exists():
        _TABLE_INFO = table_file.read_text(encoding="utf-8")
    else:
        _TABLE_INFO = ""
    return _TABLE_INFO


def get_dataguide_data_engineer_excerpt() -> str:
    """Return concatenated lower sections of `pfy_prompt/DataGuide/*.md` for Data Engineer.

    Used as the authoritative contract for:
    - Business table DDL: logical→Postgres types (§3), PK/FK placement (ALTER at file end), audit §5, soft-delete §6–6.1
    - Seed / init.sql: validation, deterministic rules, output order, `cmn_*` consistency §16

    Each file is sliced from the first line matching ``_DATAGUIDE_DATA_ENGINEER_START``; if the
    marker is missing, the full file is included so generation never runs blind.
    """
    global _DATA_ENGINEER_DATAGUIDE
    if _DATA_ENGINEER_DATAGUIDE is not None:
        return _DATA_ENGINEER_DATAGUIDE
    base = Path(settings.PROMPT_REFERENCE_DIR) / "DataGuide"
    if not base.is_dir():
        _DATA_ENGINEER_DATAGUIDE = ""
        return ""
    parts: list[str] = []
    for path in sorted(base.glob("*.md")):
        marker = _DATAGUIDE_DATA_ENGINEER_START.get(path.name)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if marker:
            idx = text.find(marker)
            excerpt = text[idx:].strip() if idx >= 0 else text.strip()
            label = f"DataGuide/{path.name} (from «{marker}»)"
        else:
            excerpt = text.strip()
            label = f"DataGuide/{path.name} (full file)"
        if excerpt:
            parts.append(f"=== {label} ===\n{excerpt}")
    _DATA_ENGINEER_DATAGUIDE = "\n\n".join(parts)
    return _DATA_ENGINEER_DATAGUIDE


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
_CLASS_FILE_MAP: dict[str, Path] | None = None  # ClassName → source file Path

_PACKAGE_RE = re.compile(r'^\s*package\s+([\w.]+)\s*;', re.MULTILINE)
_PUBLIC_TYPE_RE = re.compile(
    r'^\s*public\s+(?:(?:abstract|final|static)\s+)*'
    r'(?:class|interface|enum|@interface)\s+(\w+)',
    re.MULTILINE,
)
_PRIVATE_FIELD_RE = re.compile(
    r'^\s*(?:@\w+(?:\([^)]*\))?\s*)*'   # optional annotations
    r'private\s+'
    r'(?:(?:static|final|transient|volatile)\s+)*'
    r'[\w<>\[\],\s]+?\s+'                # type (can be generic)
    r'(\w+)\s*(?:=\s*[^;]+)?;',         # field name
    re.MULTILINE,
)
_SKIP_DIRS = {"target", "build", ".git", "node_modules", ".settings", ".mvn"}


def _scan_workspace_java_sources() -> tuple[dict[str, str], dict[str, Path]]:
    """Walk PFY workspace Java source trees.

    Returns:
        ({ClassName: fqcn}, {ClassName: source_file_path})
    """
    import os

    root = Path(settings.PFY_BACKEND_DIR).parent.parent  # C:/workspace_pfy/PFY
    if not root.exists():
        return {}, {}

    class_map: dict[str, str] = {}
    file_map: dict[str, Path] = {}

    for dirpath, dirnames, filenames in os.walk(root):
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

            stem = fname[:-5]
            for cls_m in _PUBLIC_TYPE_RE.finditer(text):
                cls_name = cls_m.group(1)
                fqcn = f"{pkg}.{cls_name}"
                if cls_name not in class_map or stem == cls_name:
                    class_map[cls_name] = fqcn
                    file_map[cls_name] = fpath

    return class_map, file_map


def get_workspace_class_map() -> dict[str, str]:
    """Return cached {ClassName: fqcn} map built from PFY workspace Java sources."""
    global _CLASS_PACKAGE_MAP, _CLASS_FILE_MAP
    if _CLASS_PACKAGE_MAP is None:
        _CLASS_PACKAGE_MAP, _CLASS_FILE_MAP = _scan_workspace_java_sources()
    return _CLASS_PACKAGE_MAP


def invalidate_class_map() -> None:
    """Force rescan of workspace Java sources on next access."""
    global _CLASS_PACKAGE_MAP, _CLASS_FILE_MAP
    _CLASS_PACKAGE_MAP = None
    _CLASS_FILE_MAP = None


# ---------------------------------------------------------------------------
# Parent DTO field extraction  (dynamic — no hardcoding)
# ---------------------------------------------------------------------------

_PARENT_FIELDS_CACHE: dict[str, set[str]] = {}


def get_parent_class_fields(class_name: str) -> set[str]:
    """Return the set of private field names declared in a parent class.

    Scans the PFY workspace source files to find the class, then extracts
    all private field declarations.  Results are cached per class name.

    Usage: when generating a DTO that extends SearchBaseDto, call
    get_parent_class_fields("SearchBaseDto") to get {"page", "size"}.
    Any field in this set MUST NOT be redeclared in the child DTO.
    """
    if class_name in _PARENT_FIELDS_CACHE:
        return _PARENT_FIELDS_CACHE[class_name]

    # Ensure scan has run so _CLASS_FILE_MAP is populated
    get_workspace_class_map()
    global _CLASS_FILE_MAP

    fields: set[str] = set()
    if _CLASS_FILE_MAP and class_name in _CLASS_FILE_MAP:
        src = _CLASS_FILE_MAP[class_name]
        try:
            text = src.read_text(encoding="utf-8", errors="ignore")
            for m in _PRIVATE_FIELD_RE.finditer(text):
                fields.add(m.group(1))
        except OSError:
            pass

    _PARENT_FIELDS_CACHE[class_name] = fields
    return fields


def get_parent_class_source_block(class_name: str) -> str:
    """Return a concise description of the parent class fields for use in prompts.

    Returns a string like:
        SearchBaseDto declares: page, size  (getOffset()/getLimit() are computed methods — NOT fields)
    """
    get_workspace_class_map()
    global _CLASS_FILE_MAP

    if not _CLASS_FILE_MAP or class_name not in _CLASS_FILE_MAP:
        return f"{class_name}: (source not found in workspace)"

    src = _CLASS_FILE_MAP[class_name]
    try:
        text = src.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return f"{class_name}: (could not read source)"

    fields: list[str] = []
    for m in _PRIVATE_FIELD_RE.finditer(text):
        fields.append(m.group(1))

    # Extract method names to warn about computed vs field
    method_re = re.compile(r'public\s+\w[\w<>\[\]]*\s+(\w+)\s*\(', re.MULTILINE)
    methods = [m.group(1) for m in method_re.finditer(text)
               if m.group(1) not in ("get", "set", "<init>")]

    result = f"{class_name} private fields: {', '.join(fields) if fields else '(none)'}"
    if methods:
        result += f"\n  (public methods — NOT redeclarable as fields: {', '.join(methods)})"
    return result


def invalidate_parent_fields_cache() -> None:
    """Force re-extraction of parent class fields on next access."""
    global _PARENT_FIELDS_CACHE
    _PARENT_FIELDS_CACHE.clear()
