"""PFY local workspace integration.

Handles writing generated files to the PFY Spring Boot + Vue3 workspace,
running Maven compile, and managing local dev-server processes.
Only used when CODEGEN_DEPLOY_MODE == "pfy".
"""

from __future__ import annotations

import asyncio
import logging
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path
from typing import AsyncIterator

from app.config import settings
from app.models import GeneratedFile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Process registry  (session_id → [Popen, ...])
# ---------------------------------------------------------------------------

_PROCS: dict[str, list[subprocess.Popen]] = {}


def register_pfy_processes(session_id: str, *procs: subprocess.Popen) -> None:
    _PROCS.setdefault(session_id, []).extend(procs)


def stop_pfy_processes(session_id: str) -> str:
    procs = _PROCS.pop(session_id, [])
    for p in procs:
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    return "stopped" if procs else "idle"


def get_pfy_status(session_id: str) -> dict:
    procs = _PROCS.get(session_id, [])
    running = any(p.poll() is None for p in procs)
    return {
        "status": "running" if running else "idle",
        "containers": [],
        "ports": {
            "db": None,
            "backend": settings.PFY_BACKEND_DEV_PORT,
            "frontend": settings.PFY_FRONT_DEV_PORT,
        },
        "deploy_mode": "pfy",
    }


# ---------------------------------------------------------------------------
# File destination resolution
# ---------------------------------------------------------------------------

def _strip_prefix(fp: str, *prefixes: str) -> str:
    """Remove the first matching prefix from fp."""
    for prefix in prefixes:
        if fp.startswith(prefix):
            return fp[len(prefix):]
    return fp


def resolve_pfy_destination(gf: GeneratedFile) -> Path | None:
    """Map a GeneratedFile to its destination path in the PFY workspace.

    Planner generates full relative paths like:
      src/main/java/biz/edu/dao/CpmsEduDaoImpl.java
      src/main/resources/biz/edu/mybatis/mappers/CpmsEduMapper.xml
    We strip the known prefix so they land under PFY_BACKEND_DIR correctly.
    """
    fp = gf.file_path.replace("\\", "/")

    if gf.layer == "backend":
        base = Path(settings.PFY_BACKEND_DIR)
        if fp.endswith(".java"):
            # Strip leading src/main/java/ variants; keep the biz/... relative path
            rel = _strip_prefix(fp,
                                 "src/main/java/",
                                 "main/java/",
                                 "java/")
            return base / "src" / "main" / "java" / rel
        if fp.endswith(".xml"):
            rel = _strip_prefix(fp,
                                 "src/main/resources/",
                                 "main/resources/",
                                 "resources/")
            return base / "src" / "main" / "resources" / rel
        if fp.endswith(".sql"):
            rel = _strip_prefix(fp,
                                 "src/main/resources/",
                                 "main/resources/",
                                 "resources/")
            return base / "src" / "main" / "resources" / rel
    elif gf.layer == "frontend":
        fp_rel = _strip_prefix(fp, "src/")
        base = Path(settings.PFY_FRONT_DIR) / "src"
        return base / fp_rel

    return None


def write_generated_files_to_pfy(files: list[GeneratedFile]) -> list[Path]:
    """Write generated files to the PFY workspace. Returns list of written paths."""
    written: list[Path] = []
    for gf in files:
        dest = resolve_pfy_destination(gf)
        if dest is None:
            logger.warning("[PFY] No destination for %s", gf.file_path)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(gf.content, encoding="utf-8")
        logger.info("[PFY] Wrote %s", dest)
        written.append(dest)
    return written


def update_pfy_file_from_generated(
    files: list[GeneratedFile],
    file_path: str,
    fixed_content: str,
) -> None:
    """Update a single file on disk after auto-fix."""
    filename = file_path.replace("\\", "/").split("/")[-1]
    for gf in files:
        if gf.file_path.replace("\\", "/").endswith(filename):
            dest = resolve_pfy_destination(gf)
            if dest and dest.exists():
                dest.write_text(fixed_content, encoding="utf-8")
                logger.info("[PFY] Updated %s", dest)
            return


# ---------------------------------------------------------------------------
# Maven build
# ---------------------------------------------------------------------------

def _maven_env() -> dict[str, str]:
    env = os.environ.copy()
    java_home = env.get("JAVA_HOME", "")
    if java_home:
        env["PATH"] = str(Path(java_home) / "bin") + os.pathsep + env.get("PATH", "")
    return env


def _find_cmd(name: str) -> str:
    found = shutil.which(name)
    return found or name


def _popen_stream_thread(
    cmd: list[str],
    cwd: str,
    env: dict,
    out_queue: queue.Queue,
) -> subprocess.Popen:
    """Start a subprocess and stream its stdout/stderr to out_queue in a thread."""
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    def _reader():
        assert proc.stdout is not None
        for line in proc.stdout:
            out_queue.put(line.rstrip())
        out_queue.put(None)  # sentinel

    threading.Thread(target=_reader, daemon=True).start()
    return proc


async def maven_compile_iter(backend_dir: Path) -> AsyncIterator[str | int]:
    """Async generator that yields log lines (str) then return code (int)."""
    env = _maven_env()
    mvn = _find_cmd("mvn")
    out_q: queue.Queue = queue.Queue()

    proc = _popen_stream_thread([mvn, "compile", "-q"], str(backend_dir), env, out_q)

    loop = asyncio.get_event_loop()
    while True:
        item = await loop.run_in_executor(None, out_q.get)
        if item is None:
            break
        yield item  # type: ignore[misc]

    rc = await loop.run_in_executor(None, proc.wait)
    yield rc  # type: ignore[misc]


def parse_maven_build_errors(build_logs: list[str]) -> list[dict]:
    """Parse Maven [ERROR] lines into {file_path, errors} dicts."""
    import re

    errors: dict[str, list[str]] = {}
    file_re = re.compile(r"\[ERROR\]\s+(.+\.java):\[(\d+),(\d+)\]")

    for line in build_logs:
        m = file_re.search(line)
        if m:
            fp = m.group(1).replace("\\", "/")
            errors.setdefault(fp, []).append(line.strip())

    return [{"file_path": fp, "errors": "\n".join(msgs)} for fp, msgs in errors.items()]


# ---------------------------------------------------------------------------
# Dev servers  (kept for API compatibility; orchestration is done inline in router)
# ---------------------------------------------------------------------------

def start_pfy_dev_servers(session_id: str) -> None:
    """Start npm run dev + mvn spring-boot:run for the PFY project."""
    stop_pfy_processes(session_id)

    front = Path(settings.PFY_FRONT_DIR)
    backend = Path(settings.PFY_BACKEND_DIR)
    env = _maven_env()

    fe_q: queue.Queue = queue.Queue()
    npm_proc = _popen_stream_thread([_find_cmd("npm"), "run", "dev"], str(front), os.environ.copy(), fe_q)

    be_q: queue.Queue = queue.Queue()
    mvn_proc = _popen_stream_thread(
        [_find_cmd("mvn"), "spring-boot:run", "-Dspring-boot.run.arguments=--spring.profiles.active=local"],
        str(backend), env, be_q,
    )

    register_pfy_processes(session_id, npm_proc, mvn_proc)
    logger.info("[PFY] Dev servers started for session %s", session_id)
