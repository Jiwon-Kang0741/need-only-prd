from app.llm.graph.frontend_validate import validate_frontend

_CONTRACT = {"identity": {"class_name": "CpmsEduPondgLst"}, "bindings": {"paths": {}}}


def _f(path, ft, content):
    return {path: {"file_path": path, "file_type": ft, "layer": "frontend", "content": content}}


def test_clean_setup_component_no_issues():
    files = _f("a/X.vue", "vue_searchform",
              '<script setup lang="ts">\nconst x = 1\n</script>\n<template><div/></template>')
    assert validate_frontend(files, _CONTRACT) == []


def test_flags_scrollheight_flex():
    files = _f("a/T.vue", "vue_datatable",
              '<script setup lang="ts"></script>\n<template><DataTable :columns="c" scrollHeight="flex"/></template>')
    issues = validate_frontend(files, _CONTRACT)
    assert any("flex" in i["issue"].lower() or "scrollheight" in i["issue"].lower() for i in issues)


def test_flags_alert_and_confirm():
    files = _f("a/X.vue", "vue_page",
               '<script setup lang="ts">\nfunction f(){ alert("x"); confirm("y"); }\n</script>')
    issues = validate_frontend(files, _CONTRACT)
    assert any("alert" in i["issue"].lower() for i in issues)
    assert any("confirm" in i["issue"].lower() for i in issues)


def test_flags_script_without_setup():
    files = _f("a/X.vue", "vue_page", '<script lang="ts">\nexport default {}\n</script>')
    issues = validate_frontend(files, _CONTRACT)
    assert any("setup" in i["issue"].lower() for i in issues)


def test_flags_datatable_column_children_without_columns_prop():
    files = _f("a/T.vue", "vue_datatable",
               '<script setup lang="ts"></script>\n<template><DataTable><Column field="a"/></DataTable></template>')
    issues = validate_frontend(files, _CONTRACT)
    assert any("column" in i["issue"].lower() and "prop" in i["issue"].lower() for i in issues)


def test_datatable_with_columns_prop_ok():
    files = _f("a/T.vue", "vue_datatable",
               '<script setup lang="ts"></script>\n<template><DataTable :columns="cols"/></template>')
    assert validate_frontend(files, _CONTRACT) == []
