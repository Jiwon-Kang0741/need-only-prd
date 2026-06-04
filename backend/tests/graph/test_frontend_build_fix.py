"""parse_vite_errors — extract offending source paths from real vite build logs."""

from app.llm.graph.frontend_build_fix import parse_vite_errors


def test_parse_defineprops_error_names_vue_file():
    log = (
        "[vite:vue] [@vue/compiler-sfc] Unresolvable type reference\n\n"
        "/app/src/pages/cpms/edupgm/CpmsEduPgm/components/x/Foo.vue\n"
        "39 |  defineProps<Record<string, never>>();\n"
    )
    assert parse_vite_errors(log) == [
        "src/pages/cpms/edupgm/CpmsEduPgm/components/x/Foo.vue"]


def test_parse_scss_error_names_importer_vue():
    log = (
        "[vite:vue] Could not load ./Foo.scss?vue&type=style (imported by "
        "src/pages/cpms/edupgm/CpmsEduPgm/components/x/Foo.vue): ENOENT"
    )
    assert "src/pages/cpms/edupgm/CpmsEduPgm/components/x/Foo.vue" in parse_vite_errors(log)


def test_parse_dedupes_and_matches_ts():
    log = "/app/src/api/pages/a/types.ts bad\nagain /app/src/api/pages/a/types.ts\n"
    assert parse_vite_errors(log) == ["src/api/pages/a/types.ts"]


def test_parse_clean_log_is_empty():
    assert parse_vite_errors("✓ built in 1.29s\nBUILD SUCCESS") == []
