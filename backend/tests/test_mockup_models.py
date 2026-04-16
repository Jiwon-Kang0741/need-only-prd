from app.models import MockupState, SessionState, FieldOption, FieldDef


def test_mockup_state_defaults():
    state = MockupState(
        screen_id="MNET010",
        screen_name="신고 관리",
        page_type="list-detail",
        fields=[],
    )
    assert state.screen_id == "MNET010"
    assert state.vue_code is None
    assert state.annotations is None
    assert state.interview_questions is None
    assert state.current_step == 1


def test_mockup_state_full():
    state = MockupState(
        screen_id="MNET010",
        screen_name="신고 관리",
        page_type="list",
        fields=[{"key": "name", "label": "이름", "type": "text"}],
        vue_code="<template>...</template>",
        annotations=[{"id": "input-name", "type": "input"}],
        annotation_markdown="| id | type |\n|---|---|\n| input-name | input |",
        interview_questions=[{"no": 1, "question": "Q1"}],
        interview_answers=[{"no": 1, "answer": "A1"}],
        current_step=4,
    )
    assert state.current_step == 4
    assert len(state.fields) == 1
    assert state.vue_code is not None


def test_session_state_with_mockup():
    from datetime import datetime, timezone
    session = SessionState(
        session_id="test-123",
        created_at=datetime.now(timezone.utc),
        spec_source="mockup",
        mockup_state=MockupState(
            screen_id="MNET010",
            screen_name="테스트",
            page_type="list",
            fields=[],
        ),
    )
    assert session.spec_source == "mockup"
    assert session.mockup_state is not None
    assert session.mockup_state.screen_id == "MNET010"


def test_session_state_without_mockup():
    from datetime import datetime, timezone
    session = SessionState(
        session_id="test-456",
        created_at=datetime.now(timezone.utc),
    )
    assert session.spec_source is None
    assert session.mockup_state is None


def test_field_def_model():
    field = FieldDef(
        key="reportType",
        label="신고유형",
        type="select",
        searchable=True,
        listable=True,
        options=[
            FieldOption(label="전체", value=""),
            FieldOption(label="내부", value="INTERNAL"),
        ],
    )
    assert field.key == "reportType"
    assert len(field.options) == 2


def test_field_def_minimal():
    field = FieldDef(key="name", label="이름", type="text")
    assert field.searchable is False
    assert field.options is None
