import pytest

from app.llm.graph.waves import wave_for_file_type, files_in_wave, MAX_WAVE


def test_wave_assignment_is_fixed():
    assert wave_for_file_type("db_init_sql") == 1
    assert wave_for_file_type("dto_request") == 1
    assert wave_for_file_type("dto_response") == 1
    assert wave_for_file_type("vue_types") == 1
    assert wave_for_file_type("dao_impl") == 2
    assert wave_for_file_type("mapper_xml") == 2
    assert wave_for_file_type("vue_page") == 2
    assert wave_for_file_type("service_impl") == 3


def test_max_wave_is_three():
    assert MAX_WAVE == 3


def test_unknown_file_type_defaults_to_last_wave():
    # safest: unknown types run last so they can see everything
    assert wave_for_file_type("mystery") == 3


def test_files_in_wave_filters_plan():
    plan = {"files": [
        {"file_path": "A.java", "file_type": "dto_request"},
        {"file_path": "B.java", "file_type": "dao_impl"},
        {"file_path": "C.java", "file_type": "service_impl"},
    ]}
    wave1 = files_in_wave(plan, 1)
    assert [f["file_path"] for f in wave1] == ["A.java"]
    wave3 = files_in_wave(plan, 3)
    assert [f["file_path"] for f in wave3] == ["C.java"]
