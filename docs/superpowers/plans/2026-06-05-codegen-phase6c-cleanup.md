# Codegen Rewrite — Phase 6c: Retire Old Path + Delete CODEGEN_RULES.md

> Cleanup phase. The new pipeline is LIVE (Phase 6b). This deletes the now-dead old path + the hand-maintained `CODEGEN_RULES.md`. The full non-LLM test suite is the green-gate oracle: after every deletion run `pytest -m "not llm" -q` and keep it green.

**Goal:** Remove dead code unreachable from the live graph (`build_graph` → contract_resolve/plan_and_bind/gen_nodes/generators/validators) and delete `pfy_prompt/CODEGEN_RULES.md` (the engine's old duplicate — NOT a guide). Leave a clean, green codebase for the user's real e2e.

**Iterative rule:** delete a chunk → `pytest -m "not llm" -q` → if a LIVE test breaks because a symbol was actually still used, RESTORE that symbol (it wasn't dead); if a test of DELETED code breaks, delete that test. Repeat until green. Never touch `BackendGuide/`/`FrontendGuide/`/`DataGuide/`, `.env`, `skeleton/`, or any new module (gen_*, contract_*, plan_and_bind, *_validate, guide_config, paths, gen_nodes).

## Live KEEP (never delete): 
new modules (gen_nodes, gen_backend, gen_frontend, gen_data, contract_resolve, plan_and_bind, backend_validate, frontend_validate, data_validate, contract_schema, guide_config, paths); shared utils (state, build[build_graph+make_checkpointer], sse_adapter, llm, prompts, _text, config); naming (all EXCEPT file_path/screen_segments); guides (load_guide_for_file_type, load_table_info, lookup_guide, _read_fresh, _split_by_headings, _guide_files, _FILE_TYPE_GUIDES, _LAYER_DIR, _INJECT_EXCLUDE, _reset_cache_for_test); tools.py (whole — validators use it); mybatis_check.py (tools.dispatch_tool references it — residual dead, keep); frontend_build_fix.py + deploy_fix.py (router uses them). Tests: test_backend_validate, test_build, test_checkpoint, test_contract_resolve, test_contract_schema, test_data_validate, test_deploy_fix, test_frontend_build_fix, test_frontend_validate, test_gen_*, test_graph_e2e_scripted, test_guide_config, test_llm, test_mybatis_check, test_paths, test_phase*, test_plan_and_bind, test_sse_adapter, test_sse_drain, test_state*, test_static_rules_restored, test_tools.

## DELETE — modules
- `pfy_prompt/CODEGEN_RULES.md`  (the old duplicate; NOT a guide)
- `backend/app/llm/graph/nodes.py`
- `backend/app/llm/graph/react.py`
- `backend/app/llm/graph/waves.py`
- `backend/app/llm/graph/frontend_ctx.py`
- `backend/app/llm/graph/cpms_checks.py`
- `backend/app/llm/graph/organize_imports.py`

## DELETE — tests (of deleted code)
test_nodes.py, test_derive_contract.py, test_nodes_robustness.py, test_react.py, test_react_open_issues.py, test_reviewer_applies.py, test_mybatis_node.py, test_progress_events.py, test_contract_injection.py, test_dep_context.py, test_frontend_archetype.py, test_package_enforce.py, test_waves.py, test_cpms_checks.py, test_organize_imports.py

## EDIT — prune dead, keep live
- `build.py`: delete `_route_waves`, `_wave_gate`, `mybatis_fix`; remove now-unused top imports (`nodes`, `react`, `waves` symbols, `mybatis_check`, `cpms_checks`, `check_forbidden_imports`, `Send`, and `logging`/`traceback` if unused). KEEP `build_graph` + `make_checkpointer` + their imports (`StateGraph`, `START`, `END`, `CodeGenState`).
- `guides.py`: delete `load_codegen_rules`, `load_path_templates` (+ `_PATHS_BLOCK_RE`, `_PATH_LINE_RE`), `load_named_frontend_guide`.
- `naming.py`: delete `file_path`, `screen_segments`, `_PASCAL_RE`. KEEP `statement_id`/`dao_method`/`mybatis_tag`/`dto_class`/`java_type`/`ops_for_screen_type`/`package_from_java_path`/`class_name_from_path`/`_OP_TABLE`/`_SCREEN_OPS`/`_TYPE_MAP`/`BASE_DAO_METHODS`.
- `tests/graph/test_naming.py`: remove tests of `file_path`/`screen_segments` only; keep the rest.
- `tests/graph/test_guides.py`: remove tests of `load_codegen_rules`/`load_path_templates`/`load_named_frontend_guide` only; keep `load_guide_for_file_type`/`load_table_info`/`lookup_guide` tests.
- `backend/app/routers/codegen.py` (trivial): line ~63 docstring "contract -> plan -> 3-wave -> reviewer" → "contract_resolve -> plan_and_bind -> gen_* -> validate".

## Verify
- `pytest -m "not llm" -q` GREEN after the cleanup.
- `grep -rn "CODEGEN_RULES\|load_codegen_rules\|load_path_templates\|naming.file_path\|screen_segments" backend/app` → empty (no live references).
- `test -f pfy_prompt/CODEGEN_RULES.md` → absent.
- Confirm `BackendGuide/`, `FrontendGuide/`, `DataGuide/` untouched (`git status` shows no changes under those).
- Commit.
