"""Frontend build-error auto-fix loop.

Compiles the generated Vue app with the REAL toolchain (vite) and feeds compiler
errors back to gpt-5.5 to fix, retrying until the build is clean or a cap is hit.
The compiler is the correctness oracle — no hardcoded Vue rules. Mirrors the
backend's maven auto-fix loop (deploy_fix.fix_build_error + codegen.py).
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from app.config import settings
from app.llm.graph.llm import gpt55_client
from app.llm.graph._text import strip_fences as _strip_fences

# Workspace-relative source file named in a vite/rollup error (strip the in-container
# /app/ prefix; match both "/app/src/..vue" lines and "(imported by src/..vue)").
_VITE_FILE_RE = re.compile(r"(?:/app/)?(src/[^\s:?'\"]+\.(?:vue|ts))")


def parse_vite_errors(logs: str) -> list[str]:
    """Return the unique workspace-relative source paths named in a vite build log."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _VITE_FILE_RE.finditer(logs or ""):
        p = m.group(1)
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


_FE_FIX_SYSTEM = (
    "You are fixing a Vue 3 + TypeScript build error reported by vite / "
    "@vue/compiler-sfc. Output ONLY the complete corrected file content — no markdown "
    "fences, no explanation.\n\n"
    "RULES:\n"
    "- Fix the reported error; preserve all working behavior, props, emits, template, "
    "imports that resolve.\n"
    "- Use <script setup lang=\"ts\">.\n"
    "- defineProps/defineEmits MUST be Vue-SFC-compilable: call each AT MOST ONCE per "
    "file; if the component has no props, OMIT defineProps entirely; do NOT use utility "
    "types (e.g. Record<string, never>) as the defineProps type argument — use an inline "
    "object literal type or a local interface.\n"
    "- Do NOT invent modules/imports that don't exist."
)


async def fix_frontend_build_error(error_log: str, file_path: str, file_content: str) -> str:
    """Ask gpt-5.5 to fix one Vue/TS file given the vite build error."""
    user = (
        f"Build error:\n```\n{error_log[:4000]}\n```\n\n"
        f"File: {file_path}\n```vue\n{file_content}\n```\n\n"
        "Output the complete fixed file."
    )
    resp = await gpt55_client.complete(_FE_FIX_SYSTEM, user, max_tokens=settings.CODEGEN_MAX_TOKENS)
    return _strip_fences(resp)


async def build_frontend_once(frontend_dir: str) -> tuple[int, str]:
    """Run `npm install && vite build` in a node container; return (returncode, logs)."""
    proc = await asyncio.create_subprocess_exec(
        "docker", "run", "--rm", "-v", f"{frontend_dir}:/app", "-w", "/app",
        "node:18-alpine", "sh", "-c",
        "npm install --no-audit --no-fund --loglevel=error && npm run build",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return proc.returncode, out.decode("utf-8", "replace")


async def run_frontend_build_fix(frontend_dir: str, max_retries: int | None = None):
    """Build → on error, gpt-5.5-fix each offending file → rebuild, until clean or cap.

    Yields (kind, text) tuples: ('log', line) and finally ('result', 'ok'|'failed').
    """
    retries = settings.DOCKER_MAX_FIX_RETRIES if max_retries is None else max_retries
    fdir = Path(frontend_dir)
    logs = ""
    for attempt in range(1, retries + 2):
        rc, logs = await build_frontend_once(frontend_dir)
        if rc == 0:
            yield ("result", "ok")
            return
        if attempt > retries:
            break
        offenders = parse_vite_errors(logs)
        yield ("log", f"[FE-FIX] build failed (attempt {attempt}); fixing {len(offenders)} file(s)")
        fixed_any = False
        for rel in offenders:
            f = fdir / rel
            if not f.exists():
                continue
            try:
                fixed = await fix_frontend_build_error(logs, rel, f.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001 — surface, keep looping
                yield ("log", f"[FE-FIX] {rel} fix error: {e}")
                continue
            if fixed and fixed.strip():
                f.write_text(fixed, encoding="utf-8")
                fixed_any = True
                yield ("log", f"[FE-FIX] fixed {rel}")
        if not fixed_any:
            break
    yield ("result", "failed")
