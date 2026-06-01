from app.llm.graph.sse_adapter import graph_files_to_pydantic, build_graph_input


def test_graph_files_to_pydantic_converts_dict_to_list():
    files = {
        "A.java": {"file_path": "A.java", "file_type": "dto_request",
                   "layer": "backend", "wave": 1, "content": "class A{}",
                   "status": "ok", "status_log": []},
    }
    out = graph_files_to_pydantic(files)
    assert len(out) == 1
    assert out[0].file_path == "A.java"
    assert out[0].file_type == "dto_request"
    assert out[0].layer == "backend"
    assert out[0].content == "class A{}"


def test_graph_files_to_pydantic_empty():
    assert graph_files_to_pydantic({}) == []


def test_build_graph_input_pulls_vue_and_table(monkeypatch):
    import app.llm.graph.sse_adapter as mod
    monkeypatch.setattr(mod.guides, "load_table_info", lambda: "TABLE_INFO")

    class FakeMockup:
        vue_code = "<template>VUE</template>"

    class FakeSession:
        session_id = "s1"
        spec_markdown = "SPEC"
        mockup_state = FakeMockup()

    state = build_graph_input(FakeSession())
    assert state["session_id"] == "s1"
    assert state["spec_markdown"] == "SPEC"
    assert state["confirmed_vue"] == "<template>VUE</template>"
    assert state["table_info"] == "TABLE_INFO"
    assert state["files"] == {}


def test_build_graph_input_handles_missing_mockup(monkeypatch):
    import app.llm.graph.sse_adapter as mod
    monkeypatch.setattr(mod.guides, "load_table_info", lambda: "T")

    class FakeSession:
        session_id = "s2"
        spec_markdown = "SPEC"
        mockup_state = None

    state = build_graph_input(FakeSession())
    assert state["confirmed_vue"] == ""
