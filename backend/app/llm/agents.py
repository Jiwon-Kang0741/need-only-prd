"""Multi-agent code generation: specialized agents for each role."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.config import settings
from app.llm.client import codex_client, llm_client
from app.llm.codegen_context import (
    get_all_backend_guide,
    get_all_frontend_guide,
    get_naming_context,
)
from app.models import CodeGenPlan, CodeGenPlanFile, GeneratedFile


# ---------------------------------------------------------------------------
# Static Check (no LLM, regex-based)
# ---------------------------------------------------------------------------

_BACKEND_CHECKS = [
    (re.compile(r'import\s+java\.util\.UUID'), "java.util.UUID import found — use String for ID fields"),
    (re.compile(r'javaType\s*=\s*["\']?java\.util\.UUID'), "UUID javaType in Mapper XML — use java.lang.String"),
    (re.compile(r'@Service\s*\(\s*"[^"]+"\s*\)'), "@Service with bean name — use bare @Service without parameter"),
]

_FRONTEND_CHECKS = [
    (re.compile(r'scrollHeight\s*=\s*["\']flex["\']'), 'scrollHeight="flex" found — use scrollHeight="540px" with virtualScrollerOptions'),
    (re.compile(r'<script(?!\s+setup)[\s>]'), '<script> without setup — must use <script setup lang="ts">'),
    (re.compile(r'\balert\s*\('), 'alert() found — use Toast component instead'),
    (re.compile(r'\bconfirm\s*\('), 'confirm() found — use ConfirmDialog instead'),
]


def static_check(files: list[GeneratedFile]) -> list[dict]:
    """Run regex-based static checks on generated files. No LLM calls."""
    issues: list[dict] = []
    for gf in files:
        checks = _BACKEND_CHECKS if gf.layer == "backend" else _FRONTEND_CHECKS
        for pattern, message in checks:
            if pattern.search(gf.content):
                issues.append({
                    "file_path": gf.file_path,
                    "issue": f"[STATIC] {message}",
                    "fix_instruction": message.split(" — ")[-1] if " — " in message else message,
                })
    return issues


# ---------------------------------------------------------------------------
# Shared context between agents
# ---------------------------------------------------------------------------

@dataclass
class SharedContext:
    spec_markdown: str
    plan: CodeGenPlan | None = None
    generated_files: dict[str, GeneratedFile] = field(default_factory=dict)
    data_contracts: str = ""   # types.ts content from Data Engineer
    db_schema: str = ""        # SQL from Data Engineer


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------

AGENT_METAS = [
    {"role": "planner", "display_name": "Planner", "description": "요구사항 분석 + 파일 생성 계획"},
    {"role": "data_engineer", "display_name": "Data Engineer", "description": "DB 스키마 + TypeScript 타입 + Mock 데이터 생성"},
    {"role": "backend_engineer", "display_name": "Backend Engineer", "description": "Service, DAO, Mapper XML, DTO 구현"},
    {"role": "frontend_engineer", "display_name": "Frontend Engineer", "description": "Vue3 페이지, 컴포넌트, API, Store 구현"},
    {"role": "backend_qa", "display_name": "Backend QA", "description": "백엔드 가이드 기반 코드 검증"},
    {"role": "frontend_qa", "display_name": "Frontend QA", "description": "프론트엔드 가이드 기반 코드 검증"},
    {"role": "fix_agent", "display_name": "Fix Agent", "description": "QA 이슈 기반 코드 수정"},
]


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        first_nl = text.index("\n") if "\n" in text else 3
        text = text[first_nl + 1:]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3].rstrip()
    return text


# ---------------------------------------------------------------------------
# Planner Agent
# ---------------------------------------------------------------------------

class PlannerAgent:
    role = "planner"

    async def execute(self, ctx: SharedContext) -> CodeGenPlan:
        naming = get_naming_context()
        backend_guide = get_all_backend_guide()[:50000]
        frontend_guide = get_all_frontend_guide()[:50000]

        system = (
            "You are a code architect that plans file generation for a CPMS Spring Boot + Vue3 project.\n"
            "Given a technical specification (spec.md), produce an ordered list of source files to generate.\n\n"
            f"--- NAMING CONVENTIONS ---\n{naming}\n--- END ---\n\n"
            f"--- BACKEND GUIDE ---\n{backend_guide}\n--- END ---\n\n"
            f"--- FRONTEND GUIDE ---\n{frontend_guide}\n--- END ---\n\n"
            "Output ONLY valid JSON:\n"
            '{"module_code":"xx","screen_code":"XXXX000","files":[{"file_path":"...","file_type":"...","layer":"backend|frontend","description":"...","depends_on":[]}]}\n\n'
            "File types: dto_request|dto_response|dao|dao_impl|service|service_impl|mapper_xml|db_init_sql|vue_types|vue_page\n"
            "IMPORTANT: Generate exactly ONE vue_page file. The vue_page MUST include SearchForm, DataTable, SumGrid sections inline, "
            "API calls (axios) directly in the component, and reactive state management using ref/reactive (no separate Pinia store).\n"
            "Do NOT generate separate vue_api, pinia_store, vue_search_form, vue_data_table, vue_sum_grid, or vue_scss files.\n"
            "Order by dependency chain. Backend package: hsc.tomms.web.{module}.{screen}/\n"
        )
        user = f"Technical Specification:\n{ctx.spec_markdown}\n\nProduce the file generation plan JSON."

        response = await codex_client.complete(system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS)
        data = json.loads(_strip_fences(response))
        plan = CodeGenPlan(
            module_code=data.get("module_code", ""),
            screen_code=data.get("screen_code", ""),
            files=[CodeGenPlanFile(**f) for f in data.get("files", [])],
        )
        ctx.plan = plan
        return plan


# ---------------------------------------------------------------------------
# Data Engineer Agent
# ---------------------------------------------------------------------------

class DataEngineerAgent:
    role = "data_engineer"

    def _get_my_files(self, plan: CodeGenPlan) -> list[CodeGenPlanFile]:
        return [f for f in plan.files if f.file_type in ("db_init_sql", "vue_types")]

    async def execute(self, ctx: SharedContext, on_chunk: callable | None = None) -> list[GeneratedFile]:
        assert ctx.plan is not None
        my_files = self._get_my_files(ctx.plan)
        results: list[GeneratedFile] = []

        system = (
            "You are a Data Engineer specializing in database schema design and TypeScript type definitions.\n"
            "You create DB init SQL (MariaDB) and TypeScript types that mirror backend DTOs.\n\n"
            "RULES:\n"
            "- Output ONLY the file content. No markdown fences, no explanations.\n"
            "- SQL: MariaDB syntax. Use snake_case for table/column names. Add CREATE TABLE IF NOT EXISTS.\n"
            "- TypeScript: Use camelCase for fields. Export interfaces matching backend DTO fields.\n"
            "- Include all fields from the spec's Domain Model section.\n"
        )

        for file_entry in my_files:
            user = (
                f"Specification:\n{ctx.spec_markdown}\n\n"
                f"Generate: {file_entry.file_path}\nType: {file_entry.file_type}\nDescription: {file_entry.description}\n"
            )

            content_parts: list[str] = []
            stream = await codex_client.complete(system, user, stream=True, max_tokens=settings.CODEGEN_MAX_TOKENS)
            async for chunk in stream:
                content_parts.append(chunk)
                if on_chunk:
                    on_chunk(chunk)

            content = _strip_fences("".join(content_parts))
            gf = GeneratedFile(
                file_path=file_entry.file_path,
                file_type=file_entry.file_type,
                content=content,
                layer=file_entry.layer,
            )
            results.append(gf)
            ctx.generated_files[gf.file_path] = gf

            # Store in shared context for other agents
            if file_entry.file_type == "vue_types":
                ctx.data_contracts = content
            elif file_entry.file_type == "db_init_sql":
                ctx.db_schema = content

        return results


# ---------------------------------------------------------------------------
# Backend Engineer Agent
# ---------------------------------------------------------------------------

class BackendEngineerAgent:
    role = "backend_engineer"

    _BACKEND_TYPES = {"dto_request", "dto_response", "dao", "dao_impl", "service", "service_impl", "mapper_xml"}

    def _get_my_files(self, plan: CodeGenPlan) -> list[CodeGenPlanFile]:
        return [f for f in plan.files if f.file_type in self._BACKEND_TYPES]

    async def execute(self, ctx: SharedContext, on_chunk: callable | None = None) -> list[GeneratedFile]:
        assert ctx.plan is not None
        my_files = self._get_my_files(ctx.plan)
        naming = get_naming_context()
        backend_guide = get_all_backend_guide()

        system = (
            "You are a senior Backend Engineer specializing in CPMS Spring Boot + MyBatis projects.\n"
            "You generate Java source files following CPMS coding patterns strictly.\n\n"
            f"--- NAMING CONVENTIONS ---\n{naming}\n--- END ---\n\n"
            f"--- BACKEND CODING GUIDE ---\n{backend_guide}\n--- END ---\n\n"
            "STRICT RULES:\n"
            "- Output ONLY the file content. No markdown fences.\n"
            "- DTO: @Getter, @Setter, @ToString. Function name only in class name (no screen code).\n"
            "- Service impl: @Service(\"ScreenCode-Desc\"), @ServiceId(\"ScreenCode/method\"), @ServiceName(\"설명\"), @Transactional on CUD.\n"
        "- ServiceId import: import hone.bom.annotation.ServiceId; (NOT has.fw.*)\n"
        "- ServiceName import: import hone.bom.annotation.ServiceName;\n"
            "- DAO impl: @Repository, SqlSession + NAMESPACE pattern.\n"
            "- Mapper XML: namespace=full DAO path, parameterType/resultType=full DTO path, <if test> for optional params.\n"
            "- All fields used in ServiceImpl MUST exist in the corresponding DTO.\n"
        "- NEVER use setter/getter methods that are not defined in the DTO (e.g., setCreatedAt, setUpdatedAt, setDeletedAt).\n"
        "- Do NOT add audit fields (createdAt, updatedAt, deletedAt) in ServiceImpl unless they are explicitly declared in the DTO.\n"
        "- Before calling any DTO method in ServiceImpl, verify the field exists in the DTO dependency file.\n"
        "- NEVER use java.util.UUID — use String for all ID fields. MyBatis has no UUID TypeHandler.\n"
        "\nKNOWN ERROR PREVENTION (DO NOT):\n"
        "- DO NOT use bare @Service with bean name like @Service(\"PMDP020Service-desc\") — use bare @Service without parameter.\n"
        "- DO NOT omit @Transactional — add @Transactional(readOnly=true) for queries, @Transactional for CUD.\n"
        "- DO NOT forget @ServiceId and @ServiceName on every public Service method.\n"
        "- DO NOT use bare < or > in Mapper XML — wrap in CDATA: <![CDATA[<=]]>\n"
        "- DO NOT hardcode all WHERE conditions — use <if test=\"param != null and param != ''\"> for optional filters.\n"
        "- DO NOT use wrong pagination — use OFFSET #{pageNo} ROWS FETCH NEXT #{pageSize} ROWS ONLY.\n"
        "- DO NOT use String for amounts — use BigDecimal for monetary fields, long for IDs.\n"
        "- DO NOT skip input validation in Service layer — validate required fields before DAO call.\n"
        "- DO NOT use inconsistent package paths — follow hsc.tomms.web.{module}.{screen}.{layer} pattern.\n"
        )

        results: list[GeneratedFile] = []
        for file_entry in my_files:
            # Collect dependencies
            deps_text = ""
            dep_parts = []
            for dep_path in file_entry.depends_on:
                if dep_path in ctx.generated_files:
                    dep = ctx.generated_files[dep_path]
                    dep_parts.append(f"--- {dep.file_path} ---\n{dep.content}")
            if not dep_parts:
                # Include recent same-layer files
                backend_files = [gf for gf in results[-3:]]
                for gf in backend_files:
                    dep_parts.append(f"--- {gf.file_path} ---\n{gf.content}")
            if dep_parts:
                deps_text = "\n\n".join(dep_parts)

            # Include DB schema for context
            schema_ctx = f"\nDB Schema:\n{ctx.db_schema}\n" if ctx.db_schema else ""

            user = (
                f"Specification:\n{ctx.spec_markdown}\n{schema_ctx}\n"
            )
            if deps_text:
                user += f"Dependencies:\n{deps_text}\n\n"
            user += f"Generate: {file_entry.file_path}\nType: {file_entry.file_type}\nDescription: {file_entry.description}\n"

            content_parts: list[str] = []
            stream = await codex_client.complete(system, user, stream=True, max_tokens=settings.CODEGEN_MAX_TOKENS)
            async for chunk in stream:
                content_parts.append(chunk)
                if on_chunk:
                    on_chunk(chunk)

            content = _strip_fences("".join(content_parts))
            gf = GeneratedFile(
                file_path=file_entry.file_path,
                file_type=file_entry.file_type,
                content=content,
                layer="backend",
            )
            results.append(gf)
            ctx.generated_files[gf.file_path] = gf

        return results


# ---------------------------------------------------------------------------
# Frontend Engineer Agent
# ---------------------------------------------------------------------------

class FrontendEngineerAgent:
    role = "frontend_engineer"

    _FRONTEND_TYPES = {"vue_page"}

    def _get_my_files(self, plan: CodeGenPlan) -> list[CodeGenPlanFile]:
        return [f for f in plan.files if f.file_type in self._FRONTEND_TYPES]

    async def execute(self, ctx: SharedContext, on_chunk: callable | None = None) -> list[GeneratedFile]:
        assert ctx.plan is not None
        my_files = self._get_my_files(ctx.plan)
        naming = get_naming_context()
        frontend_guide = get_all_frontend_guide()

        system = (
            "You are a senior Frontend Engineer specializing in CPMS Vue3 + PrimeVue projects.\n"
            "You generate a SINGLE consolidated Vue3 page component that includes ALL functionality inline.\n\n"
            f"--- NAMING CONVENTIONS ---\n{naming}\n--- END ---\n\n"
            f"--- FRONTEND CODING GUIDE ---\n{frontend_guide}\n--- END ---\n\n"
            "STRICT RULES:\n"
            "- Output ONLY the file content. No markdown fences.\n"
            "- MUST use <script setup lang=\"ts\"> syntax.\n"
            "- This single file MUST include:\n"
            "  1. TypeScript interfaces/types (inline, matching backend DTOs)\n"
            "  2. API call functions (using axios, inline)\n"
            "  3. Reactive state (ref/reactive, NO separate Pinia store)\n"
            "  4. SearchForm section (inline in template)\n"
            "  5. DataTable section (scrollHeight=\"540px\" + virtualScrollerOptions, pre-format dates in watch)\n"
            "  6. SumGrid section if applicable (inline in template)\n"
            "- Use <style scoped> for styles. No separate SCSS file.\n\n"
            "CRITICAL IMPORT PATHS:\n"
            "- ContentHeader: import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue'\n"
            "- SearchForm: import { SearchForm, SearchFormField, SearchFormLabel, SearchFormContent } from '@/components/common/searchForm'\n"
            "- DataTable2: import DataTable2 from '@/components/common/dataTable2/DataTable2.vue'\n"
            "- Button: import { Button } from '@/components/common/button'\n"
            "- InputText: import InputText from '@/components/common/inputText/InputText.vue'\n"
            "- Select: import Select from '@/components/common/select/Select.vue'\n"
            "- axios: import api from '@/plugins/axios'\n"
            "- formatErrorMessage: import { formatErrorMessage } from '@/utils/formatErrorMessage'\n"
            "- CommonCodeStore: import { useCommonCodeStore } from '@/stores/commonCodeStore'\n"
            "\nKNOWN ERROR PREVENTION (DO NOT):\n"
            "- DO NOT use scrollHeight=\"flex\" — MUST use scrollHeight=\"540px\" with virtualScrollerOptions=\"{ itemSize: 46 }\".\n"
            "- DO NOT format dates in template slots — pre-format in watch() with nextTick(), store as _FORMATTED fields.\n"
            "- DO NOT use if(newVal) in watch — use if(newVal !== undefined) to handle null/empty/0.\n"
            "- DO NOT access ref as .value.value.form — correct path is .value.form.\n"
            "- DO NOT use alert()/confirm()/prompt() — use Toast and ConfirmDialog.\n"
            "- DO NOT define UPPER_SNAKE_CASE TypeScript fields — match backend camelCase DTO field names exactly.\n"
            "- DO NOT forget await on commonCodeStore.loadMulti() in onMounted.\n"
            "- DO NOT define SelectBox options without computed() wrapper.\n"
            "- DO NOT omit GPU acceleration CSS — add will-change: background-color on tr, contain: layout style on td.\n"
            "- DO NOT apply hover styles to selected rows — use :hover:not(.p-datatable-row-selected).\n"
            "- DO NOT use <script> without setup — MUST be <script setup lang=\"ts\">.\n"
        )

        results: list[GeneratedFile] = []
        for file_entry in my_files:
            deps_text = ""
            dep_parts = []
            # Include data contracts (types.ts)
            if ctx.data_contracts:
                dep_parts.append(f"--- types.ts ---\n{ctx.data_contracts}")
            # Include recent frontend files
            for gf in results[-3:]:
                dep_parts.append(f"--- {gf.file_path} ---\n{gf.content}")
            if dep_parts:
                deps_text = "\n\n".join(dep_parts)

            user = f"Specification:\n{ctx.spec_markdown}\n\n"
            if deps_text:
                user += f"Dependencies:\n{deps_text}\n\n"
            user += f"Generate: {file_entry.file_path}\nType: {file_entry.file_type}\nDescription: {file_entry.description}\n"

            content_parts: list[str] = []
            stream = await codex_client.complete(system, user, stream=True, max_tokens=settings.CODEGEN_MAX_TOKENS)
            async for chunk in stream:
                content_parts.append(chunk)
                if on_chunk:
                    on_chunk(chunk)

            content = _strip_fences("".join(content_parts))
            gf = GeneratedFile(
                file_path=file_entry.file_path,
                file_type=file_entry.file_type,
                content=content,
                layer="frontend",
            )
            results.append(gf)
            ctx.generated_files[gf.file_path] = gf

        return results


# ---------------------------------------------------------------------------
# Backend QA Agent
# ---------------------------------------------------------------------------

class BackendQAAgent:
    role = "backend_qa"

    async def execute(self, ctx: SharedContext) -> list[dict]:
        """Review backend files against BackendGuide standards."""
        backend_files = [
            gf for gf in ctx.generated_files.values() if gf.layer == "backend"
        ]
        if not backend_files:
            return []

        backend_guide = get_all_backend_guide()
        files_text = "\n\n".join(
            f"=== {gf.file_path} ===\n{gf.content}" for gf in backend_files
        )

        system = (
            "You are a Backend QA Engineer reviewing generated Java/Spring Boot/MyBatis source files.\n"
            "You MUST validate against BOTH the technical specification AND the coding guide below.\n\n"
            f"--- TECHNICAL SPECIFICATION ---\n{ctx.spec_markdown}\n--- END ---\n\n"
            f"--- BACKEND CODING GUIDE ---\n{backend_guide}\n--- END ---\n\n"
            "CHECK ALL of the following:\n"
            "SPEC COMPLIANCE:\n"
            "- All functional requirements from the spec are implemented in Service/DAO/Mapper\n"
            "- All fields from the spec's domain model are present in DTOs\n"
            "- All API endpoints described in the spec have corresponding @ServiceId methods\n"
            "- Search conditions from the spec are reflected in Mapper XML queries\n\n"
            "CODING GUIDE COMPLIANCE:\n"
            "- DTO class names: function name only, NO screen code in class name (e.g., SearchListReqDto, NOT PMDP020SearchListReqDto)\n"
            "- @ServiceId format: @ServiceId(\"ScreenCode/methodName\")\n"
            "- @ServiceName with Korean description on every public service method\n"
            "- @Transactional on CUD methods, NOT on read-only methods\n"
            "- DAO impl: @Repository, SqlSession, NAMESPACE = full DAO interface path\n"
            "- Mapper XML: namespace = full DAO path, parameterType/resultType = full DTO path\n"
            "- Mapper XML: <if test> for optional params, CDATA for < > operators\n"
            "- ServiceImpl must NOT call DTO getter/setter methods that don't exist in the DTO\n"
            "- DAO interface methods must match DAO impl and Mapper XML statement IDs\n"
            "- Package paths must follow: hsc.tomms.web.{module}.{screen}.*\n"
            "- NEVER use java.util.UUID in DTOs or Mapper XML — use String for all ID fields (MyBatis has no UUID TypeHandler)\n"
            "- Mapper XML: all parameter properties must have matching javaType if not String (avoid jdbcType=null errors)\n\n"
            'Output JSON: {"issues": [{"file_path": "...", "issue": "description of problem", "fix_instruction": "how to fix"}]}\n'
            'If no issues: {"issues": []}\n'
            "Output ONLY JSON.\n"
        )

        user = f"Review these backend files:\n\n{files_text}\n\nValidate against the coding guide and report issues."
        response = await llm_client.complete(system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS)

        try:
            data = json.loads(_strip_fences(response))
            return data.get("issues", [])
        except (json.JSONDecodeError, KeyError):
            return []


# ---------------------------------------------------------------------------
# Frontend QA Agent
# ---------------------------------------------------------------------------

class FrontendQAAgent:
    role = "frontend_qa"

    async def execute(self, ctx: SharedContext) -> list[dict]:
        """Review frontend files against FrontendGuide standards."""
        frontend_files = [
            gf for gf in ctx.generated_files.values() if gf.layer == "frontend"
        ]
        if not frontend_files:
            return []

        frontend_guide = get_all_frontend_guide()
        files_text = "\n\n".join(
            f"=== {gf.file_path} ===\n{gf.content}" for gf in frontend_files
        )

        system = (
            "You are a Frontend QA Engineer reviewing generated Vue3/TypeScript source files.\n"
            "You MUST validate against BOTH the technical specification AND the coding guide below.\n\n"
            f"--- TECHNICAL SPECIFICATION ---\n{ctx.spec_markdown}\n--- END ---\n\n"
            f"--- FRONTEND CODING GUIDE ---\n{frontend_guide}\n--- END ---\n\n"
            "CHECK ALL of the following:\n"
            "SPEC COMPLIANCE:\n"
            "- All UI fields from the spec are present in the page (search form fields, grid columns)\n"
            "- All user actions from the spec are implemented (add row, delete row, search, etc.)\n"
            "- Grid columns match the spec's domain model fields\n"
            "- Search conditions match the spec's defined filters\n\n"
            "CODING GUIDE COMPLIANCE:\n"
            "- MUST use <script setup lang=\"ts\"> syntax (Options API is forbidden)\n"
            "- DataTable MUST have scrollHeight=\"540px\" + virtualScrollerOptions (performance critical)\n"
            "- Date formatting MUST be in watch+nextTick, NOT in template slots (causes 5000+ calls per render)\n"
            "- Import paths must be exact: ContentHeader from '@/components/common/contentHeader/ContentHeader.vue', etc.\n"
            "- API parameters: frontend snake_case MUST be converted to UPPERCASE for backend\n"
            "- searchParams: must use provide/inject pattern correctly\n"
            "- Ref access: must be .value.form (NOT .value.value.form or .form.value)\n"
            "- Watch conditions: use !== undefined (NOT if(value) which fails for null/empty)\n"
            "- GPU acceleration CSS: will-change and contain properties for DataTable rows\n"
            "- TypeScript types must match backend DTO fields\n\n"
            'Output JSON: {"issues": [{"file_path": "...", "issue": "description of problem", "fix_instruction": "how to fix"}]}\n'
            'If no issues: {"issues": []}\n'
            "Output ONLY JSON.\n"
        )

        user = f"Review these frontend files:\n\n{files_text}\n\nValidate against the coding guide and report issues."
        response = await llm_client.complete(system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS)

        try:
            data = json.loads(_strip_fences(response))
            return data.get("issues", [])
        except (json.JSONDecodeError, KeyError):
            return []


# ---------------------------------------------------------------------------
# Fix Agent
# ---------------------------------------------------------------------------

class FixAgent:
    role = "fix_agent"

    async def execute(self, ctx: SharedContext, issues: list[dict]) -> list[dict]:
        """Fix files based on QA issue reports. Returns list of {file_path, content}."""
        # Group issues by file
        file_issues: dict[str, list[dict]] = {}
        for issue in issues:
            fp = issue.get("file_path", "")
            if fp:
                file_issues.setdefault(fp, []).append(issue)

        fixes: list[dict] = []
        for file_path, file_issue_list in file_issues.items():
            # Find the original file
            gf = ctx.generated_files.get(file_path)
            if not gf:
                # Try partial match
                for path, candidate in ctx.generated_files.items():
                    if path.endswith(file_path) or file_path.endswith(candidate.file_path):
                        gf = candidate
                        break
            if not gf:
                continue

            issues_text = "\n".join(
                f"- {iss.get('issue', '')} → Fix: {iss.get('fix_instruction', '')}"
                for iss in file_issue_list
            )

            # Collect related files for context
            dep_parts = []
            file_dir = "/".join(gf.file_path.split("/")[:-1])
            for path, other in ctx.generated_files.items():
                if other.file_path != gf.file_path and other.file_path.startswith(file_dir):
                    dep_parts.append(f"--- {other.file_path} ---\n{other.content}")
            deps_text = "\n\n".join(dep_parts[:5])

            system = (
                "You are an expert developer applying QA fixes to source code.\n"
                "Output ONLY the complete fixed file content. No markdown fences, no explanations.\n"
                "Apply ALL the fixes listed below while preserving the overall structure and logic.\n"
            )

            user = (
                f"File to fix: {gf.file_path}\n"
                f"```\n{gf.content}\n```\n\n"
                f"Issues to fix:\n{issues_text}\n\n"
            )
            if deps_text:
                user += f"Related files for context:\n{deps_text}\n\n"
            user += "Output the complete fixed file."

            response = await llm_client.complete(system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS)
            fixes.append({"file_path": gf.file_path, "content": _strip_fences(response)})

        return fixes


# ---------------------------------------------------------------------------
# QA Engineer Agent (kept for deploy auto-fix)
# ---------------------------------------------------------------------------

class QAEngineerAgent:
    role = "qa_engineer"

    async def fix_file(
        self,
        error_log: str,
        file_path: str,
        file_content: str,
        all_files: list[GeneratedFile],
    ) -> str:
        """Fix compilation errors in a specific file."""
        related = []
        file_dir = "/".join(file_path.split("/")[:-1])
        for gf in all_files:
            if gf.file_path != file_path and (
                gf.file_path.startswith(file_dir) or
                any(part in error_log for part in gf.file_path.split("/")[-1:])
            ):
                related.append(f"--- {gf.file_path} ---\n{gf.content}")

        system = (
            "You are an expert developer fixing compilation errors.\n"
            "Output ONLY the complete fixed file content. No markdown fences.\n"
            "Fix ALL errors. If a method/field is missing in a DTO, ADD it.\n"
        )

        user = (
            f"Errors:\n```\n{error_log}\n```\n\n"
            f"File: {file_path}\n```\n{file_content}\n```\n\n"
        )
        if related:
            user += f"Related files:\n{''.join(related[:5])}\n\n"
        user += "Output the complete fixed file."

        response = await llm_client.complete(system, user, stream=False, max_tokens=settings.CODEGEN_MAX_TOKENS)
        return _strip_fences(response)
