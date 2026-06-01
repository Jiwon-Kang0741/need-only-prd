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


def test_validate_mybatis_binding_reviewer_only():
    from app.llm.graph.tools import TOOL_SPECS, REVIEWER_TOOL_SPECS
    assert "validate_mybatis_binding" not in {t["name"] for t in TOOL_SPECS}
    assert "validate_mybatis_binding" in {t["name"] for t in REVIEWER_TOOL_SPECS}


def test_dispatch_validate_mybatis_binding():
    from app.llm.graph.tools import dispatch_tool
    dao = """package p; public class FooDaoImpl extends B {
        public int x(X q){ return super.selectList("selectFoo", q); } }"""
    mapper = '<mapper namespace="p.WrongNs"><select id="selectBar">S</select></mapper>'
    files = {
        "a/FooDaoImpl.java": {"file_path": "a/FooDaoImpl.java", "file_type": "dao_impl",
                              "layer": "backend", "wave": 2, "status": "ok",
                              "status_log": [], "content": dao},
        "b/FooMapper.xml": {"file_path": "b/FooMapper.xml", "file_type": "mapper_xml",
                            "layer": "backend", "wave": 2, "status": "ok",
                            "status_log": [], "content": mapper},
    }
    result = dispatch_tool("validate_mybatis_binding", {}, files, {})
    assert isinstance(result, list)
    assert any(i.get("severity") == "error" for i in result)
