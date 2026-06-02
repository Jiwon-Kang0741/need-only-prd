from datetime import datetime, timezone

from app.models import MockupState, SessionState


def test_mockup_state_minimal():
    s = MockupState(
        screen_id="CpmsTestLst",
        screen_name="테스트 목록",
        page_type="list",
        fields=[],
    )
    assert s.screen_id == "CpmsTestLst"
    assert s.screen_name == "테스트 목록"
    assert s.page_type == "list"
    assert s.vue_code is None
    assert s.raw_interview_text is None
    assert s.interview_note_md is None
    assert s.current_step == 1


def test_mockup_state_full():
    s = MockupState(
        screen_id="CpmsEduLst",
        screen_name="교육",
        page_type="list-detail",
        fields=[{"key": "a", "label": "A", "type": "text"}],
        vue_code="<template></template>",
        raw_interview_text="text...",
        interview_note_md="## Keep...",
        current_step=4,
    )
    assert s.current_step == 4
    assert s.interview_note_md == "## Keep..."


def test_mockup_state_ignores_unknown_extra_fields():
    """디스크에 남은 알 수 없는 키가 있어도 ValidationError 없이 무시."""
    s = MockupState.model_validate(
        {
            "screen_id": "X",
            "screen_name": "X",
            "page_type": "list",
            "fields": [],
            "legacy_project_id": "SHOULD_IGNORE",
            "brief_md": "ignored",
        }
    )
    assert s.screen_id == "X"
    assert not hasattr(s, "legacy_project_id")


def test_session_state_with_new_mockup():
    session = SessionState(
        session_id="t1",
        created_at=datetime.now(timezone.utc),
        spec_source="mockup",
        mockup_state=MockupState(
            screen_id="P1",
            screen_name="N1",
            page_type="list",
            fields=[],
        ),
    )
    assert session.spec_source == "mockup"
    assert session.mockup_state is not None
    assert session.mockup_state.screen_id == "P1"
