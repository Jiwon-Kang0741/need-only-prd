"""Code generation router: plan, generate files, deploy & run, download ZIP."""

from __future__ import annotations

import io
import json
import logging
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.docker_manager import docker_manager
from app.llm.codegen_pipeline import codegen_pipeline
from app.llm.orchestrator import orchestrator
from app.llm.agents import QAEngineerAgent, _ensure_slf4j_service_impl, organize_imports
from app.models import CodeGenState
from app.pfy_local import (
    get_pfy_status,
    maven_compile_iter,
    parse_maven_build_errors,
    start_pfy_dev_servers,
    stop_pfy_processes,
    update_pfy_file_from_generated,
    write_generated_files_to_pfy,
)
from app.session import get_session_id, session_store

logger = logging.getLogger(__name__)
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

                # When complete: collect files, write to PFY, then notify client
                if event.get("type") == "complete":
                    # Collect final files from orchestrator
                    if hasattr(orchestrator, '_last_files'):
                        codegen_state.generated_files = orchestrator._last_files
                    if hasattr(orchestrator, '_last_agents'):
                        codegen_state.agents = orchestrator._last_agents

                    # Write to PFY workspace BEFORE sending complete event
                    if settings.CODEGEN_DEPLOY_MODE == "pfy" and codegen_state.generated_files:
                        try:
                            n = len(write_generated_files_to_pfy(codegen_state.generated_files))
                            logger.info("PFY: synced %d files after codegen", n)
                            yield _sse(type="log", line=f"[PFY] {n}개 파일을 워크스페이스에 저장했습니다.")
                        except Exception as exc:
                            logger.warning("PFY sync after codegen failed: %s", exc)
                            yield _sse(type="log", line=f"[PFY] 파일 저장 실패: {exc}")

                    codegen_state.status = "generated"
                    session_store.save(session.session_id)

                yield _sse(**event)

        except Exception as e:
            codegen_state.status = "error"
            codegen_state.error = str(e)
            session_store.save(session.session_id)
            yield _sse(type="error", message=str(e))

    return EventSourceResponse(event_stream(), ping=10)


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
        codegen_state = session.codegen
        codegen_state.status = "building"
        codegen_state.error = None

        logger.info("deploy event_stream started — mode=%s, files=%d",
                     settings.CODEGEN_DEPLOY_MODE, len(codegen_state.generated_files))

        try:
            if settings.CODEGEN_DEPLOY_MODE == "pfy":
                yield _sse("status", message="Writing generated files to PFY workspace...")
                try:
                    n = len(write_generated_files_to_pfy(codegen_state.generated_files))
                    yield _sse("log", line=f"[INFO] Wrote {n} file(s) to PFY backend/front.")
                except OSError as e:
                    codegen_state.status = "error"
                    codegen_state.error = str(e)
                    yield _sse("error", message=f"Failed to write PFY files: {e}")
                    return

                backend = Path(settings.PFY_BACKEND_DIR)
                max_retries = settings.DOCKER_MAX_FIX_RETRIES
                for attempt in range(1, max_retries + 2):
                    label = f" (attempt {attempt})" if attempt > 1 else ""
                    yield _sse("status", message=f"Maven compile{label}...")

                    build_logs: list[str] = []
                    rc: int | None = None
                    async for item in maven_compile_iter(backend):
                        if isinstance(item, int):
                            rc = item
                        else:
                            build_logs.append(item)
                            yield _sse("log", line=item)

                    if rc == 0:
                        break

                    if attempt > max_retries:
                        err_lines = [ln for ln in build_logs if "[ERROR]" in ln]
                        codegen_state.status = "error"
                        codegen_state.error = "\n".join(err_lines[-5:]) if err_lines else f"mvn compile failed ({rc})"
                        yield _sse("error", message=f"Build failed after {max_retries} auto-fix attempts.")
                        return

                    parsed_errors = parse_maven_build_errors(build_logs)
                    if not parsed_errors:
                        codegen_state.status = "error"
                        codegen_state.error = "Maven compile failed with unparseable errors"
                        yield _sse("error", message="Build failed. Check logs.")
                        return

                    yield _sse("status", message=f"Auto-fixing {len(parsed_errors)} file(s)...")
                    for err_info in parsed_errors:
                        err_file_path = err_info["file_path"]
                        err_text = err_info["errors"]
                        err_filename = err_file_path.replace("\\", "/").split("/")[-1]
                        matching = [
                            gf
                            for gf in codegen_state.generated_files
                            if gf.file_path.replace("\\", "/").endswith(err_filename)
                        ]
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

                        if target.file_type == "service_impl":
                            fixed_content = _ensure_slf4j_service_impl(fixed_content)
                        if target.file_path.endswith(".java"):
                            fixed_content = organize_imports(fixed_content)
                        target.content = fixed_content
                        update_pfy_file_from_generated(
                            codegen_state.generated_files,
                            err_file_path,
                            fixed_content,
                        )
                        yield _sse("log", line=f"[FIX] Fixed {target.file_path}")

                # Start dev servers (fire-and-forget in background task so we can
                # immediately signal the UI that the build succeeded)
                yield _sse("status", message="Build OK — starting dev servers in background...")
                from app.pfy_local import stop_pfy_processes as _stop, register_pfy_processes as _reg, _find_cmd as _fc, _popen_stream_thread as _pst, _maven_env as _menv
                import queue as _tq, threading as _threading, os as _os

                _stop(session.session_id)
                _front = Path(settings.PFY_FRONT_DIR)

                _fe_q: _tq.Queue = _tq.Queue()
                _npm_proc = _pst([_fc("npm"), "run", "dev"], str(_front), _os.environ.copy(), _fe_q)

                _be_q: _tq.Queue = _tq.Queue()
                _mvn_proc = _pst(
                    [_fc("mvn"), "spring-boot:run", "-Dspring-boot.run.arguments=--spring.profiles.active=local"],
                    str(backend), _menv(), _be_q,
                )
                _reg(session.session_id, _npm_proc, _mvn_proc)

                # Drain both queues in a background thread so logs flow without blocking
                def _drain_startup():
                    fe_done = be_done = False
                    while not (fe_done and be_done):
                        for _q, _name in ((_fe_q, "npm"), (_be_q, "mvn")):
                            try:
                                ln = _q.get_nowait()
                                if ln is None:
                                    if _name == "npm":
                                        fe_done = True
                                    else:
                                        be_done = True
                                else:
                                    logger.info("[PFY-START][%s] %s", _name, ln)
                            except _tq.Empty:
                                pass
                        import time
                        time.sleep(0.1)

                _threading.Thread(target=_drain_startup, daemon=True).start()

                # Immediately transition UI to running — don't wait for Spring Boot to be ready
                ports = {
                    "db": None,
                    "backend": settings.PFY_BACKEND_DEV_PORT,
                    "frontend": settings.PFY_FRONT_DEV_PORT,
                }
                codegen_state.status = "running"
                yield _sse("log", line=f"[INFO] npm run dev starting in {_front}")
                yield _sse("log", line=f"[INFO] mvn spring-boot:run starting in {backend}")
                yield _sse("log", line=f"[INFO] Frontend: http://localhost:{settings.PFY_FRONT_DEV_PORT}/")
                yield _sse("log", line=f"[INFO] Backend:  http://localhost:{settings.PFY_BACKEND_DEV_PORT}/")
                yield _sse("complete", message="Build OK — dev servers are starting",
                           status="running", containers=[], ports=ports, deploy_mode="pfy")
                return

            # --- Docker (CPMS skeleton) ---
            yield _sse("status", message="Checking Docker availability...")
            docker_ok, docker_msg = await docker_manager.check_docker_available()
            if not docker_ok:
                codegen_state.status = "error"
                codegen_state.error = docker_msg
                yield _sse("error", message=docker_msg)
                return

            yield _sse("status", message="Preparing CPMS skeleton project...")
            await docker_manager.write_workspace(
                session_id=session.session_id,
                files=codegen_state.generated_files,
            )

            max_retries = settings.DOCKER_MAX_FIX_RETRIES
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

                    if target.file_type == "service_impl":
                        fixed_content = _ensure_slf4j_service_impl(fixed_content)
                    if target.file_path.endswith(".java"):
                        fixed_content = organize_imports(fixed_content)
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
            logger.exception("deploy event_stream error")
            codegen_state.status = "error"
            codegen_state.error = str(e)
            yield _sse("error", message=f"Deploy error: {type(e).__name__}: {e}")

    return EventSourceResponse(event_stream(), ping=5)


# --------------------------------------------------------------- stop
@router.post("/stop")
async def stop_containers(session_id: str = Depends(get_session_id)):
    session = _get_session(session_id)
    if settings.CODEGEN_DEPLOY_MODE == "pfy":
        result = stop_pfy_processes(session.session_id)
    else:
        result = await docker_manager.stop(session.session_id)
    if session.codegen:
        session.codegen.status = "generated"
    return {"status": result}


# ------------------------------------------------------------- status
@router.get("/status")
async def container_status(session_id: str = Depends(get_session_id)):
    session = _get_session(session_id)
    if settings.CODEGEN_DEPLOY_MODE == "pfy":
        return get_pfy_status(session.session_id)
    return await docker_manager.get_status(session.session_id)


# ---------------------------------------------------- delete source
@router.post("/delete-source")
async def delete_source(session_id: str = Depends(get_session_id)):
    """Delete all generated files from disk (PFY workspace or skeleton) and reset session state."""
    session = _get_session(session_id)
    codegen = session.codegen

    deleted: list[str] = []
    if codegen and codegen.generated_files:
        if settings.CODEGEN_DEPLOY_MODE == "pfy":
            from app.pfy_local import resolve_pfy_destination
            for gf in codegen.generated_files:
                dest = resolve_pfy_destination(gf)
                if dest and dest.exists():
                    try:
                        dest.unlink()
                        deleted.append(dest.as_posix())
                        logger.info("[DELETE-SOURCE] Removed %s", dest)
                    except Exception as exc:
                        logger.warning("[DELETE-SOURCE] Could not remove %s: %s", dest, exc)
        else:
            # skeleton mode: remove the session workspace directory
            import shutil
            session_ws = docker_manager._workspace(session_id)
            if session_ws.exists():
                shutil.rmtree(session_ws, ignore_errors=True)
                deleted.append(str(session_ws))

        # Reset codegen state to idle
        codegen.generated_files = []
        codegen.status = "idle"
        codegen.plan = None
        codegen.error = None
        codegen.build_logs = []

    return {"deleted": len(deleted), "paths": deleted}


# --------------------------------------------------------- docker check
@router.get("/docker-check")
async def docker_check():
    """Check if Docker daemon is available and running."""
    if settings.CODEGEN_DEPLOY_MODE == "pfy":
        return {"available": True, "message": "PFY local deploy mode — Docker is not used."}
    ok, message = await docker_manager.check_docker_available()
    return {"available": ok, "message": message}
