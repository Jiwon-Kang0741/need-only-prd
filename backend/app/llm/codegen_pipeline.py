"""Code generation pipeline: spec.md -> source files -> Docker config."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from app.config import settings
from app.llm.client import codex_client
from app.llm.codegen_context import get_context_for_file_type, get_naming_context
from app.llm.codegen_prompts import (
    codegen_docker_prompt,
    codegen_file_prompt,
    codegen_fix_prompt,
    codegen_plan_prompt,
    codegen_review_prompt,
)
from app.models import CodeGenPlan, CodeGenPlanFile, DockerConfig, GeneratedFile


class CodeGenPipeline:
    async def plan_files(self, spec_markdown: str) -> CodeGenPlan:
        """Analyze spec.md and produce an ordered file generation plan."""
        system, user = codegen_plan_prompt(spec_markdown)
        response = await codex_client.complete(system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS)

        # Strip markdown fences if present
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        plan = CodeGenPlan(
            module_code=data.get("module_code", ""),
            screen_code=data.get("screen_code", ""),
            files=[CodeGenPlanFile(**f) for f in data.get("files", [])],
        )
        return plan

    async def generate_file(
        self,
        spec_markdown: str,
        plan: CodeGenPlan,
        file_index: int,
        previously_generated: list[GeneratedFile],
    ) -> AsyncIterator[str]:
        """Generate a single source file with streaming."""
        file_entry = plan.files[file_index]
        file_type = file_entry.file_type

        # Get relevant guide context for this file type
        guide_context = get_context_for_file_type(file_type)
        naming_context = get_naming_context()

        # Collect dependent files
        depends_on = set(file_entry.depends_on)
        dependent_files = []
        for gf in previously_generated:
            if gf.file_path in depends_on:
                dependent_files.append({"file_path": gf.file_path, "content": gf.content})

        # If no explicit depends_on but we have prior files of the same layer,
        # include the most recent few for context (up to 3)
        if not dependent_files and previously_generated:
            same_layer = [gf for gf in previously_generated if gf.layer == file_entry.layer]
            for gf in same_layer[-3:]:
                dependent_files.append({"file_path": gf.file_path, "content": gf.content})

        system, user = codegen_file_prompt(
            spec_markdown=spec_markdown,
            guide_context=guide_context,
            naming_context=naming_context,
            file_plan_entry=file_entry.model_dump(),
            dependent_files=dependent_files,
        )

        stream = await codex_client.complete(
            system, user, stream=True, max_tokens=settings.CODEGEN_MAX_TOKENS
        )
        async for chunk in stream:
            yield chunk

    async def generate_docker_config(
        self,
        spec_markdown: str,
        plan: CodeGenPlan,
        generated_files: list[GeneratedFile],
    ) -> DockerConfig:
        """Generate Docker/docker-compose configuration."""
        file_list = [gf.file_path for gf in generated_files]
        system, user = codegen_docker_prompt(
            spec_markdown=spec_markdown,
            module_code=plan.module_code,
            screen_code=plan.screen_code,
            file_list=file_list,
        )
        response = await codex_client.complete(
            system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS
        )

        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        return DockerConfig(**data)


    async def review_and_fix(
        self,
        generated_files: list[GeneratedFile],
    ) -> list[dict]:
        """Review all files for cross-file consistency and return fixes.

        Returns list of {"file_path": str, "content": str} for files that need fixing.
        """
        all_files = [
            {"file_path": gf.file_path, "content": gf.content}
            for gf in generated_files
        ]

        system, user = codegen_review_prompt(all_files)
        response = await codex_client.complete(
            system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS
        )

        text = response.strip()
        if text.startswith("```"):
            first_nl = text.index("\n") if "\n" in text else 3
            text = text[first_nl + 1:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()

        try:
            data = json.loads(text)
            return data.get("fixes", [])
        except (json.JSONDecodeError, KeyError):
            return []

    async def fix_file(
        self,
        error_log: str,
        file_path: str,
        file_content: str,
        all_files: list[GeneratedFile],
    ) -> str:
        """Fix compilation errors in a generated file using LLM."""
        # Gather related files (same package / same layer)
        related = []
        file_dir = "/".join(file_path.split("/")[:-1])
        for gf in all_files:
            if gf.file_path != file_path and (
                gf.file_path.startswith(file_dir) or
                # Also include DTOs referenced in errors
                any(part in error_log for part in gf.file_path.split("/")[-1:])
            ):
                related.append({"file_path": gf.file_path, "content": gf.content})

        # Limit related files to avoid token overflow
        related = related[:5]

        system, user = codegen_fix_prompt(
            error_log=error_log,
            file_path=file_path,
            file_content=file_content,
            related_files=related,
        )
        response = await codex_client.complete(
            system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS
        )

        # Strip markdown fences if present
        text = response.strip()
        if text.startswith("```"):
            first_nl = text.index("\n") if "\n" in text else 3
            text = text[first_nl + 1:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()

        return text


codegen_pipeline = CodeGenPipeline()
