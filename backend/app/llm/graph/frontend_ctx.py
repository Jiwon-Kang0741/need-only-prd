"""Frontend archetype inference + reference context (ported from agents.py).

Adapted from ctx(SharedContext)-based functions to operate on spec_markdown + the
graph's dict plan. Used to enrich vue_page/vue_* generation prompts.
"""

from __future__ import annotations

import re

_FRONTEND_PAGE_PATH_RE = re.compile(r"src/pages/([^/]+)/([^/]+)/([^/]+)/index\.vue$")

_POPUP_KEYWORDS = ("popup", "팝업", "dialog", "lookup", "searchinput", "사용자 검색")
_EDITABLE_KEYWORDS = ("저장", "수정", "삭제", "등록", "save", "update", "delete",
                      "editable", "add row", "copyinsertrow", "excel upload", "업로드")
_SUMMARY_KEYWORDS = ("집계", "summary", "progress", "status count", "상태별", "카운트")


def infer_frontend_archetype(spec_markdown: str, plan: dict) -> str:
    """Pick a dominant frontend screen pattern from spec + plan (deterministic)."""
    files = (plan or {}).get("files", [])
    plan_text = " ".join(
        f"{f.get('file_type', '')} {f.get('description', '')}".lower()
        for f in files if f.get("layer") == "frontend"
    )
    combined = f"{(spec_markdown or '').lower()}\n{plan_text}"
    has_sum_grid = any(f.get("file_type") == "vue_sum_grid" for f in files)

    if has_sum_grid or any(k in combined for k in _SUMMARY_KEYWORDS):
        return "summary-filter"
    if any(k in combined for k in _EDITABLE_KEYWORDS):
        return "editable-grid"
    if any(k in combined for k in _POPUP_KEYWORDS):
        return "popup-linked"
    return "list-query"


def frontend_route_parts(plan: dict) -> tuple[str, str, str] | None:
    """Extract (module, category, screen_id) from a planned vue page path."""
    for f in (plan or {}).get("files", []):
        if f.get("layer") != "frontend":
            continue
        m = _FRONTEND_PAGE_PATH_RE.search(f.get("file_path", ""))
        if m:
            return m.group(1), m.group(2), m.group(3)
    return None


def hydrate_frontend_reference_context(plan: dict) -> str:
    """Load CPMS frontend reference context for the planned screen route (if any)."""
    parts = frontend_route_parts(plan)
    if parts is None:
        return ""
    try:
        from app.llm.codegen_context import get_frontend_reference_context
        return get_frontend_reference_context(*parts)
    except Exception:
        return ""


_ARCHETYPE_GUIDANCE = {
    "editable-grid": ("editable-grid: grid supports add/edit/delete/save. Keep save buttons "
                      "and row editing inside DataTable, not in index.vue."),
    "summary-filter": ("summary-filter: emphasize SumGrid/aggregate counts above the table; "
                       "filters drive both summary and list."),
    "popup-linked": ("popup-linked: provides a lookup/popup (SearchInput dialog) to pick a "
                     "parent value that filters the list."),
    "list-query": ("list-query: plain search + paginated DataTable, read-only."),
}


def archetype_prompt_block(spec_markdown: str, plan: dict) -> str:
    """Build a vue-prompt block describing the inferred archetype + reference context."""
    arch = infer_frontend_archetype(spec_markdown, plan)
    block = (f"\n=== FRONTEND ARCHETYPE: {arch} ===\n{_ARCHETYPE_GUIDANCE[arch]}\n")
    ref = hydrate_frontend_reference_context(plan)
    if ref:
        block += f"\n=== FRONTEND REFERENCE ===\n{ref[:50000]}\n"
    return block
