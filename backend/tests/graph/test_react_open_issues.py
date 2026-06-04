import pytest

from app.llm.graph import react

pytestmark = pytest.mark.asyncio


class _NoToolResp:
    def __init__(self):
        self.output = []
        self.output_text = "DONE"


class _NoToolClient:
    async def complete_with_tools(self, system, user, tools):
        return _NoToolResp()


async def test_reviewer_preserves_incoming_open_issues(monkeypatch):
    monkeypatch.setattr(react, "gpt55_client", _NoToolClient())
    incoming = [{
        "file_path": "a/FooServiceImpl.java",
        "issue": "DAO call type mismatch: fooDao.updateFoo(FooResDto) -> expected (List<FooResDto>)",
        "severity": "error",
    }]
    out = await react.reviewer({
        "files": {},
        "contract": {},
        "review_iterations": 0,
        "open_issues": incoming,
    })
    assert out["open_issues"] == incoming
