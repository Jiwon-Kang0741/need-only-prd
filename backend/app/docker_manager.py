"""Docker workspace management using CPMS skeleton project."""

from __future__ import annotations

import asyncio
import re
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

from app.config import settings
from app.models import GeneratedFile


# Port allocation
_next_port_offset = 0


def _allocate_ports() -> tuple[int, int, int]:
    global _next_port_offset
    base = 18000 + (_next_port_offset * 10)
    _next_port_offset += 1
    return base, base + 1, base + 2  # db, backend, frontend


class DockerManager:
    def __init__(self) -> None:
        self.workspace_base = Path(settings.DOCKER_WORKSPACE_DIR)
        self.workspace_base.mkdir(parents=True, exist_ok=True)
        self.skeleton_dir = Path(settings.PROMPT_REFERENCE_DIR).parent / "skeleton"
        self._ports: dict[str, tuple[int, int, int]] = {}

    def _workspace(self, session_id: str) -> Path:
        return self.workspace_base / session_id

    async def write_workspace(
        self,
        session_id: str,
        files: list[GeneratedFile],
    ) -> Path:
        """Copy skeleton + generated files to a workspace directory."""
        ws = self._workspace(session_id)
        if ws.exists():
            shutil.rmtree(ws)

        # Copy skeleton as base
        shutil.copytree(str(self.skeleton_dir), str(ws))

        # Allocate ports
        db_port, backend_port, frontend_port = _allocate_ports()
        self._ports[session_id] = (db_port, backend_port, frontend_port)

        # Write .env for docker-compose port variables
        (ws / ".env").write_text(
            f"DB_PORT={db_port}\nBACKEND_PORT={backend_port}\nFRONTEND_PORT={frontend_port}\n",
            encoding="utf-8",
        )

        # Ensure db/init.sql exists
        db_dir = ws / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        if not (db_dir / "init.sql").exists():
            (db_dir / "init.sql").write_text("-- auto-generated\n", encoding="utf-8")

        # Detect first vue_page to configure router
        module_code = ""
        category = ""
        screen_id_lower = ""

        # Write generated files into the skeleton
        for gf in files:
            # Strip tomms-lite-war/ or tomms-lite-front/ prefix if present
            fp = gf.file_path
            for prefix in ("tomms-lite-war/", "tomms-lite-front/", "tomms-biz-com/"):
                if fp.startswith(prefix):
                    fp = fp[len(prefix):]
                # Also handle nested: tomms-lite-war/tomms-biz-com/src/...
                combined = "tomms-lite-war/" + prefix
                if fp.startswith(combined):
                    fp = fp[len(combined):]

            if gf.layer == "backend":
                dest = ws / "backend" / fp
            else:
                dest = ws / "frontend" / fp

            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(gf.content, encoding="utf-8")

            # Detect page info for router
            if gf.file_type == "vue_page" and "/pages/" in gf.file_path and not module_code:
                parts = gf.file_path.split("/pages/")[-1].split("/")
                if len(parts) >= 3:
                    module_code = parts[0]
                    category = parts[1]
                    screen_id_lower = parts[2]

            # Write DB init SQL
            if gf.file_type == "db_init_sql":
                (db_dir / "init.sql").write_text(gf.content, encoding="utf-8")

        # Update frontend router to point to ALL generated pages
        vue_pages: list[tuple[str, str]] = []  # (route_path, file_path relative to src/)
        for gf in files:
            if gf.file_type == "vue_page" and "/pages/" in gf.file_path:
                # e.g. src/pages/sys/mnu/cpmsSysMnuLst/index.vue
                # or   tomms-lite-front/src/pages/sys/mnu/cpmsSysMnuLst/index.vue
                parts = gf.file_path.split("/pages/")
                if len(parts) == 2:
                    page_rel = parts[1]  # sys/mnu/cpmsSysMnuLst/index.vue
                    # Route path from folder name
                    folders = page_rel.split("/")
                    if len(folders) >= 3:
                        route_name = folders[-2]  # cpmsSysMnuLst
                        # Reconstruct the @/pages/... import path
                        import_path = f"@/pages/{page_rel}"
                        vue_pages.append((f"/{route_name}", import_path))

        if vue_pages:
            route_entries = []
            for i, (route_path, import_path) in enumerate(vue_pages):
                # First page is also the root route
                if i == 0:
                    route_entries.append(f"  {{ path: '/', component: () => import('{import_path}') }}")
                route_entries.append(f"  {{ path: '{route_path}', component: () => import('{import_path}') }}")

            router_content = (
                "import { createRouter, createWebHistory } from 'vue-router'\n\n"
                "const routes = [\n"
                + ",\n".join(route_entries) + "\n"
                "]\n\n"
                "export default createRouter({\n"
                "  history: createWebHistory(),\n"
                "  routes,\n"
                "})\n"
            )
            router_file = ws / "frontend" / "src" / "router" / "index.ts"
            router_file.parent.mkdir(parents=True, exist_ok=True)
            router_file.write_text(router_content, encoding="utf-8")

        # Auto-generate empty SCSS files referenced by Vue components
        fe_dir = ws / "frontend"
        for gf in files:
            if gf.layer == "frontend" and gf.file_path.endswith(".vue"):
                for m in re.finditer(r"""(?:@import|from)\s+['"](.+?\.scss)['"]""", gf.content):
                    scss_ref = m.group(1)
                    if scss_ref.startswith("./") or scss_ref.startswith("../"):
                        vue_dir = (fe_dir / gf.file_path).parent
                        scss_path = (vue_dir / scss_ref).resolve()
                        if not scss_path.exists():
                            scss_path.parent.mkdir(parents=True, exist_ok=True)
                            scss_path.write_text("/* auto-generated stub */\n", encoding="utf-8")

        # Auto-generate stub files for missing @/ imports
        generated_fe_paths: set[str] = set()
        for gf in files:
            if gf.layer == "frontend":
                generated_fe_paths.add(gf.file_path)

        all_at_imports: set[str] = set()
        for gf in files:
            if gf.layer == "frontend":
                for m in re.finditer(r"""from\s+['"]@/(.+?)['"]""", gf.content):
                    all_at_imports.add(m.group(1))
                for m in re.finditer(r"""import\(\s*['"]@/(.+?)['"]""", gf.content):
                    all_at_imports.add(m.group(1))

        fe_src = fe_dir / "src"
        for imp_path in all_at_imports:
            src_path = f"src/{imp_path}"
            already_exists = any(fp == src_path or fp.startswith(src_path) for fp in generated_fe_paths)
            if already_exists:
                continue

            stub_file = fe_src / imp_path
            # Check if it already exists in skeleton
            extensions = ["", ".ts", ".js", ".vue", "/index.ts", "/index.js"]
            exists_in_skeleton = any((fe_src / f"{imp_path}{ext}").exists() for ext in extensions)
            if exists_in_skeleton:
                continue

            if stub_file.suffix == ".vue":
                stub_file.parent.mkdir(parents=True, exist_ok=True)
                comp_name = stub_file.stem
                stub_file.write_text(
                    f"<template>\n  <div><!-- {comp_name} stub --></div>\n</template>\n\n"
                    f"<script setup lang=\"ts\">\n</script>\n",
                    encoding="utf-8",
                )
            elif stub_file.suffix in (".ts", ".js"):
                stub_file.parent.mkdir(parents=True, exist_ok=True)
                stub_file.write_text("export default {};\n", encoding="utf-8")
            else:
                for ext_path in [fe_src / f"{imp_path}.ts", fe_src / imp_path / "index.ts"]:
                    if not ext_path.exists():
                        ext_path.parent.mkdir(parents=True, exist_ok=True)
                        ext_path.write_text("export default {};\n", encoding="utf-8")
                        break

        return ws

    async def build_and_run(self, session_id: str) -> AsyncIterator[str]:
        """Run docker compose up --build, streaming logs."""
        ws = self._workspace(session_id)
        if not ws.exists():
            yield "[ERROR] Workspace not found"
            return

        ports = self._ports.get(session_id)
        if ports:
            yield f"[INFO] Ports — DB:{ports[0]}, Backend:{ports[1]}, Frontend:{ports[2]}"

        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "up", "--build", "-d",
            cwd=str(ws),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        assert proc.stdout is not None
        while True:
            try:
                line = await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=settings.DOCKER_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                yield "[ERROR] Build timed out"
                proc.kill()
                break
            if not line:
                break
            yield line.decode("utf-8", errors="replace").rstrip("\n")

        await proc.wait()
        if proc.returncode == 0:
            yield "[SUCCESS] Containers started"
        else:
            yield f"[ERROR] docker compose exited with code {proc.returncode}"

    async def get_status(self, session_id: str) -> dict:
        """Check running container status and ports."""
        ws = self._workspace(session_id)
        if not ws.exists():
            return {"status": "no_workspace"}

        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "ps", "--format", "json",
            cwd=str(ws),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return {"status": "error", "containers": []}

        import json
        containers = []
        for line in stdout.decode().strip().splitlines():
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        running = any(
            c.get("State") == "running" or c.get("Status", "").startswith("Up")
            for c in containers
        )

        ports = self._ports.get(session_id)
        return {
            "status": "running" if running else "stopped",
            "containers": containers,
            "ports": {
                "db": ports[0] if ports else None,
                "backend": ports[1] if ports else None,
                "frontend": ports[2] if ports else None,
            },
        }

    async def stop(self, session_id: str) -> str:
        """Stop and remove containers."""
        ws = self._workspace(session_id)
        if not ws.exists():
            return "no_workspace"

        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "down", "--remove-orphans", "-v",
            cwd=str(ws),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await proc.communicate()
        return "stopped"

    def parse_build_errors(self, build_logs: list[str]) -> list[dict]:
        """Extract compilation errors from Maven build logs."""
        errors_by_file: dict[str, list[str]] = {}
        current_file = None

        for line in build_logs:
            m = re.search(r"\[ERROR\]\s+/app/(src/main/java/\S+\.java):\[(\d+),\d+\]\s+(.*)", line)
            if m:
                current_file = m.group(1)
                error_msg = f"Line {m.group(2)}: {m.group(3)}"
                errors_by_file.setdefault(current_file, []).append(error_msg)
                continue

            m2 = re.search(r"\[ERROR\]\s+symbol:\s+(.*)", line)
            if m2 and current_file:
                errors_by_file[current_file].append(f"  symbol: {m2.group(1)}")

            m3 = re.search(r"\[ERROR\]\s+location:\s+(.*)", line)
            if m3 and current_file:
                errors_by_file[current_file].append(f"  location: {m3.group(1)}")

        return [
            {"file_path": fp, "errors": "\n".join(errs)}
            for fp, errs in errors_by_file.items()
        ]

    def update_file_in_workspace(self, session_id: str, file_path: str, content: str) -> None:
        """Write updated file content to the workspace. Searches by filename if exact path not found."""
        import time
        ws = self._workspace(session_id)

        # Try exact path first
        dest = ws / "backend" / file_path
        if not dest.parent.exists():
            # Search by filename in backend/src/
            filename = file_path.split("/")[-1]
            backend_src = ws / "backend" / "src"
            candidates = list(backend_src.rglob(filename)) if backend_src.exists() else []
            if candidates:
                dest = candidates[0]
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)

        dest.write_text(content, encoding="utf-8")

        # Bust Docker cache by touching a marker file
        cache_bust = ws / "backend" / "src" / ".cache_bust"
        cache_bust.write_text(str(time.time()), encoding="utf-8")

    async def cleanup(self, session_id: str) -> None:
        """Stop containers and remove workspace directory."""
        await self.stop(session_id)
        ws = self._workspace(session_id)
        if ws.exists():
            shutil.rmtree(ws, ignore_errors=True)


docker_manager = DockerManager()
