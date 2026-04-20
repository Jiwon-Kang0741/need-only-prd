from datetime import datetime, timezone

from app.models import MockupState, SessionState


def test_mockup_state_minimal():
    s = MockupState(project_id="ETHICS_REPORT", project_name="윤리경영")
    assert s.project_id == "ETHICS_REPORT"
    assert s.project_name == "윤리경영"
    assert s.brief_md is None
    assert s.mockup_vue is None
    assert s.raw_interview_text is None
    assert s.interview_notes_md is None
    assert s.current_step == 1


def test_mockup_state_full():
    s = MockupState(
        project_id="EDU_PROG",
        project_name="교육",
        brief_md="# Brief",
        mockup_vue="<template>...</template>",
        raw_interview_text="text...",
        interview_notes_md="## Keep...",
        current_step=4,
    )
    assert s.current_step == 4
    assert s.brief_md == "# Brief"


def test_mockup_state_ignores_legacy_fields():
    """기존 디스크 세션에 screen_id, fields 등 구 필드가 있어도 ValidationError 없이 무시."""
    s = MockupState(
        project_id="X",
        project_name="X",
        screen_id="SHOULD_IGNORE",       # legacy
        fields=[{"a": 1}],                # legacy
        annotations=None,                  # legacy
    )
    assert s.project_id == "X"
    # 필드 자체가 모델에 없어야 함 (extra="ignore"로 누락 처리)
    assert not hasattr(s, "screen_id") or getattr(s, "screen_id", None) is None


def test_session_state_with_new_mockup():
    session = SessionState(
        session_id="t1",
        created_at=datetime.now(timezone.utc),
        spec_source="mockup",
        mockup_state=MockupState(project_id="P1", project_name="N1"),
    )
    assert session.spec_source == "mockup"
    assert session.mockup_state.project_id == "P1"
