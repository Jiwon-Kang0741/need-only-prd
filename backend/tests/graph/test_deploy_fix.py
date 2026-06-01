"""Deterministic post-processing tests for deploy_fix (no LLM)."""

from app.llm.graph.deploy_fix import ensure_slf4j_service_impl, postprocess_fixed_file


def test_ensure_slf4j_injects_annotation_and_import():
    src = "package biz.edu;\n\n@Service\npublic class FooServiceImpl {}\n"
    out = ensure_slf4j_service_impl(src)
    assert "@Slf4j" in out
    assert "import lombok.extern.slf4j.Slf4j;" in out


def test_ensure_slf4j_strips_old_logger():
    src = (
        "package biz.edu;\n"
        "import org.slf4j.Logger;\n"
        "import org.slf4j.LoggerFactory;\n"
        "@Service\npublic class FooServiceImpl {\n"
        "  private static final Logger log = LoggerFactory.getLogger(FooServiceImpl.class);\n"
        "}\n"
    )
    out = ensure_slf4j_service_impl(src)
    assert "LoggerFactory" not in out
    assert "import org.slf4j.Logger;" not in out
    assert "@Slf4j" in out


def test_ensure_slf4j_idempotent():
    src = ("package biz.edu;\n\nimport lombok.extern.slf4j.Slf4j;\n\n"
           "@Slf4j\n@Service\npublic class FooServiceImpl {}\n")
    out = ensure_slf4j_service_impl(src)
    assert out.count("@Slf4j") == 1
    assert out.count("import lombok.extern.slf4j.Slf4j;") == 1


def test_postprocess_non_java_is_noop():
    content = "SELECT * FROM x;"
    assert postprocess_fixed_file("db/init.sql", "db_init_sql", content) == content
