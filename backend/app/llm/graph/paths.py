"""Deterministic target-path resolver for generated files.

Backend/data paths come from the FIXED BackendGuide §11.4 table (parsed by
guide_config) — guide-driven, read-only. Frontend paths are a CODE resolver:
the FrontendGuide states them only as prose/examples (no parseable table), so we
substitute a fixed project-layout template validated by guide examples (golden
tests). Takes (module, category, screenId, className) — the resolver substitutes,
it does not derive casing (the Contract supplies both screenId and className).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.graph import guide_config


@dataclass(frozen=True)
class Identity:
    module: str
    category: str
    screen_id: str       # camelCase, e.g. "cpmsEduPondgLst"
    class_name: str      # PascalCase, e.g. "CpmsEduPondgLst" (== {ClassName}/{Screen})


def backend_path(file_type: str, ident: Identity) -> str | None:
    """Backend/data path from §11.4 template, or None if the guide has no template."""
    tpl = guide_config.load_backend_path_templates().get(file_type)
    if not tpl:
        return None
    return (tpl.replace("{module}", ident.module)
               .replace("{ClassName}", ident.class_name)
               .replace("{Screen}", ident.class_name))


def data_path() -> str:
    """The db init SQL output path (db_init_sql template == 'db/init.sql')."""
    return guide_config.load_backend_path_templates().get("db_init_sql", "db/init.sql")


_FE_PAGE_BASE = "src/pages/{module}/{category}/{screenId}"
_FE_API_BASE = "src/api/pages/{module}/{category}"


def _sub(tpl: str, ident: Identity) -> str:
    return (tpl.replace("{module}", ident.module)
               .replace("{category}", ident.category)
               .replace("{screenId}", ident.screen_id)
               .replace("{ClassName}", ident.class_name))


def frontend_paths(ident: Identity, components: list[str]) -> dict[str, str]:
    """Resolve every frontend file path for one screen.

    Folder segments use the camelCase screenId ({screenId}{Comp}); .vue/.scss
    filenames use the PascalCase className ({ClassName}{Comp}). index.vue/ts,
    utils/index.ts, types.ts are lowercase exceptions. types.ts is category-shared.
    Only DataTable gets a utils/ dir.
    """
    page_base = _sub(_FE_PAGE_BASE, ident)
    api_base = _sub(_FE_API_BASE, ident)
    out: dict[str, str] = {
        "vue_page": f"{page_base}/index.vue",
        "vue_page_scss": f"{page_base}/{ident.screen_id}.scss",
        "vue_api": f"{api_base}/{ident.screen_id}.ts",
        "vue_types": f"{api_base}/types.ts",
    }
    for comp in components:           # "SearchForm" | "DataTable" | "SumGrid" | "ProgressList"
        folder = f"{page_base}/components/{ident.screen_id}{comp}"
        key = f"vue_{comp.lower()}"
        out[key] = f"{folder}/{ident.class_name}{comp}.vue"
        out[f"{key}_scss"] = f"{folder}/{ident.class_name}{comp}.scss"
        if comp == "DataTable":
            out["vue_datatable_utils"] = f"{folder}/utils/index.ts"
    return out
