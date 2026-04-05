"""Prompt templates for code generation from spec.md."""

from __future__ import annotations

from app.llm.codegen_context import (
    get_all_backend_guide,
    get_all_frontend_guide,
    get_context_for_file_type,
    get_naming_context,
)


def codegen_plan_prompt(spec_markdown: str) -> tuple[str, str]:
    """Produce a file generation plan from a spec.md."""
    naming = get_naming_context()
    # For planning, include a summary of both guides (structure overviews)
    # but not the full 400KB — use the 02-project-structure files
    backend_guide = get_all_backend_guide()
    frontend_guide = get_all_frontend_guide()

    # Truncate guides to keep within context limits (~50KB each max)
    max_guide = 50000
    if len(backend_guide) > max_guide:
        backend_guide = backend_guide[:max_guide] + "\n... [truncated]"
    if len(frontend_guide) > max_guide:
        frontend_guide = frontend_guide[:max_guide] + "\n... [truncated]"

    system = (
        "You are a code architect that plans file generation for a Spring Boot + Vue3 project.\n"
        "Given a technical specification (spec.md), produce an ordered list of source files to generate.\n\n"
        "You MUST follow the naming conventions and project structure defined in the reference documents below.\n\n"
        "--- NAMING CONVENTIONS ---\n"
        f"{naming}\n"
        "--- END NAMING CONVENTIONS ---\n\n"
        "--- BACKEND GUIDE ---\n"
        f"{backend_guide}\n"
        "--- END BACKEND GUIDE ---\n\n"
        "--- FRONTEND GUIDE ---\n"
        f"{frontend_guide}\n"
        "--- END FRONTEND GUIDE ---\n\n"
        "Output ONLY valid JSON with this exact schema:\n"
        "{\n"
        '  "module_code": "xx",\n'
        '  "screen_code": "XXXX000",\n'
        '  "files": [\n'
        "    {\n"
        '      "file_path": "relative/path/to/File.java",\n'
        '      "file_type": "dto_request|dto_response|dao|dao_impl|service|service_impl|mapper_xml|db_init_sql|vue_types|vue_page",\n'
        '      "layer": "backend|frontend",\n'
        '      "description": "Brief description",\n'
        '      "depends_on": ["path/to/dependency.java"]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "File generation order MUST follow dependency chain:\n"
        "1. Request DTOs → 2. Response DTOs → 3. DAO interfaces → 4. DAO impls →\n"
        "5. Mapper XML → 6. Service interfaces → 7. Service impls →\n"
        "8. DB init SQL → 9. Frontend types.ts → 10. Vue page (single file with SearchForm, DataTable, SumGrid, API calls, and state inline)\n\n"
        "IMPORTANT: Generate exactly ONE vue_page file. Do NOT generate separate vue_api, pinia_store, vue_search_form, vue_data_table, vue_sum_grid, or vue_scss files.\n"
        "The vue_page must include all frontend functionality in a single component.\n\n"
        "Backend package: hsc.tomms.web.{module}.{screen}/\n"
        "Backend path: src/main/java/hsc/tomms/web/{module}/{screen}/\n"
        "Frontend path: src/pages/{module}/{category}/{screenId}/\n"
        "Frontend API path: src/api/pages/{module}/{category}/\n"
    )

    user = (
        f"Technical Specification:\n{spec_markdown}\n\n"
        "Analyze this specification and produce the file generation plan JSON."
    )
    return system, user


def codegen_file_prompt(
    spec_markdown: str,
    guide_context: str,
    naming_context: str,
    file_plan_entry: dict,
    dependent_files: list[dict],
) -> tuple[str, str]:
    """Generate a single source file."""
    file_type = file_plan_entry.get("file_type", "")
    file_path = file_plan_entry.get("file_path", "")
    description = file_plan_entry.get("description", "")

    system = (
        f"You are an expert developer generating a {file_type} file for a Spring Boot + Vue3 project.\n"
        "Follow the coding patterns, naming conventions, and project structure from the reference documents below.\n\n"
        "--- NAMING CONVENTIONS ---\n"
        f"{naming_context}\n"
        "--- END NAMING CONVENTIONS ---\n\n"
        "--- CODING GUIDE ---\n"
        f"{guide_context}\n"
        "--- END CODING GUIDE ---\n\n"
        "STRICT RULES — you MUST follow all of these:\n"
        "- Output ONLY the file content. No markdown fences, no explanations, no commentary.\n"
        "- Use the exact package paths and class names as specified.\n"
        "- Follow the patterns from the CODING GUIDE exactly. The guide is the authority.\n"
        "\n"
        "BACKEND (Java/Spring Boot) RULES:\n"
        "- Use Lombok: @Getter, @Setter, @ToString on DTOs; @Slf4j, @RequiredArgsConstructor on Service/DAO impl.\n"
        "- Service impl: @Service(\"ScreenCode-Description\"), @ServiceId(\"ScreenCode/methodName\"), @ServiceName(\"설명\").\n"
        "- Service impl: @Transactional on all CUD (Create/Update/Delete) methods. Read-only methods do NOT need it.\n"
        "- DAO impl: @Repository, private final SqlSession sqlSession, private static final String NAMESPACE = full DAO interface path.\n"
        "- DAO impl: Use sqlSession.selectList(), selectOne(), insert(), update(), delete() with NAMESPACE + \".methodName\".\n"
        "- Mapper XML: Use <!DOCTYPE mapper> header, namespace = full DAO interface path, parameterType/resultType = full DTO path.\n"
        "- Mapper XML: Use <if test=\"field != null and field != ''\"> for optional parameters. Column aliasing: SNAKE_CASE as camelCase.\n"
        "- DTO class names: Function name ONLY (e.g., SearchListReqDto), NO screen code in class name.\n"
        "\n"
        "FRONTEND (Vue3) RULES — CRITICAL:\n"
        "- MUST use <script setup lang=\"ts\"> syntax. Never use Options API or <script> without setup.\n"
        "- Page component (index.vue): MUST define searchParams as ref and provide() it to child components.\n"
        "  Example: const searchParams = ref<SearchParams>({}); provide('searchParams', searchParams);\n"
        "- Child components (SearchForm, DataTable, SumGrid): MUST inject('searchParams') to receive shared state.\n"
        "- SearchForm: Use inject('searchParams'), emit('search'), watch searchParams fields and sync with form via setFieldValue.\n"
        "- DataTable: Props-based data binding, virtual scrolling with scrollHeight=\"540px\" + virtualScrollerOptions.\n"
        "- DataTable: Pre-format dates in watch() with nextTick(), NOT in template slots.\n"
        "- Use PrimeVue components: DataTable, Column, Button, InputText, Dropdown, Dialog, Toast.\n"
        "- API layer: Parameter convention — frontend uses snake_case, backend uses UPPERCASE. API layer converts.\n"
        "- Types: Define in src/api/pages/{module}/{category}/types.ts (shared), NOT in page folder.\n"
        "- SCSS: Each component has its own .scss file imported in the component.\n"
        "- SCSS variables: Use CSS custom properties (--spacing-md, --bg-1, --border-radius-lg, --shadow-sm, etc.).\n"
        "\n"
        "CRITICAL IMPORT PATHS (must match exactly):\n"
        "- ContentHeader: import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue'\n"
        "- SearchForm: import { SearchForm, SearchFormField, SearchFormLabel, SearchFormContent } from '@/components/common/searchForm'\n"
        "- DataTable2: import DataTable2 from '@/components/common/dataTable2/DataTable2.vue'\n"
        "- Button: import { Button } from '@/components/common/button'\n"
        "- InputText: import InputText from '@/components/common/inputText/InputText.vue'\n"
        "- InputNumber: import InputNumber from '@/components/common/inputNumber/InputNumber.vue'\n"
        "- Select: import Select from '@/components/common/select/Select.vue'\n"
        "- MultiSelect: import MultiSelect from '@/components/common/multiSelect/MultiSelect.vue'\n"
        "- DatePicker: import { DatePicker, RangeDatePicker } from '@/components/common/datePicker'\n"
        "- axios: import api from '@/plugins/axios'\n"
        "- formatErrorMessage: import { formatErrorMessage } from '@/utils/formatErrorMessage'\n"
        "- CommonCodeStore: import { useCommonCodeStore } from '@/stores/commonCodeStore'\n"
        "- AuthStore: import { useAuthenticationStore } from '@/stores/userStore'\n"
    )

    deps_text = ""
    if dependent_files:
        dep_parts = []
        for dep in dependent_files:
            dep_parts.append(f"--- {dep['file_path']} ---\n{dep['content']}")
        deps_text = "\n\n".join(dep_parts)

    user = (
        f"Technical Specification:\n{spec_markdown}\n\n"
    )

    if deps_text:
        user += f"Previously generated files (dependencies):\n{deps_text}\n\n"

    user += (
        f"Generate the following file:\n"
        f"- Path: {file_path}\n"
        f"- Type: {file_type}\n"
        f"- Description: {description}\n\n"
        "Output the complete file content now."
    )
    return system, user


def codegen_review_prompt(
    all_files: list[dict],
) -> tuple[str, str]:
    """Review all generated files for cross-file consistency issues."""
    system = (
        "You are a senior code reviewer checking generated Java and Vue3 source files for consistency.\n"
        "Review ALL files together and find cross-file reference errors:\n"
        "- ServiceImpl calling DTO methods (getXxx/setXxx) that don't exist in the DTO class\n"
        "- DAO interface methods that don't match DaoImpl or Mapper XML\n"
        "- Vue components importing files that don't exist\n"
        "- TypeScript types that don't match backend DTOs\n"
        "- Missing fields that are referenced across files\n\n"
        "For EACH file that needs fixes, output the COMPLETE corrected file.\n"
        "Output valid JSON with this schema:\n"
        "{\n"
        '  "fixes": [\n'
        '    {"file_path": "path/to/File.java", "content": "complete fixed file content"}\n'
        "  ]\n"
        "}\n"
        "If no fixes needed, output: {\"fixes\": []}\n"
        "Output ONLY JSON. No explanation.\n"
    )

    files_text = "\n\n".join(
        f"=== {f['file_path']} ===\n{f['content']}" for f in all_files
    )

    user = (
        f"Review these generated source files for cross-file consistency:\n\n"
        f"{files_text}\n\n"
        "Find and fix all cross-file reference errors. Output JSON."
    )
    return system, user


def codegen_fix_prompt(
    error_log: str,
    file_path: str,
    file_content: str,
    related_files: list[dict],
) -> tuple[str, str]:
    """Fix a compilation error in a generated source file."""
    system = (
        "You are an expert Java/Vue3 developer fixing compilation errors.\n"
        "You will be given a source file that failed to compile, the error messages, "
        "and related files for context.\n\n"
        "RULES:\n"
        "- Output ONLY the complete fixed file content. No markdown fences, no explanations.\n"
        "- Fix ALL compilation errors mentioned in the error log.\n"
        "- Do NOT change the overall structure or logic — only fix what is broken.\n"
        "- If a method or field is referenced but missing in a DTO, ADD it.\n"
        "- If an import is missing, ADD it.\n"
        "- Preserve all existing annotations and patterns.\n"
    )

    related_text = ""
    if related_files:
        parts = [f"--- {rf['file_path']} ---\n{rf['content']}" for rf in related_files]
        related_text = "\n\n".join(parts)

    user = (
        f"Compilation errors:\n```\n{error_log}\n```\n\n"
        f"File to fix: {file_path}\n"
        f"```\n{file_content}\n```\n\n"
    )
    if related_text:
        user += f"Related files for context:\n{related_text}\n\n"
    user += "Output the complete fixed file content."

    return system, user


def codegen_docker_prompt(
    spec_markdown: str,
    module_code: str,
    screen_code: str,
    file_list: list[str],
) -> tuple[str, str]:
    """Generate Docker configuration files."""
    system = (
        "You are a DevOps engineer creating Docker configuration for a Spring Boot + Vue3 project.\n"
        "Generate docker-compose.yml, backend Dockerfile, frontend Dockerfile, and DB init SQL.\n\n"
        "Output valid JSON with this exact schema:\n"
        "{\n"
        '  "docker_compose_yaml": "...",\n'
        '  "backend_dockerfile": "...",\n'
        '  "frontend_dockerfile": "...",\n'
        '  "db_init_sql": "..."\n'
        "}\n\n"
        "Requirements:\n"
        "- Backend: Spring Boot 2.7.18, Java 11, Maven build, port 8080\n"
        "- Frontend: Vue3 + Vite, Node 18, dev server port 3000\n"
        "- Database: MariaDB 10.11, port 3306\n"
        "- Use multi-stage builds for efficiency\n"
        "- Backend connects to DB via SPRING_DATASOURCE_URL env var\n"
        "- Frontend proxies /api to backend\n"
        "- All services on same Docker network\n"
    )

    user = (
        f"Module: {module_code}, Screen: {screen_code}\n\n"
        f"Generated source files:\n" + "\n".join(f"- {f}" for f in file_list) + "\n\n"
        f"Specification summary:\n{spec_markdown[:3000]}\n\n"
        "Generate the Docker configuration JSON."
    )
    return system, user
