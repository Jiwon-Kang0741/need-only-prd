"""Deploy-time build-error auto-fix.

When a generated project fails to compile (maven/docker), this module fixes the
offending Java file via gpt-5.5 and applies deterministic Java post-processing
(import organization, @Slf4j enforcement). Extracted from the legacy agents.py
so the deploy path no longer depends on the old orchestrator stack.
"""

from __future__ import annotations

import logging
import re

from app.config import settings
from app.llm.graph.llm import gpt55_client
from app.llm.codegen_context import get_allowed_import_prefixes, get_workspace_class_map
from app.models import GeneratedFile

logger = logging.getLogger(__name__)


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        nl = text.index("\n") if "\n" in text else 3
        text = text[nl + 1:]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3].rstrip()
    return text


# ---------------------------------------------------------------------------
# Import organization (STS/Eclipse-style, pom.xml enforced)
# ---------------------------------------------------------------------------

_IMPORT_REPLACEMENTS: list[tuple[str, str]] = [
    ("hone.bom.annotation.ServiceId", "aondev.framework.annotation.ServiceId"),
    ("hone.bom.annotation.ServiceName", "aondev.framework.annotation.ServiceName"),
    ("hone.bom.dao.mybatis.support.AbstractSqlSessionDaoSupport",
     "aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport"),
    ("javax.validation.constraints.Email", "jakarta.validation.constraints.Email"),
    ("javax.validation.constraints.NotBlank", "jakarta.validation.constraints.NotBlank"),
    ("javax.validation.constraints.NotNull", "jakarta.validation.constraints.NotNull"),
    ("javax.validation.constraints.NotEmpty", "jakarta.validation.constraints.NotEmpty"),
    ("javax.validation.constraints.Size", "jakarta.validation.constraints.Size"),
    ("javax.validation.constraints.Pattern", "jakarta.validation.constraints.Pattern"),
    ("javax.validation.constraints.Min", "jakarta.validation.constraints.Min"),
    ("javax.validation.constraints.Max", "jakarta.validation.constraints.Max"),
    ("javax.validation.constraints.Positive", "jakarta.validation.constraints.Positive"),
    ("javax.validation.constraints.PositiveOrZero", "jakarta.validation.constraints.PositiveOrZero"),
    ("javax.validation.Valid", "jakarta.validation.Valid"),
    ("javax.validation.constraints.*", "jakarta.validation.constraints.*"),
    ("javax.validation.*", "jakarta.validation.*"),
]

_IMPORT_RE = re.compile(r'^import\s+(static\s+)?([a-zA-Z0-9_.]+(?:\.\*)?)\s*;', re.MULTILINE)
_JAVA_IMPORT_ORDER = ["java.", "jakarta.", "javax.", "org.", "com.", "aondev.", "biz.", ""]


def _import_sort_key(imp: str) -> tuple[int, str]:
    for idx, prefix in enumerate(_JAVA_IMPORT_ORDER):
        if prefix and imp.startswith(prefix):
            return (idx, imp)
    return (len(_JAVA_IMPORT_ORDER), imp)


def _is_import_allowed(fqcn: str, allowed_prefixes: set[str]) -> bool:
    for prefix in allowed_prefixes:
        if fqcn.startswith(prefix + ".") or fqcn == prefix:
            return True
    return False


def organize_imports(content: str) -> str:
    """Organize Java imports: pom.xml validation, replace, remove unused/duplicates, sort."""
    allowed_prefixes = get_allowed_import_prefixes()
    lines = content.split("\n")

    package_line = ""
    import_lines: list[str] = []
    code_lines: list[str] = []
    in_imports = False
    past_imports = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("package ") and not past_imports:
            package_line = line
        elif stripped.startswith("import ") and not past_imports:
            in_imports = True
            import_lines.append(stripped)
        elif in_imports and stripped == "":
            continue
        else:
            if in_imports:
                past_imports = True
                in_imports = False
            code_lines.append(line)

    if not import_lines:
        return content

    code_body = "\n".join(code_lines)
    workspace_map = get_workspace_class_map()

    processed: dict[str, str] = {}
    for imp_line in import_lines:
        match = _IMPORT_RE.match(imp_line)
        if not match:
            continue
        static_prefix = match.group(1) or ""
        fqcn = match.group(2)

        for old, new in _IMPORT_REPLACEMENTS:
            if fqcn == old:
                fqcn = new
                break

        if "." in fqcn and not fqcn.endswith(".*"):
            simple_name = fqcn.rsplit(".", 1)[1]
            correct_fqcn = workspace_map.get(simple_name)
            if correct_fqcn and correct_fqcn != fqcn:
                fqcn = correct_fqcn

        if not _is_import_allowed(fqcn, allowed_prefixes):
            continue

        simple_name = fqcn.rsplit(".", 1)[-1] if "." in fqcn else fqcn
        # Word-boundary match so `List` is not considered "used" by `ArrayList`.
        used = simple_name == "*" or bool(
            re.search(rf"\b{re.escape(simple_name)}\b", code_body))
        if used:
            key = f"{static_prefix.strip()} {fqcn}".strip()
            if key not in processed:
                processed[key] = (f"import static {fqcn};" if static_prefix
                                  else f"import {fqcn};")

    sorted_imports = sorted(processed.values(),
                            key=lambda x: _import_sort_key(x.split()[-1].rstrip(";")))

    grouped: list[str] = []
    prev_prefix = ""
    for imp in sorted_imports:
        fqcn = imp.split()[-1].rstrip(";")
        cur_prefix = fqcn.split(".")[0] if "." in fqcn else ""
        if prev_prefix and cur_prefix != prev_prefix:
            grouped.append("")
        grouped.append(imp)
        prev_prefix = cur_prefix

    result_parts: list[str] = []
    if package_line:
        result_parts.append(package_line)
        result_parts.append("")
    if grouped:
        result_parts.extend(grouped)
        result_parts.append("")
    result_parts.extend(code_lines)
    return "\n".join(result_parts)


# ---------------------------------------------------------------------------
# @Slf4j enforcement for ServiceImpl
# ---------------------------------------------------------------------------

_SLF4J_ANNOTATION_RE = re.compile(r'@Slf4j\b')
_SLF4J_IMPORT_RE = re.compile(r'import\s+lombok\.extern\.slf4j\.Slf4j\s*;')
_SERVICE_OR_REPO_ANNOTATION_RE = re.compile(r'(@(?:Service|Repository)\b)')


def _strip_old_logger(content: str) -> str:
    """Normalize line endings and remove manual Logger/LoggerFactory field + imports."""
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    content = re.sub(
        r'\n[ \t]*(?:private\s+)?static\s+final\s+Logger\s+\w+\s*=\s*'
        r'LoggerFactory\.getLogger\s*\([^)]+\)\s*;[ \t]*',
        '\n', content,
    )
    content = re.sub(
        r'\nimport\s+org\.slf4j\.(?:Logger|LoggerFactory)\s*;[ \t]*',
        '\n', content,
    )
    return content


def ensure_slf4j_service_impl(content: str) -> str:
    """Unconditionally ensure @Slf4j annotation + import are present on a ServiceImpl."""
    content = _strip_old_logger(content)

    if not _SLF4J_ANNOTATION_RE.search(content):
        content = _SERVICE_OR_REPO_ANNOTATION_RE.sub(
            lambda m: '@Slf4j\n' + m.group(1), content, count=1
        )

    if not _SLF4J_IMPORT_RE.search(content):
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('package '):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, 'import lombok.extern.slf4j.Slf4j;')
        content = '\n'.join(lines)
    return content


# ---------------------------------------------------------------------------
# LLM-based build-error fix
# ---------------------------------------------------------------------------

_FIX_SYSTEM = (
    "You are an expert developer fixing compilation errors.\n"
    "Output ONLY the complete fixed file content. No markdown fences.\n"
    "Fix ALL errors. If a method/field is missing in a DTO, ADD it.\n\n"
    "ABSOLUTE RULES (violating ANY of these = broken code):\n"
    "- Use aondev.framework.annotation.ServiceId/ServiceName (NOT hone.bom.annotation.*).\n"
    "- Use aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport (NOT hone.bom.dao.*).\n"
    "- NEVER import org.slf4j.Logger or org.slf4j.LoggerFactory; ALWAYS use @Slf4j (Lombok).\n"
    "- EVERY public service method MUST wrap DAO calls in try { ... } "
    "catch (Exception e) { throw HscException.systemError(\"...\", e); }.\n"
    "- ALWAYS two args: HscException.systemError(\"메시지\", e) — never single-arg.\n"
    "- NEVER call log.error()/log.warn() before throw HscException.\n"
    "- DTO field Java types MUST match how they are used (String/int/List/Boolean).\n"
    "- ServiceImpl: NEVER call bare DAO base-class methods "
    "(insert/select/update/delete/selectOne/selectList) — use full wrapper names.\n"
    "- DaoImpl method names MUST append a domain noun (not bare CRUD verbs).\n"
    "- NEVER use CommonUtils.getUuid() or UUID.randomUUID() — IDs come from DB sequence.\n"
    "- ServiceImpl MUST only use methods/fields that exist in DTO and DAO.\n"
)


async def fix_build_error(
    error_log: str,
    file_path: str,
    file_content: str,
    all_files: list[GeneratedFile],
) -> str:
    """Fix compilation errors in a specific file using gpt-5.5."""
    file_dir = "/".join(file_path.split("/")[:-1])
    related: list[str] = []
    for gf in all_files:
        if gf.file_path != file_path and (
            gf.file_path.startswith(file_dir)
            or any(part in error_log for part in gf.file_path.split("/")[-1:])
        ):
            related.append(f"--- {gf.file_path} ---\n{gf.content}")

    backend_context_parts = [
        f"--- [{gf.file_type.upper()}] {gf.file_path} ---\n{gf.content}"
        for gf in all_files
        if gf.layer == "backend" and gf.file_path != file_path
    ]
    backend_context = "\n\n".join(backend_context_parts[:10])

    user = (
        f"Errors:\n```\n{error_log}\n```\n\n"
        f"File: {file_path}\n```\n{file_content}\n```\n\n"
    )
    if related:
        user += f"Related files:\n{''.join(related[:5])}\n\n"
    if backend_context:
        user += (f"=== ALL BACKEND FILES (cross-reference) ===\n{backend_context}\n"
                 f"=== END ===\n\n")
    user += (
        "BEFORE outputting, verify:\n"
        "  1. Every DAO method called in ServiceImpl exists in DaoImpl\n"
        "  2. Every DTO getter/setter called in ServiceImpl has a field in DTO\n"
        "  3. No CommonUtils.getUuid() or UUID.randomUUID()\n\n"
        "Output the complete fixed file."
    )

    response = await gpt55_client.complete(_FIX_SYSTEM, user,
                                           max_tokens=settings.CODEGEN_MAX_TOKENS)
    return _strip_fences(response)


def postprocess_fixed_file(file_path: str, file_type: str, content: str) -> str:
    """Apply deterministic Java post-processing after an LLM fix."""
    if file_type == "service_impl":
        content = ensure_slf4j_service_impl(content)
    if file_path.endswith(".java"):
        content = organize_imports(content)
    return content
