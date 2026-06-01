"""LangGraph state schema for code generation."""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict


class GeneratedFile(TypedDict):
    file_path: str
    file_type: str        # dto_request | dao_impl | vue_page | ...
    layer: str            # backend | frontend
    wave: int             # 1 | 2 | 3
    content: str
    status: str           # ok | failed
    status_log: list[str]


def merge_files(
    left: dict[str, GeneratedFile] | None,
    right: dict[str, GeneratedFile] | None,
) -> dict[str, GeneratedFile]:
    """Reducer for parallel file writes. file_path-keyed; right wins on conflict."""
    return {**(left or {}), **(right or {})}


class CodeGenState(TypedDict, total=False):
    # ── 입력 (불변) ──
    session_id: str
    spec_markdown: str
    confirmed_vue: str
    table_info: str
    # ── Contract Extractor 산출 ──
    contract: dict | None
    # ── Planner 산출 ──
    plan: dict | None
    # ── 병렬 생성 결과 ──
    files: Annotated[dict[str, GeneratedFile], merge_files]
    # ── Reviewer ──
    review_iterations: int
    open_issues: list[dict]
    # ── 진행/관찰 ──
    current_wave: int
    events: Annotated[list[dict], add]
