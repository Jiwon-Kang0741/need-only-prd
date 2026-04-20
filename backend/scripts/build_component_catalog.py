"""원본 pfy-front의 템플릿/공통 컴포넌트 메타를 componentCatalog.md로 생성.

사용:
  python backend/scripts/build_component_catalog.py

출력: pfy_prompt/componentCatalog.md
"""
from __future__ import annotations

import re
from pathlib import Path

PFY_FRONT_ROOT = Path("/Users/g1_kang/Downloads/pfy-front/src")
OUTPUT = Path(__file__).parent.parent.parent / "pfy_prompt" / "componentCatalog.md"

TEMPLATE_DIRS = [
    "templates/TypeA_StandardSearch",
    "templates/TypeB_InputDetail",
    "templates/TypeC_TreeGrid",
    "templates/TypeD_MasterDetail",
]

COMMON_COMPONENT_DIRS = [
    "components/common/searchForm",
    "components/common/dataTable2",
    "components/common/treeTable",
    "components/common/button",
    "components/common/select",
    "components/common/inputText",
    "components/common/inputNumber",
    "components/common/datePicker",
    "components/common/textarea",
    "components/common/contentHeader",
    "components/common/paginator",
    "components/common/splitter",
    "components/common/radioButton",
    "components/common/toggleSwitch",
]


def extract_template_section(vue_source: str) -> str:
    m = re.search(r"<template[^>]*>(.*?)</template>", vue_source, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_props(vue_source: str) -> list[str]:
    """defineProps<{...}>()에서 prop 이름 추출."""
    m = re.search(r"defineProps<\{([^}]*)\}>", vue_source, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    return re.findall(r"^\s*(\w+)[\?:]", body, re.MULTILINE)


def main() -> None:
    lines: list[str] = [
        "# Component Catalog",
        "",
        "원본 pfy-front의 템플릿 및 공통 컴포넌트 시그니처. ",
        "Mockup 생성 LLM은 여기 등록된 컴포넌트만 사용해야 한다.",
        "",
        "## 페이지 템플릿 (TypeA~D)",
        "",
        "각 생성 페이지는 반드시 아래 4개 중 하나를 상속(사용)해야 한다:",
        "",
    ]

    for rel in TEMPLATE_DIRS:
        full = PFY_FRONT_ROOT / rel / "index.vue"
        if not full.exists():
            lines.append(f"- `@/{rel}` — **파일 없음**")
            continue
        src = full.read_text(encoding="utf-8")
        template = extract_template_section(src)
        props = extract_props(src)
        preview = "\n".join(template.splitlines()[:40])
        lines.append(f"### `@/{rel}`")
        lines.append("")
        if props:
            lines.append(f"**Props**: {', '.join(props)}")
            lines.append("")
        lines.append("**Template 구조 (상위 40줄)**:")
        lines.append("```vue")
        lines.append(preview)
        lines.append("```")
        lines.append("")

    lines.append("## 공통 컴포넌트")
    lines.append("")
    lines.append("생성 페이지는 아래 공통 컴포넌트만 import하여 사용한다:")
    lines.append("")

    for rel in COMMON_COMPONENT_DIRS:
        full = PFY_FRONT_ROOT / rel
        if not full.exists():
            continue
        index = full / "index.ts"
        if index.exists():
            exports_raw = index.read_text(encoding="utf-8")
            exports = re.findall(r"export\s+\{([^}]+)\}", exports_raw)
            names = []
            for e in exports:
                names.extend(n.strip() for n in e.split(","))
            lines.append(f"- `@/{rel}` → `{{ {', '.join(names)} }}`")
        else:
            vues = list(full.glob("*.vue"))
            names = [v.stem for v in vues]
            lines.append(f"- `@/{rel}` → `{', '.join(names)}.vue`")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
