"""Reviewer must actually apply fixes (apply_fix) and tolerate bad tool args. No LLM."""

import json

import pytest

from app.llm.graph import react
from app.llm.graph.tools import TOOL_SPECS, REVIEWER_TOOL_SPECS

pytestmark = pytest.mark.asyncio


class _Call:
    type = "function_call"
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _Resp:
    def __init__(self, output_text="", output=None):
        self.output_text = output_text
        self.output = output or []


class _ScriptedClient:
    """Yields scripted responses for complete_with_tools."""
    def __init__(self, responses):
        self._responses = responses
        self._i = 0
    async def complete_with_tools(self, system, user, tools, max_tokens=16384):
        r = self._responses[self._i]
        self._i += 1
        return r


_DTO = {"file_path": "D.java", "file_type": "dto_response", "layer": "backend",
        "wave": 1, "status": "ok", "status_log": [], "content": "class D {}"}


def test_apply_fix_only_in_reviewer_specs():
    assert "apply_fix" not in {t["name"] for t in TOOL_SPECS}
    assert "apply_fix" in {t["name"] for t in REVIEWER_TOOL_SPECS}


async def test_reviewer_applies_fix_to_files(monkeypatch):
    # turn 1: apply_fix on D.java ; turn 2: DONE
    scripted = _ScriptedClient([
        _Resp(output=[_Call("apply_fix",
                            json.dumps({"file_path": "D.java",
                                        "content": "class D { private String nm; }"}))]),
        _Resp(output_text="DONE", output=[]),
    ])
    monkeypatch.setattr(react, "gpt55_client", scripted)
    out = await react.reviewer({"files": {"D.java": dict(_DTO)}, "contract": {},
                               "review_iterations": 0, "open_issues": []})
    assert out["files"]["D.java"]["content"] == "class D { private String nm; }"
    assert any(e["type"] == "file_fixed" and e["path"] == "D.java" for e in out["events"])


async def test_reviewer_survives_malformed_tool_args(monkeypatch):
    # turn 1: truncated JSON args ; turn 2: DONE — must NOT raise
    scripted = _ScriptedClient([
        _Resp(output=[_Call("cross_check", '{"bad": tru')],),  # malformed
        _Resp(output_text="DONE", output=[]),
    ])
    monkeypatch.setattr(react, "gpt55_client", scripted)
    out = await react.reviewer({"files": {"D.java": dict(_DTO)}, "contract": {},
                               "review_iterations": 0, "open_issues": []})
    # loop completed without crashing; bad-arg observation recorded
    assert out["review_iterations"] >= 2
