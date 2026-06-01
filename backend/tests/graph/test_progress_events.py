"""Unit tests for wave_start/wave_complete/react_step event emission (no LLM)."""

from app.llm.graph import build


def _plan():
    return {"files": [
        {"file_path": "A.java", "file_type": "dto_request", "wave": 1},
        {"file_path": "T.ts", "file_type": "vue_types", "wave": 1},
        {"file_path": "D.java", "file_type": "dao_impl", "wave": 2},
        {"file_path": "S.java", "file_type": "service_impl", "wave": 3},
    ]}


def test_wave_gate_emits_complete_and_next_start():
    # finishing wave 1 -> complete(1) + start(2, 1 file)
    out = build._wave_gate({"current_wave": 1, "plan": _plan()})
    assert out["current_wave"] == 2
    types = [(e["type"], e["wave"]) for e in out["events"]]
    assert ("wave_complete", 1) in types
    assert ("wave_start", 2) in types
    start = next(e for e in out["events"] if e["type"] == "wave_start")
    assert start["file_count"] == 1


def test_wave_gate_last_wave_only_completes():
    # finishing wave 3 (MAX) -> only complete(3), no next start
    out = build._wave_gate({"current_wave": 3, "plan": _plan()})
    assert out["current_wave"] == 4
    types = [e["type"] for e in out["events"]]
    assert "wave_complete" in types
    assert "wave_start" not in types


def test_wave_gate_skips_empty_wave_start():
    # a plan with no wave-2 files: finishing wave 1 emits complete(1) but no start(2)
    plan = {"files": [{"file_path": "A.java", "file_type": "dto_request", "wave": 1},
                      {"file_path": "S.java", "file_type": "service_impl", "wave": 3}]}
    out = build._wave_gate({"current_wave": 1, "plan": plan})
    starts = [e for e in out["events"] if e["type"] == "wave_start"]
    assert starts == []
