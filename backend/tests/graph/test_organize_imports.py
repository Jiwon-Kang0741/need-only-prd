"""organize_imports word-boundary usage detection (F7). No LLM."""

from unittest.mock import patch

from app.llm.graph import deploy_fix


def _run(content):
    # allow java.* so the import isn't dropped for being undeclared
    with patch.object(deploy_fix, "get_allowed_import_prefixes",
                      return_value={"java", "biz"}), \
         patch.object(deploy_fix, "get_workspace_class_map", return_value={}):
        return deploy_fix.organize_imports(content)


def test_unused_import_dropped_despite_substring_match():
    # `List` appears only as a substring of `ArrayList` → import must be DROPPED
    src = ("package biz.t;\n\n"
           "import java.util.List;\n"
           "import java.util.ArrayList;\n\n"
           "public class T { ArrayList<String> x = new ArrayList<>(); }\n")
    out = _run(src)
    assert "import java.util.ArrayList;" in out
    assert "import java.util.List;" not in out


def test_genuinely_used_import_kept():
    src = ("package biz.t;\n\n"
           "import java.util.List;\n\n"
           "public class T { List<String> x; }\n")
    out = _run(src)
    assert "import java.util.List;" in out
