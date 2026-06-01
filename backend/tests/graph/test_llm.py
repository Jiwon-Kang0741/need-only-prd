from app.llm.graph.tools import TOOL_SPECS


def test_tool_specs_has_seven_tools():
    names = {t["name"] for t in TOOL_SPECS}
    assert names == {
        "static_check", "cross_check", "lookup_class",
        "get_dto_fields", "lookup_guide", "validate_sql", "list_generated_files",
    }


def test_tool_specs_responses_api_shape():
    for t in TOOL_SPECS:
        assert t["type"] == "function"
        assert "name" in t and "description" in t and "parameters" in t
        assert t["parameters"]["type"] == "object"


def test_gpt55_client_importable():
    from app.llm.graph.llm import gpt55_client, Gpt55Client
    assert isinstance(gpt55_client, Gpt55Client)
