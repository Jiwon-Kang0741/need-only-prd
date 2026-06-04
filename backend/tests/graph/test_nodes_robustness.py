"""contract_extract retry-parse guard (F4) + gate failed status (F5). No LLM."""

import pytest

from app.llm.graph import nodes

pytestmark = pytest.mark.asyncio


class _Client:
    def __init__(self, replies):
        self._replies = replies
        self._i = 0
        self.last_user = None
    async def complete(self, system, user, max_tokens=16384):
        self.last_user = user
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


_DAO_PATH = "src/main/java/hsc/tomms/web/cpms/edursltlst/dao/CpmsEduRsltLstDaoImpl.java"


async def test_generate_file_enforces_package_from_path(monkeypatch):
    # LLM declares a wrong package; the node must rewrite it to match the path
    monkeypatch.setattr(nodes, "gpt55_client", _Client([
        "package com.example.bad.dao;\nclass CpmsEduRsltLstDaoImpl "
        "{ private String id; }"]))
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "G")
    spec = {"file_path": _DAO_PATH, "file_type": "dao_impl", "layer": "backend",
            "class_name": "CpmsEduRsltLstDaoImpl", "description": "d", "wave": 2}
    out = await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    content = out["files"][_DAO_PATH]["content"]
    assert "package hsc.tomms.web.cpms.edursltlst.dao;" in content
    assert "com.example.bad" not in content


async def test_vue_page_expands_local_child_components(monkeypatch):
    # index.vue imports local child components → the node must GENERATE those files
    # (at the resolved path) so the multi-file structure actually exists.
    index_vue = (
        '<template>\n  <CpmsFooSearchForm @search="x" />\n</template>\n'
        '<script setup lang="ts">\n'
        "import CpmsFooSearchForm from './components/cpmsFooSearchForm/CpmsFooSearchForm.vue';\n"
        "import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue';\n"
        "</script>\n"
    )
    component_vue = '<template><div/></template>\n<script setup lang="ts"></script>\n'
    client = _Client([index_vue, component_vue])
    monkeypatch.setattr(nodes, "gpt55_client", client)
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "G")
    monkeypatch.setattr(nodes.guides, "load_codegen_rules", lambda: "")
    monkeypatch.setattr(nodes.guides, "load_named_frontend_guide", lambda prefix: "FEGUIDE")
    spec = {"file_path": "src/pages/cpms/foo/CpmsFoo/index.vue", "file_type": "vue_page",
            "layer": "frontend", "class_name": "CpmsFoo", "description": "d", "wave": 2}
    out = await nodes.generate_file({"contract": {}, "files": {}, "spec_markdown": "",
                                     "plan": {}, "_file_spec": spec})
    comp = "src/pages/cpms/foo/CpmsFoo/components/cpmsFooSearchForm/CpmsFooSearchForm.vue"
    assert comp in out["files"]
    assert out["files"][comp]["file_type"] == "vue_component"
    assert out["files"][comp]["layer"] == "frontend"
    # alias (@/) imports are NOT expanded (skeleton-provided)
    assert not any("ContentHeader" in p for p in out["files"])
    # the generated component set makes index.vue's local imports resolve
    from app.llm.graph.cpms_checks import check_frontend_local_imports
    assert check_frontend_local_imports(out["files"]) == []


async def test_db_init_sql_does_not_double_inject_dataguide(monkeypatch):
    # DataGuide now arrives via the layer guide (whole DataGuide/); the old
    # get_dataguide_data_engineer_excerpt() injection is redundant and removed.
    client = _Client(["CREATE TABLE x (id varchar);"])
    monkeypatch.setattr(nodes, "gpt55_client", client)
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type",
                        lambda ft: "DATAGUIDE_VIA_GUIDE")
    monkeypatch.setattr(nodes.guides, "load_codegen_rules", lambda: "")
    spec = {"file_path": "db/init.sql", "file_type": "db_init_sql", "layer": "backend",
            "class_name": "", "description": "d", "wave": 1}
    await nodes.generate_file({"contract": {}, "files": {},
                               "spec_markdown": "", "_file_spec": spec})
    assert "DATAGUIDE_VIA_GUIDE" in client.last_user          # guide still injected
    assert "=== DATA SEED GUIDE ===" not in client.last_user  # redundant excerpt gone


async def test_generate_file_injects_codegen_rules_spine(monkeypatch):
    # A 방식: CODEGEN_RULES.md spine must be injected into every generate_file prompt
    client = _Client(["class A { private String id; }"])
    monkeypatch.setattr(nodes, "gpt55_client", client)
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "G")
    monkeypatch.setattr(nodes.guides, "load_codegen_rules", lambda: "SPINE_RULES_MARKER")
    spec = {"file_path": "A.java", "file_type": "dto_request", "layer": "backend",
            "class_name": "A", "description": "d", "wave": 1}
    await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    assert "SPINE_RULES_MARKER" in client.last_user


async def test_generate_file_prompt_grounds_target_package(monkeypatch):
    # the generator prompt must state the canonical package so imports are correct
    client = _Client(["package x;\nclass CpmsEduRsltLstDaoImpl { private String id; }"])
    monkeypatch.setattr(nodes, "gpt55_client", client)
    monkeypatch.setattr(nodes.guides, "load_guide_for_file_type", lambda ft: "G")
    spec = {"file_path": _DAO_PATH, "file_type": "dao_impl", "layer": "backend",
            "class_name": "CpmsEduRsltLstDaoImpl", "description": "d", "wave": 2}
    await nodes.generate_file({"contract": {}, "files": {}, "_file_spec": spec})
    assert "hsc.tomms.web.cpms.edursltlst.dao" in client.last_user
