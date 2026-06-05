import time
from pathlib import Path

import pytest

from app.llm.graph import guides


@pytest.fixture
def guide_dir(tmp_path, monkeypatch):
    base = tmp_path / "pfy_prompt"
    (base / "BackendGuide").mkdir(parents=True)
    (base / "FrontendGuide").mkdir(parents=True)
    (base / "BackendGuide" / "표준.md").write_text(
        "## DTO 표준\n원본 DTO 규칙\n## Service 표준\nsvc\n", encoding="utf-8"
    )
    (base / "FrontendGuide" / "03_SearchForm_구현.md").write_text(
        "## SearchForm\n검색폼 규칙\n", encoding="utf-8"
    )
    # non-rule files that must be EXCLUDED from injection
    (base / "FrontendGuide" / "README.md").write_text("README_MARKER\n", encoding="utf-8")
    (base / "FrontendGuide" / "자주_발생하는_에러.md").write_text(
        "DUP_ERR_MARKER\n", encoding="utf-8")
    (base / "FrontendGuide" / "13_공통컴포넌트_카탈로그.md").write_text(
        "CATALOG_MARKER\n", encoding="utf-8")
    (base / "BackendGuide" / "테이블정보.md").write_text(
        "## 테이블\nTB_X\n", encoding="utf-8"
    )
    (base / "CODEGEN_RULES.md").write_text(
        "# CODEGEN_RULES\n스파인 규칙\n", encoding="utf-8"
    )
    (base / "DataGuide").mkdir(parents=True)
    (base / "DataGuide" / "00.data_standard.md").write_text(
        "## 데이터 표준\n시드규칙X\n", encoding="utf-8"
    )
    monkeypatch.setattr(guides.settings, "PROMPT_REFERENCE_DIR", str(base))
    guides._reset_cache_for_test()
    return base


def test_load_backend_guide_returns_content(guide_dir):
    text = guides.load_guide_for_file_type("dto_request")
    assert "DTO 표준" in text
    assert "원본 DTO 규칙" in text


def test_load_frontend_guide_for_vue_page(guide_dir):
    text = guides.load_guide_for_file_type("vue_page")
    assert "SearchForm" in text or "검색폼" in text


def test_backend_loads_whole_backendguide_dir(guide_dir):
    # backend code must follow the WHOLE BackendGuide/ (not just 표준.md)
    text = guides.load_guide_for_file_type("dao_impl")
    assert "DTO 표준" in text   # 표준.md
    assert "TB_X" in text       # 테이블정보.md — proves whole-dir load


def test_db_init_sql_follows_dataguide(guide_dir):
    # data 관련 코드(db_init_sql)는 DataGuide/ 를 따라야 함
    text = guides.load_guide_for_file_type("db_init_sql")
    assert "시드규칙X" in text


def test_frontend_injection_excludes_non_rule_files(guide_dir):
    # README / 중복 에러문서 / 컴포넌트 카탈로그는 규칙이 아니므로 주입 제외
    text = guides.load_guide_for_file_type("vue_page")
    assert "검색폼 규칙" in text          # 03_SearchForm 은 포함
    assert "README_MARKER" not in text
    assert "DUP_ERR_MARKER" not in text
    assert "CATALOG_MARKER" not in text


def test_mtime_change_triggers_reload(guide_dir):
    first = guides.load_guide_for_file_type("dto_request")
    assert "원본 DTO 규칙" in first
    time.sleep(0.01)
    (guide_dir / "BackendGuide" / "표준.md").write_text(
        "## DTO 표준\n변경된 DTO 규칙\n", encoding="utf-8"
    )
    second = guides.load_guide_for_file_type("dto_request")
    assert "변경된 DTO 규칙" in second
    assert "원본 DTO 규칙" not in second


def test_lookup_guide_by_topic(guide_dir):
    text = guides.lookup_guide("backend", "Service 표준")
    assert "svc" in text


def test_load_table_info(guide_dir):
    text = guides.load_table_info()
    assert "TB_X" in text


def test_guide_files_glob_is_cached_by_dir_mtime(monkeypatch, tmp_path):
    # review #6: repeated calls must not re-glob when the directory is unchanged.
    from app.llm.graph import guides
    guides._reset_cache_for_test()
    d = tmp_path / "BackendGuide"
    d.mkdir()
    (d / "표준.md").write_text("hi", encoding="utf-8")
    monkeypatch.setattr(guides.settings, "PROMPT_REFERENCE_DIR", str(tmp_path))

    calls = {"n": 0}
    real_glob = guides.Path.glob
    def counting_glob(self, pat):
        calls["n"] += 1
        return real_glob(self, pat)
    monkeypatch.setattr(guides.Path, "glob", counting_glob)

    a = guides._guide_files("backend", "표준")
    b = guides._guide_files("backend", "표준")
    assert [p.name for p in a] == ["표준.md"] == [p.name for p in b]
    assert calls["n"] == 1            # second call served from cache (no re-glob)
