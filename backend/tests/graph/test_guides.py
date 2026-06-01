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
    (base / "BackendGuide" / "테이블정보.md").write_text(
        "## 테이블\nTB_X\n", encoding="utf-8"
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
