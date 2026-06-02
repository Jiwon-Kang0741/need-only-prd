"""CPMS domain validators ported from the legacy agents.py (dict-based, no LLM).

These were valuable deterministic checks living in the old static_check stack.
Adapted to the graph's dict GeneratedFile shape (gf["file_type"] etc.).
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

_RELATIVE_IMPORT_RE = re.compile(
    r'^\s*import\s+[\s\S]*?\s+from\s+[\'"](\.[^\'"]+)[\'"]',
    re.MULTILINE,
)


def extract_markdown_section(markdown: str, heading_prefix: str) -> str:
    """Extract a markdown section by heading prefix (e.g., '## 7.')."""
    if not markdown:
        return ""
    m = re.search(rf"^{re.escape(heading_prefix)}.*$", markdown, flags=re.MULTILINE)
    if not m:
        return ""
    start = m.start()
    tail = markdown[start:]
    n = re.search(r"^##\s+\d+[\.\-]?\s", tail[len(m.group(0)):], flags=re.MULTILINE)
    if not n:
        return tail.strip()
    end = start + len(m.group(0)) + n.start()
    return markdown[start:end].strip()


def check_db_seed_sql(files: dict) -> list[dict]:
    """Validate db_init_sql minimum seed rules (ported from agents._check_db_seed_sql)."""
    issues: list[dict] = []
    db_files = [gf for gf in files.values() if gf["file_type"] == "db_init_sql"]
    if not db_files:
        return issues

    expected_pgm_urls: list[str] = []
    for gf in files.values():
        if gf["file_type"] != "vue_page":
            continue
        fp = gf["file_path"].replace("\\", "/")
        if "/pages/" in fp and fp.endswith("/index.vue"):
            rel = fp.split("/pages/", 1)[1].removesuffix("/index.vue").strip("/")
            if rel:
                expected_pgm_urls.append(f"/pages/{rel}/index.vue".lower())

    for gf in db_files:
        raw = gf["content"]
        content = raw.lower()
        required_tables = ["cmn_lbl", "cmn_pgm", "cmn_menu", "cmn_role_pgm", "cmn_role_menu"]
        missing = [t for t in required_tables if t not in content]
        if missing:
            issues.append({
                "file_path": gf["file_path"],
                "issue": f"[STATIC] db_init_sql missing required seed tables: {', '.join(missing)}",
                "fix_instruction": (
                    "Include seed SQL for cmn_lbl, cmn_pgm, cmn_menu, cmn_role_pgm, cmn_role_menu "
                    "following Section 7 DB Seed rules."
                ),
            })
        else:
            seed_order = ["cmn_class", "cmn_code", "cmn_lbl", "cmn_pgm",
                          "cmn_menu", "cmn_role_pgm", "cmn_role_menu"]
            idx = {t: content.find(t) for t in seed_order}
            if "cmn_code" in content and "cmn_class" not in content:
                issues.append({
                    "file_path": gf["file_path"],
                    "issue": "[STATIC] db_init_sql has cmn_code without cmn_class",
                    "fix_instruction": "Insert cmn_class rows before cmn_code per SEED_STANDARD §3 / §16.4.",
                })
            if "cmn_class" in content and "cmn_code" not in content:
                issues.append({
                    "file_path": gf["file_path"],
                    "issue": "[STATIC] db_init_sql has cmn_class without cmn_code",
                    "fix_instruction": "Add cmn_code rows for each class or remove cmn_class if not used.",
                })
            for a, b in zip(seed_order, seed_order[1:]):
                ia, ib = idx[a], idx[b]
                if ia != -1 and ib != -1 and ia >= ib:
                    issues.append({
                        "file_path": gf["file_path"],
                        "issue": "[STATIC] db_init_sql seed table order does not follow Section 7 / SEED_STANDARD",
                        "fix_instruction": (
                            "Reorder seed blocks as: cmn_class (if any) -> cmn_code (if any) -> "
                            "cmn_lbl -> cmn_pgm -> cmn_menu -> cmn_role_pgm -> cmn_role_menu."
                        ),
                    })
                    break

        if "dev_auto" not in content:
            issues.append({
                "file_path": gf["file_path"],
                "issue": "[STATIC] db_init_sql missing DEV_AUTO role mapping",
                "fix_instruction": "Insert DEV_AUTO into both cmn_role_pgm and cmn_role_menu mappings.",
            })
        if "root98" not in content:
            issues.append({
                "file_path": gf["file_path"],
                "issue": "[STATIC] db_init_sql missing ROOT98 fallback rule",
                "fix_instruction": "Add fallback menu parent ROOT98 and ROOT98_YYMMDD_NNN menu_id generation handling.",
            })
        if "cmn_lbl" in content and "on conflict" not in content:
            issues.append({
                "file_path": gf["file_path"],
                "issue": "[STATIC] db_init_sql missing PostgreSQL upsert style for cmn_lbl",
                "fix_instruction": ("Use INSERT ... ON CONFLICT ... DO UPDATE for cmn_lbl seed rows "
                                    "(do not use MERGE)."),
            })
        if "cmn_lbl" in content and "ko_kr" not in content and "ko-kr" not in content:
            issues.append({
                "file_path": gf["file_path"],
                "issue": "[STATIC] db_init_sql missing default lang_cd='ko-KR' for cmn_lbl",
                "fix_instruction": ("Ensure cmn_lbl seed rows include lang_cd with default 'ko-KR'."),
            })

        label_key_pattern = re.compile(r"'[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+'")
        if "cmn_lbl" in content and not label_key_pattern.search(raw):
            issues.append({
                "file_path": gf["file_path"],
                "issue": "[STATIC] db_init_sql missing screen label keys for cmn_lbl",
                "fix_instruction": ("Include screen UI label IDs in cmn_lbl with pattern "
                                    "{화면코드}.{대컴포넌트명}.{라벨ID}."),
            })
        if "cmn_lbl" in content:
            markers = ("searchform.", "datatable.", "sumgrid.", "editdialog.",
                       "detaildialog.", "detailpanel.", "tabpanel.")
            if not any(mk in content for mk in markers):
                issues.append({
                    "file_path": gf["file_path"],
                    "issue": "[STATIC] db_init_sql label prefix does not match generated screen/component names",
                    "fix_instruction": ("Use actual generated component prefixes for cmn_lbl keys "
                                        "(e.g. SearchForm.*, DataTable.*, SumGrid.*)."),
                })

        if expected_pgm_urls and not any(url in content for url in expected_pgm_urls):
            issues.append({
                "file_path": gf["file_path"],
                "issue": "[STATIC] db_init_sql missing cmn_pgm.pgm_url derived from actual vue_page path",
                "fix_instruction": ("Set cmn_pgm.pgm_url using vue_page path rule: "
                                    "/pages/{module}/{category}/{screenId}/index.vue."),
            })
    return issues


def _resolve_frontend_import_candidates(source_path: str, import_path: str) -> list[str]:
    base = PurePosixPath(source_path).parent
    resolved = PurePosixPath(base.joinpath(import_path))
    resolved_str = resolved.as_posix()
    if resolved.suffix:
        return [resolved_str]
    return [f"{resolved_str}.vue", f"{resolved_str}.ts",
            f"{resolved_str}/index.vue", f"{resolved_str}/index.ts"]


def check_frontend_local_imports(files: dict) -> list[dict]:
    """Ensure generated frontend files only import local files that actually exist."""
    issues: list[dict] = []
    frontend_files = [gf for gf in files.values() if gf["layer"] == "frontend"]
    if not frontend_files:
        return issues

    known_paths = {gf["file_path"].replace("\\", "/") for gf in frontend_files}
    for gf in frontend_files:
        if not (gf["file_path"].endswith(".vue") or gf["file_path"].endswith(".ts")):
            continue
        for import_path in _RELATIVE_IMPORT_RE.findall(gf["content"]):
            if import_path.endswith((".scss", ".css")):
                continue
            candidates = _resolve_frontend_import_candidates(
                gf["file_path"].replace("\\", "/"), import_path)
            if any(c in known_paths for c in candidates):
                continue
            issues.append({
                "file_path": gf["file_path"],
                "issue": (f"[STATIC] Local import '{import_path}' does not resolve to any generated "
                          "frontend file. Do not import unplanned child components or missing modules."),
                "fix_instruction": (f"Remove the import '{import_path}' from {gf['file_path']} or "
                                    "generate the missing file."),
            })
    return issues
