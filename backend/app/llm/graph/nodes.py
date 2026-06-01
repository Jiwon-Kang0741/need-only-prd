"""Code-generation graph nodes (pure async functions)."""

from __future__ import annotations

import json

from app.llm.graph import guides
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import CONTRACT_SYSTEM, GENERATOR_SYSTEM, PLANNER_SYSTEM
from app.llm.graph.waves import wave_for_file_type
from app.llm.graph.tools import static_check_impl, validate_sql_impl
from app.llm.graph.config import GATE_MAX_REGEN


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        nl = text.index("\n") if "\n" in text else 3
        text = text[nl + 1:]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3].rstrip()
    return text


def _parse_json(text: str) -> dict:
    return json.loads(_strip_fences(text))


async def contract_extract(state: dict) -> dict:
    """Extract structured contract from spec + confirmed Vue + table info."""
    user = (
        f"=== SPEC ===\n{state['spec_markdown']}\n\n"
        f"=== CONFIRMED VUE ===\n{state['confirmed_vue']}\n\n"
        f"=== TABLE INFO ===\n{state.get('table_info', '')}\n"
    )
    raw = await gpt55_client.complete(CONTRACT_SYSTEM, user)
    try:
        contract = _parse_json(raw)
    except (ValueError, json.JSONDecodeError):
        # one retry with explicit instruction
        raw = await gpt55_client.complete(
            CONTRACT_SYSTEM, user + "\n\nReturn ONLY valid JSON.")
        contract = _parse_json(raw)
    return {"contract": contract,
            "events": [{"type": "contract", "contract": contract}]}


async def planner(state: dict) -> dict:
    """Plan files from contract; wave numbers assigned by code (not LLM)."""
    user = f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n"
    raw = await gpt55_client.complete(PLANNER_SYSTEM, user)
    plan = _parse_json(raw)
    for f in plan.get("files", []):
        f["wave"] = wave_for_file_type(f["file_type"])
    return {"plan": plan, "current_wave": 1,
            "events": [{"type": "plan", "files": plan.get("files", [])}]}


def _gate_check(spec: dict, content: str) -> list[dict]:
    """Run the deterministic gate for a file (static_check, or validate_sql for SQL)."""
    if spec["file_type"] == "db_init_sql":
        return validate_sql_impl(content)
    return static_check_impl(spec["file_path"], content, spec["file_type"], spec["layer"])


def _dep_context(state: dict, spec: dict) -> str:
    """Inject already-generated files from earlier waves as dependency context."""
    my_wave = spec["wave"]
    deps = [gf for gf in state.get("files", {}).values() if gf["wave"] < my_wave]
    if not deps:
        return ""
    parts = [f"--- {gf['file_path']} ---\n{gf['content']}" for gf in deps]
    return "\n\n=== DEPENDENCY FILES ===\n" + "\n\n".join(parts)


async def generate_file(state: dict) -> dict:
    """Generate ONE file (single-shot) + static_check gate (1 regen). For Send fan-out."""
    spec = state["_file_spec"]
    guide = guides.load_guide_for_file_type(spec["file_type"])
    base_user = (
        f"=== CONTRACT ===\n{json.dumps(state['contract'], ensure_ascii=False)}\n\n"
        f"=== GUIDE ===\n{guide}\n"
        f"{_dep_context(state, spec)}\n\n"
        f"Generate file: {spec['file_path']} (type={spec['file_type']}, "
        f"class={spec.get('class_name', '')})\n{spec.get('description', '')}"
    )
    content = _strip_fences(await gpt55_client.complete(GENERATOR_SYSTEM, base_user))
    issues = _gate_check(spec, content)

    regen = 0
    while issues and regen < GATE_MAX_REGEN:
        fix_user = (base_user + "\n\n=== FIX THESE VIOLATIONS ===\n"
                    + "\n".join(f"- {i['issue']}" for i in issues))
        content = _strip_fences(await gpt55_client.complete(GENERATOR_SYSTEM, fix_user))
        issues = _gate_check(spec, content)
        regen += 1

    gf = {"file_path": spec["file_path"], "file_type": spec["file_type"],
          "layer": spec["layer"], "wave": spec["wave"], "content": content,
          "status": "ok", "status_log": [f"gate regen={regen}"]}
    result = {"files": {spec["file_path"]: gf},
              "events": [{"type": "file_complete", "path": spec["file_path"],
                          "layer": spec["layer"]}]}
    if issues:
        result["open_issues"] = issues  # passed through; reviewer will handle
    return result
