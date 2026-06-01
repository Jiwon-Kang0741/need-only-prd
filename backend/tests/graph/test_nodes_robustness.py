"""contract_extract retry-parse guard (F4) + gate failed status (F5). No LLM."""

import pytest

from app.llm.graph import nodes

pytestmark = pytest.mark.asyncio


class _Client:
    def __init__(self, replies):
        self._replies = replies
        self._i = 0
    async def complete(self, system, user, max_tokens=16384):
        r = self._replies[self._i]
        self._i += 1
        return r


async def test_contract_extract_raises_clean_error_on_repeated_bad_json(monkeypatch):
    # both attempts return non-JSON → should raise a clear ValueError, not bare JSONDecodeError
    monkeypatch.setattr(nodes, "gpt55_client", _Client(["not json", "still not json"]))
    with pytest.raises(ValueError):
        await nodes.contract_extract({"spec_markdown": "s", "confirmed_vue": "v",
                                      "table_info": "t"})


async def test_generate_file_marks_failed_when_gate_unresolved(monkeypatch):
    # both attempts keep the UUID violation → status must be 'failed', not 'ok'
    monkeypatch.setattr(nodes, "gpt55_client",
                        _Client(["import java.util.UUID; class A {}",
                                 "import java.util.UUID; class A {}"]))
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "G")
    spec = {"file_path": "A.java", "file_type": "dto_request", "layer": "backend",
            "class_name": "A", "description": "d", "wave": 1}
    out = await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    gf = out["files"]["A.java"]
    assert gf["status"] == "failed"
    assert any("UUID" in i["issue"] for i in out["open_issues"])


async def test_generate_file_ok_when_clean(monkeypatch):
    monkeypatch.setattr(nodes, "gpt55_client",
                        _Client(["class A { private String id; }"]))
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "G")
    spec = {"file_path": "A.java", "file_type": "dto_request", "layer": "backend",
            "class_name": "A", "description": "d", "wave": 1}
    out = await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    assert out["files"]["A.java"]["status"] == "ok"
