"""Multi-agent orchestrator: async generator that yields SSE events."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable

logger = logging.getLogger(__name__)

from app.llm.agents import (
    BackendEngineerAgent,
    BackendQAAgent,
    DataEngineerAgent,
    FixAgent,
    FrontendEngineerAgent,
    FrontendQAAgent,
    PlannerAgent,
    QAEngineerAgent,
    SharedContext,
    _post_fix_cross_check,
    organize_imports_for_files,
    postprocess_backend_files,
    static_check,
)
from app.models import AgentStatus, GeneratedFile


class CodeGenOrchestrator:
    """Orchestrates multi-agent code generation as an async generator."""

    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.data_engineer = DataEngineerAgent()
        self.backend_engineer = BackendEngineerAgent()
        self.frontend_engineer = FrontendEngineerAgent()
        self.backend_qa = BackendQAAgent()
        self.frontend_qa = FrontendQAAgent()
        self.fix_agent = FixAgent()
        self.qa_engineer = QAEngineerAgent()  # kept for deploy auto-fix
        # Store last results for router to collect
        self._last_files: list[GeneratedFile] = []
        self._last_agents: list[AgentStatus] = []

    async def run(
        self,
        spec_markdown: str,
        increment_llm_calls: Callable[[], None],
    ) -> AsyncIterator[dict]:
        """Run multi-agent pipeline, yielding SSE events."""
        ctx = SharedContext(spec_markdown=spec_markdown)
        agent_statuses: list[AgentStatus] = []

        # ------------------------------------------------------------------
        # Phase 1: Planner
        # ------------------------------------------------------------------
        planner_status = AgentStatus(role="planner", display_name="Planner", status="running")
        agent_statuses.append(planner_status)
        yield {"type": "agent_start", "agent": "planner", "display_name": "Planner"}
        yield {"type": "status", "message": "Planner analyzing spec..."}

        increment_llm_calls()
        try:
            plan = await self.planner.execute(ctx)
        except Exception as e:
            logger.exception("Planner failed")
            yield {"type": "error", "message": f"Planner failed: {e}"}
            return
        yield {"type": "plan", "plan": plan.model_dump()}

        planner_status.status = "completed"
        planner_status.files_count = len(plan.files)
        yield {"type": "agent_complete", "agent": "planner", "files_count": len(plan.files)}

        # ------------------------------------------------------------------
        # Phase 2: Data Engineer
        # ------------------------------------------------------------------
        data_status = AgentStatus(role="data_engineer", display_name="Data Engineer", status="running")
        agent_statuses.append(data_status)
        yield {"type": "agent_start", "agent": "data_engineer", "display_name": "Data Engineer"}

        data_files = self.data_engineer._get_my_files(plan)
        for f in data_files:
            increment_llm_calls()
        yield {"type": "status", "message": f"Data Engineer generating {len(data_files)} file(s)..."}

        # Data Engineer runs sequentially, collect chunks
        data_results = await self.data_engineer.execute(ctx)

        data_status.status = "completed"
        data_status.files_count = len(data_results)
        for gf in data_results:
            yield {"type": "file_complete", "agent": "data_engineer", "file_path": gf.file_path,
                   "file_type": gf.file_type, "layer": gf.layer, "content": gf.content}
        yield {"type": "agent_complete", "agent": "data_engineer", "files_count": len(data_results)}

        # ------------------------------------------------------------------
        # Phase 3: Backend + Frontend (parallel)
        # ------------------------------------------------------------------
        be_status = AgentStatus(role="backend_engineer", display_name="Backend Engineer", status="running")
        fe_status = AgentStatus(role="frontend_engineer", display_name="Frontend Engineer", status="running")
        agent_statuses.extend([be_status, fe_status])

        be_files = self.backend_engineer._get_my_files(plan)
        fe_files = self.frontend_engineer._get_my_files(plan)
        for _ in be_files:
            increment_llm_calls()
        for _ in fe_files:
            increment_llm_calls()

        yield {"type": "agent_start", "agent": "backend_engineer", "display_name": "Backend Engineer"}
        yield {"type": "agent_start", "agent": "frontend_engineer", "display_name": "Frontend Engineer"}
        yield {"type": "status", "message": f"Backend Engineer generating {len(be_files)} file(s)..."}
        be_results = await self.backend_engineer.execute(ctx)

        for gf in be_results:
            yield {"type": "file_complete", "agent": "backend_engineer", "file_path": gf.file_path,
                   "file_type": gf.file_type, "layer": gf.layer, "content": gf.content}

        be_status.status = "completed"
        be_status.files_count = len(be_results)
        yield {"type": "agent_complete", "agent": "backend_engineer", "files_count": len(be_results)}

        yield {"type": "status", "message": f"Frontend Engineer generating {len(fe_files)} file(s)..."}
        fe_results = await self.frontend_engineer.execute(ctx)

        fe_status.status = "completed"
        fe_status.files_count = len(fe_results)

        for gf in fe_results:
            yield {"type": "file_complete", "agent": "frontend_engineer", "file_path": gf.file_path,
                   "file_type": gf.file_type, "layer": gf.layer, "content": gf.content}
        yield {"type": "agent_complete", "agent": "frontend_engineer", "files_count": len(fe_results)}

        # ------------------------------------------------------------------
        # Phase 3.5: Backend Cross-File Consistency Check (no LLM)
        # ALWAYS runs after backend generation regardless of LLM output.
        # Programmatically adds missing DAO methods and DTO fields so that
        # ServiceImpl never references something that doesn't exist.
        # ------------------------------------------------------------------
        yield {"type": "status", "message": "Cross-checking backend file consistency (DTO ↔ DAO ↔ Service)..."}
        try:
            pre_qa_repairs = _post_fix_cross_check(ctx)
            if pre_qa_repairs:
                for repair in pre_qa_repairs:
                    fp = repair.get("file_path", "")
                    fc = repair.get("content", "")
                    if not fp or not fc:
                        continue
                    for path, gf in ctx.generated_files.items():
                        if path == fp or fp.endswith(gf.file_path):
                            gf.content = fc
                            yield {"type": "log", "line": f"[CROSS-CHECK] Auto-repaired {gf.file_path}"}
                            yield {"type": "file_complete", "agent": "backend_engineer",
                                   "file_path": gf.file_path, "file_type": gf.file_type,
                                   "layer": gf.layer, "content": gf.content}
                            break
                yield {"type": "log", "line": f"[CROSS-CHECK] {len(pre_qa_repairs)} file(s) auto-repaired before QA"}
            else:
                yield {"type": "log", "line": "[CROSS-CHECK] All backend files consistent — no repairs needed"}
        except Exception as e:
            logger.exception("[CROSS-CHECK] CRITICAL: pre-QA cross-check FAILED — %s", e)
            yield {"type": "log", "line": f"[CROSS-CHECK] ERROR: cross-check failed: {e}"}

        # ------------------------------------------------------------------
        # Phase 3.6: Static Check (no LLM)
        # ------------------------------------------------------------------
        try:
            static_issues = static_check(list(ctx.generated_files.values()))
        except Exception as e:
            logger.exception("[STATIC] CRITICAL: static_check FAILED — %s", e)
            yield {"type": "log", "line": f"[STATIC] ERROR: static_check failed: {e}"}
            static_issues = []
        if static_issues:
            for iss in static_issues:
                yield {"type": "log", "line": f"[STATIC] {iss['file_path']}: {iss['issue']}"}

        # ------------------------------------------------------------------
        # Phase 4: Backend QA + Frontend QA (parallel)
        # ------------------------------------------------------------------
        be_qa_status = AgentStatus(role="backend_qa", display_name="Backend QA", status="running")
        fe_qa_status = AgentStatus(role="frontend_qa", display_name="Frontend QA", status="running")
        agent_statuses.extend([be_qa_status, fe_qa_status])

        yield {"type": "agent_start", "agent": "backend_qa", "display_name": "Backend QA"}
        yield {"type": "agent_start", "agent": "frontend_qa", "display_name": "Frontend QA"}
        yield {"type": "status", "message": "Backend QA + Frontend QA reviewing code..."}

        increment_llm_calls()
        increment_llm_calls()

        try:
            backend_issues, frontend_issues = await asyncio.gather(
                self.backend_qa.execute(ctx),
                self.frontend_qa.execute(ctx),
            )
        except Exception as e:
            logger.exception("QA agents failed")
            backend_issues, frontend_issues = [], []
            yield {"type": "log", "line": f"[QA] Error: {e}"}

        be_qa_status.status = "completed"
        fe_qa_status.status = "completed"
        be_qa_status.files_count = len(backend_issues)
        fe_qa_status.files_count = len(frontend_issues)

        yield {"type": "agent_complete", "agent": "backend_qa", "files_count": len(backend_issues)}
        yield {"type": "agent_complete", "agent": "frontend_qa", "files_count": len(frontend_issues)}

        for iss in backend_issues:
            yield {"type": "log", "line": f"[Backend QA] {iss.get('file_path', '')}: {iss.get('issue', '')}"}
        for iss in frontend_issues:
            yield {"type": "log", "line": f"[Frontend QA] {iss.get('file_path', '')}: {iss.get('issue', '')}"}

        # ------------------------------------------------------------------
        # Phase 5: Fix Agent (if issues found)
        # ------------------------------------------------------------------
        all_issues = static_issues + backend_issues + frontend_issues

        if all_issues:
            fix_status = AgentStatus(role="fix_agent", display_name="Fix Agent", status="running")
            agent_statuses.append(fix_status)
            yield {"type": "agent_start", "agent": "fix_agent", "display_name": "Fix Agent"}
            yield {"type": "status", "message": f"Fix Agent resolving {len(all_issues)} issue(s)..."}

            increment_llm_calls()
            try:
                fixes = await self.fix_agent.execute(ctx, all_issues)
            except Exception as e:
                logger.exception("Fix agent failed")
                fixes = []
                yield {"type": "log", "line": f"[FIX] Error: {e}"}

            for fix in fixes:
                fp = fix.get("file_path", "")
                fc = fix.get("content", "")
                if not fp or not fc:
                    continue
                for path, gf in ctx.generated_files.items():
                    if path == fp or fp.endswith(gf.file_path):
                        gf.content = fc
                        yield {"type": "log", "line": f"[FIX] Fixed {gf.file_path}"}
                        yield {"type": "file_complete", "agent": "fix_agent", "file_path": gf.file_path,
                               "file_type": gf.file_type, "layer": gf.layer, "content": gf.content}
                        break

            fix_status.status = "completed"
            fix_status.files_count = len(fixes)
            yield {"type": "agent_complete", "agent": "fix_agent", "files_count": len(fixes)}
        else:
            yield {"type": "log", "line": "[QA] No issues found — skipping Fix Agent"}

        # ------------------------------------------------------------------
        # Phase 6: Final Backend Validation (no LLM)
        # 1. Cross-check again (Fix Agent may have introduced new mismatches)
        # 2. Postprocess + organize imports
        # 3. Static check for any remaining issues
        # ------------------------------------------------------------------
        yield {"type": "status", "message": "Running final backend validation..."}

        # 6a. Cross-file consistency check (catches Fix Agent regressions)
        try:
            final_repairs = _post_fix_cross_check(ctx)
            if final_repairs:
                for repair in final_repairs:
                    fp = repair.get("file_path", "")
                    fc = repair.get("content", "")
                    if not fp or not fc:
                        continue
                    for path, gf in ctx.generated_files.items():
                        if path == fp or fp.endswith(gf.file_path):
                            gf.content = fc
                            yield {"type": "log", "line": f"[FINAL REPAIR] Auto-repaired {gf.file_path}"}
                            yield {"type": "file_complete", "agent": "fix_agent",
                                   "file_path": gf.file_path, "file_type": gf.file_type,
                                   "layer": gf.layer, "content": gf.content}
                            break
                yield {"type": "log", "line": f"[FINAL REPAIR] {len(final_repairs)} file(s) auto-repaired in final pass"}
        except Exception as e:
            logger.exception("[FINAL REPAIR] CRITICAL: post-fix cross-check FAILED — %s", e)
            yield {"type": "log", "line": f"[FINAL REPAIR] ERROR: cross-check failed: {e}"}

        # 6b. Postprocess + organize imports
        try:
            backend_files = [gf for gf in ctx.generated_files.values() if gf.layer == "backend"]
            if backend_files:
                postprocess_backend_files(backend_files)
                organize_imports_for_files(backend_files)
                for gf in backend_files:
                    ctx.generated_files[gf.file_path] = gf
        except Exception as e:
            logger.exception("[FINAL] CRITICAL: postprocess/organize_imports FAILED — %s", e)
            yield {"type": "log", "line": f"[FINAL] ERROR: postprocess failed: {e}"}

        # 6c. Final static check
        try:
            final_issues = static_check(list(ctx.generated_files.values()))
        except Exception as e:
            logger.exception("[FINAL CHECK] CRITICAL: final static_check FAILED — %s", e)
            yield {"type": "log", "line": f"[FINAL CHECK] ERROR: static_check failed: {e}"}
            final_issues = []

        if final_issues:
            for iss in final_issues:
                yield {"type": "log", "line": f"[FINAL CHECK] {iss.get('file_path', '')}: {iss.get('issue', '')}"}
            yield {"type": "log", "line": f"[FINAL CHECK] {len(final_issues)} remaining issue(s) detected after fix"}
        else:
            yield {"type": "log", "line": "[FINAL CHECK] All backend files passed validation"}

        # ------------------------------------------------------------------
        # Complete
        # ------------------------------------------------------------------
        all_files = list(ctx.generated_files.values())
        self._last_files = all_files
        self._last_agents = agent_statuses

        yield {"type": "complete", "message": f"All {len(all_files)} files generated by {len(agent_statuses)} agents", "total": len(all_files)}


orchestrator = CodeGenOrchestrator()
