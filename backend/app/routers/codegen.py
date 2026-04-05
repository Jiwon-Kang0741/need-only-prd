"""Code generation router: plan, generate files, deploy & run, download ZIP."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.docker_manager import docker_manager
from app.llm.codegen_pipeline import codegen_pipeline
from app.llm.orchestrator import orchestrator
from app.llm.agents import QAEngineerAgent
from app.models import CodeGenState, GeneratedFile
from app.session import get_session_id, session_store

router = APIRouter(prefix="/codegen", tags=["codegen"])


def _get_session(session_id: str):
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


def _ensure_codegen(session) -> CodeGenState:
    if session.codegen is None:
        session.codegen = CodeGenState()
    return session.codegen


def _sse(type: str, **kwargs) -> dict:
    """Build SSE message in the same format as other routers."""
    return {"event": "message", "data": json.dumps({"type": type, **kwargs})}


# -------------------------------------------------------------- generate
@router.post("/generate")
async def generate_code(session_id: str = Depends(get_session_id)):
    """Multi-agent code generation: Planner → Data → Backend+Frontend (parallel) → QA."""
    session = _get_session(session_id)
    if not session.spec_markdown:
        raise HTTPException(400, "No spec generated yet")

    async def event_stream():
        codegen_state = _ensure_codegen(session)
        codegen_state.status = "generating"
        codegen_state.error = None
        codegen_state.generated_files = []
        codegen_state.agents = []

        try:
            async for event in orchestrator.run(
                spec_markdown=session.spec_markdown,
                increment_llm_calls=lambda: session_store.increment_llm_calls(session.session_id),
            ):
                # Update plan in session when received
                if event.get("type") == "plan" and "plan" in event:
                    from app.models import CodeGenPlan, CodeGenPlanFile
                    plan_data = event["plan"]
                    codegen_state.plan = CodeGenPlan(
                        module_code=plan_data.get("module_code", ""),
                        screen_code=plan_data.get("screen_code", ""),
                        files=[CodeGenPlanFile(**f) for f in plan_data.get("files", [])],
                    )

                # Store generated files when complete
                if event.get("type") == "complete":
                    codegen_state.status = "generated"

                yield _sse(**event)

            # Collect final files from orchestrator
            if hasattr(orchestrator, '_last_files'):
                codegen_state.generated_files = orchestrator._last_files
            if hasattr(orchestrator, '_last_agents'):
                codegen_state.agents = orchestrator._last_agents

            # Persist session to disk
            session_store.save(session.session_id)

        except Exception as e:
            codegen_state.status = "error"
            codegen_state.error = str(e)
            session_store.save(session.session_id)
            yield _sse(type="error", message=str(e))

    return EventSourceResponse(event_stream())


# --------------------------------------------------------------- files
@router.get("/files")
async def get_generated_files(
    layer: str | None = None,
    session_id: str = Depends(get_session_id),
):
    session = _get_session(session_id)
    codegen = session.codegen
    if not codegen:
        return {"files": []}

    files = codegen.generated_files
    if layer:
        files = [f for f in files if f.layer == layer]

    return {
        "files": [
            {
                "file_path": f.file_path,
                "file_type": f.file_type,
                "content": f.content,
                "layer": f.layer,
            }
            for f in files
        ]
    }


# -------------------------------------------------------------- download
@router.get("/download")
async def download_code(session_id: str = Depends(get_session_id)):
    session = _get_session(session_id)
    codegen = session.codegen
    if not codegen or not codegen.generated_files:
        raise HTTPException(400, "No generated files")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for gf in codegen.generated_files:
            # Organize by layer: backend/ or frontend/
            archive_path = f"{gf.layer}/{gf.file_path}"
            zf.writestr(archive_path, gf.content)

    buf.seek(0)
    screen_code = codegen.plan.screen_code if codegen.plan else "generated"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={screen_code}-code.zip"},
    )


# ----------------------------------------------------------- deploy & run
@router.post("/deploy")
async def deploy_and_run(session_id: str = Depends(get_session_id)):
    session = _get_session(session_id)
    codegen = session.codegen
    if not codegen or not codegen.generated_files:
        raise HTTPException(400, "No generated files. Run /codegen/generate first.")

    async def event_stream():
        from app.config import settings as cfg

        codegen_state = session.codegen
        codegen_state.status = "building"
        codegen_state.error = None

        try:
            # Write skeleton + generated files to workspace
            yield _sse("status", message="Preparing CPMS skeleton project...")
            await docker_manager.write_workspace(
                session_id=session.session_id,
                files=codegen_state.generated_files,
            )

            max_retries = cfg.DOCKER_MAX_FIX_RETRIES
            for attempt in range(1, max_retries + 2):
                label = f" (attempt {attempt})" if attempt > 1 else ""
                yield _sse("status", message=f"Building & starting containers{label}...")

                build_logs: list[str] = []
                async for log_line in docker_manager.build_and_run(session.session_id):
                    build_logs.append(log_line)
                    yield _sse("log", line=log_line)

                # Check for compilation errors
                has_build_error = any("[ERROR]" in log for log in build_logs)
                if not has_build_error:
                    break

                if attempt > max_retries:
                    error_lines = [l for l in build_logs if "[ERROR]" in l]
                    codegen_state.status = "error"
                    codegen_state.error = "\n".join(error_lines[-5:])
                    yield _sse("error", message=f"Build failed after {max_retries} auto-fix attempts.")
                    return

                # Auto-fix
                parsed_errors = docker_manager.parse_build_errors(build_logs)
                if not parsed_errors:
                    codegen_state.status = "error"
                    codegen_state.error = "Build failed with unparseable errors"
                    yield _sse("error", message="Build failed. Check logs.")
                    return

                yield _sse("status", message=f"Auto-fixing {len(parsed_errors)} file(s)...")
                for err_info in parsed_errors:
                    err_file_path = err_info["file_path"]
                    err_text = err_info["errors"]

                    err_filename = err_file_path.split("/")[-1]
                    matching = [gf for gf in codegen_state.generated_files
                                if gf.file_path.endswith(err_filename)]
                    if not matching:
                        yield _sse("log", line=f"[WARN] Cannot find source for {err_file_path}")
                        continue

                    target = matching[0]
                    yield _sse("log", line=f"[FIX] Fixing {target.file_path}...")

                    session_store.increment_llm_calls(session.session_id)
                    qa = QAEngineerAgent()
                    fixed_content = await qa.fix_file(
                        error_log=err_text,
                        file_path=target.file_path,
                        file_content=target.content,
                        all_files=codegen_state.generated_files,
                    )

                    target.content = fixed_content
                    docker_manager.update_file_in_workspace(
                        session.session_id, err_file_path, fixed_content
                    )
                    yield _sse("log", line=f"[FIX] Fixed {target.file_path}")

                await docker_manager.stop(session.session_id)

            # Check container status
            status = await docker_manager.get_status(session.session_id)
            if status["status"] == "running":
                codegen_state.status = "running"
                yield _sse("complete", message="Containers running", **status)
            else:
                codegen_state.status = "error"
                codegen_state.error = "Containers failed to start"
                yield _sse("error", message="Containers failed to start. Check logs.")

        except Exception as e:
            codegen_state.status = "error"
            codegen_state.error = str(e)
            yield _sse("error", message=str(e))

    return EventSourceResponse(event_stream())


# --------------------------------------------------------------- stop
@router.post("/stop")
async def stop_containers(session_id: str = Depends(get_session_id)):
    session = _get_session(session_id)
    result = await docker_manager.stop(session.session_id)
    if session.codegen:
        session.codegen.status = "generated"
    return {"status": result}


# ------------------------------------------------------------- status
@router.get("/status")
async def container_status(session_id: str = Depends(get_session_id)):
    session = _get_session(session_id)
    status = await docker_manager.get_status(session.session_id)
    return status
