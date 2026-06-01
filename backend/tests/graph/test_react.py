"""Reviewer ReAct loop tests using the REAL gpt-5.5 LLM (tool-calling)."""

import pytest

from app.llm.graph import react

pytestmark = [pytest.mark.asyncio, pytest.mark.llm]

_CLEAN_DTO = {
    "file_path": "CpmsEduResDto.java", "file_type": "dto_response", "layer": "backend",
    "wave": 1, "status": "ok", "status_log": [],
    "content": "public class CpmsEduResDto { private String eduPgmNm; }",
}
_GOOD_SVC = {
    "file_path": "CpmsEduServiceImpl.java", "file_type": "service_impl", "layer": "backend",
    "wave": 3, "status": "ok", "status_log": [],
    "content": "public class CpmsEduServiceImpl { void f(CpmsEduResDto d){ d.getEduPgmNm(); } }",
}
_BAD_SVC = {
    "file_path": "CpmsEduServiceImpl.java", "file_type": "service_impl", "layer": "backend",
    "wave": 3, "status": "ok", "status_log": [],
    "content": "public class CpmsEduServiceImpl { void f(CpmsEduResDto d){ d.getNope(); } }",
}


async def test_reviewer_runs_and_returns_state():
    """Reviewer executes the ReAct loop, returns iterations + open_issues."""
    out = await react.reviewer({
        "files": {"CpmsEduResDto.java": _CLEAN_DTO, "CpmsEduServiceImpl.java": _GOOD_SVC},
        "contract": {}, "review_iterations": 0, "open_issues": [],
    })
    assert out["review_iterations"] >= 1
    assert out["review_iterations"] <= react.REVIEWER_HARD_CAP
    assert isinstance(out["open_issues"], list)
    # a clean codebase -> cross_check finds no missing-field issues
    assert out["open_issues"] == []


async def test_reviewer_detects_cross_file_issue_via_tools():
    """With a getNope() call on a DTO lacking that field, cross_check flags it.

    The reviewer may or may not fix it within the cap, but the convergence
    signal (cross_check) must surface the inconsistency in open_issues OR the
    model must have fixed the file (issue gone). Either way the loop ran tools.
    """
    out = await react.reviewer({
        "files": {"CpmsEduResDto.java": _CLEAN_DTO, "CpmsEduServiceImpl.java": _BAD_SVC},
        "contract": {}, "review_iterations": 0, "open_issues": [],
    })
    fixed = out["open_issues"] == []
    flagged = any("getNope" in i["issue"] or "Nope" in i["issue"]
                  for i in out["open_issues"])
    assert fixed or flagged
    # the loop issued at least one tool call along the way
    assert any(e["type"] == "tool_call" for e in out["events"])
