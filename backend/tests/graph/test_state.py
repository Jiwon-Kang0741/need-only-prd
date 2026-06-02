from app.llm.graph.state import merge_files, GeneratedFile


def test_merge_files_combines_disjoint_keys():
    left = {"a.java": {"file_path": "a.java", "file_type": "dto_request",
                       "layer": "backend", "wave": 1, "content": "A",
                       "status": "ok", "status_log": []}}
    right = {"b.java": {"file_path": "b.java", "file_type": "dao_impl",
                        "layer": "backend", "wave": 2, "content": "B",
                        "status": "ok", "status_log": []}}
    merged = merge_files(left, right)
    assert set(merged.keys()) == {"a.java", "b.java"}


def test_merge_files_right_wins_on_same_key():
    left = {"a.java": {"file_path": "a.java", "content": "OLD", "file_type": "x",
                       "layer": "backend", "wave": 1, "status": "ok", "status_log": []}}
    right = {"a.java": {"file_path": "a.java", "content": "NEW", "file_type": "x",
                        "layer": "backend", "wave": 1, "status": "ok", "status_log": []}}
    merged = merge_files(left, right)
    assert merged["a.java"]["content"] == "NEW"


def test_merge_files_handles_none_left():
    right = {"a.java": {"file_path": "a.java", "content": "A", "file_type": "x",
                        "layer": "backend", "wave": 1, "status": "ok", "status_log": []}}
    assert merge_files(None, right) == right


def test_generated_file_keys():
    gf: GeneratedFile = {"file_path": "x", "file_type": "dto_request",
                         "layer": "backend", "wave": 1, "content": "",
                         "status": "ok", "status_log": []}
    assert gf["wave"] == 1
