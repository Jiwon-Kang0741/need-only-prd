"""Multi-agent code generation: specialized agents for each role."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from app.config import settings
from app.llm.client import codex_client, llm_client
from app.llm.codegen_context import (
    get_all_backend_guide,
    get_all_frontend_guide,
    get_allowed_import_prefixes,
    get_context_for_file_type,
    get_naming_context,
    get_pom_dependencies,
    get_workspace_class_map,
)
from app.models import CodeGenPlan, CodeGenPlanFile, GeneratedFile


# ---------------------------------------------------------------------------
# Static Check (no LLM, regex-based)
# ---------------------------------------------------------------------------

_BACKEND_CHECKS = [
    (re.compile(r'import\s+java\.util\.UUID'), "java.util.UUID import found — use String for ID fields"),
    (re.compile(r'javaType\s*=\s*["\']?java\.util\.UUID'), "UUID javaType in Mapper XML — use java.lang.String"),
    (re.compile(r'@Service\s*\(\s*"[^"]+"\s*\)'), "@Service with bean name — use bare @Service without parameter"),
    (re.compile(r'import\s+com\.mnwise\.'), "com.mnwise.* import found — use aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport for DAO"),
    (re.compile(r'import\s+com\.posdata\.'), "com.posdata.* import found — use aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport for DAO"),
    (re.compile(r'import\s+has\.fw\.'), "has.fw.* import found — use aondev.framework.annotation for ServiceId/ServiceName"),
    (re.compile(r'import\s+hone\.bom\.annotation\.'), "hone.bom.annotation.* import found — use aondev.framework.annotation.ServiceId/ServiceName"),
    (re.compile(r'import\s+hone\.bom\.dao\.'), "hone.bom.dao.* import found — use aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport"),
    (re.compile(r'import\s+biz\.common\.dto\.'), "biz.common.dto.* import found — use com.common.dto.base.SearchBaseDto / AuditBaseDto"),
    # Bare DAO base-class method call from ServiceImpl — must use full wrapper method names
    # NOTE: "select" alone (without suffix) is also a bare call — caught here alongside selectOne/selectList
    (re.compile(r'\w+(?:Dao|DaoImpl)\s*\.\s*(?:insert|update|delete|selectOne|selectList|batchUpdateReturnSumAffectedRows|select)\s*\('),
     "Bare DAO base-class method call in ServiceImpl — "
     "these are AbstractSqlSessionDaoSupport internal methods NOT accessible from Service layer. "
     "Use the full wrapper method names defined in DaoImpl (insertXxx, selectXxxList, selectXxx, updateXxx, deleteXxx)"),
    # DaoImpl method declarations must NOT be named with bare CRUD verbs — must include a domain suffix
    (re.compile(r'\bpublic\s+\S+\s+(?:insert|update|delete|select|selectList|selectOne)\s*\('),
     "DaoImpl method declaration has a bare CRUD name (insert/update/delete/select/selectList/selectOne). "
     "WRONG: public int insert(XxxResDto p)  "
     "CORRECT: public int insertXxx(XxxResDto p) — always append a domain noun (e.g. insertEduPgm, selectUserList). "
     "The method name MUST match the Mapper XML statement id exactly."),
    # Logging violations
    (re.compile(r'LoggerFactory\.getLogger\s*\('),
     "LoggerFactory.getLogger() found — remove the Logger field declaration and use @Slf4j class annotation "
     "(import lombok.extern.slf4j.Slf4j) instead. @Slf4j provides the 'log' field automatically."),
    (re.compile(r'import\s+org\.slf4j\.Logger\s*;'),
     "import org.slf4j.Logger found — remove this import; use @Slf4j (Lombok) instead of manual Logger declaration"),
    (re.compile(r'import\s+org\.slf4j\.LoggerFactory\s*;'),
     "import org.slf4j.LoggerFactory found — remove this import; use @Slf4j (Lombok) instead of LoggerFactory.getLogger()"),
    (re.compile(r'log\.(error|warn)\s*\([^;]+\);\s*\n\s*throw\s+(?:HscException|new\s+HscException)', re.MULTILINE),
     "log.error()/log.warn() immediately before throw HscException — remove the log call entirely. "
     "Just use: throw HscException.systemError(\"...\", e); The framework already logs thrown exceptions."),
    # UUID usage
    (re.compile(r'UUID\s*\.\s*randomUUID\s*\('),
     "UUID.randomUUID() found — NEVER use java.util.UUID. "
     "ID values come from DB sequence or are already in the DTO. Remove the UUID usage entirely."),
    # Manual audit field setting (AuditBaseDto handles these automatically)
    (re.compile(r'\.\s*set(?:FstCretDtm|FstCrtrId|LastMdfcDtm|LastMdfrId)\s*\('),
     "Manual audit field setting found (setFstCretDtm/setFstCrtrId/setLastMdfcDtm/setLastMdfrId) — "
     "AuditBaseDto constructor sets these automatically. Remove all manual audit field assignments."),
    # DateTimeFormatter in ServiceImpl
    (re.compile(r'DateTimeFormatter\s*\.\s*ofPattern'),
     "DateTimeFormatter.ofPattern() found in ServiceImpl — "
     "NEVER format dates manually. Use DateUtil from framework or let AuditBaseDto handle audit timestamps."),
    # getSortDirection() used for CRUD status routing
    (re.compile(r'\.getSortDirection\s*\(\s*\)'),
     "getSortDirection() used for CRUD status — WRONG. "
     "Use ResDto.getStatus() with CommonUtils.filterByStatus(list, GridStatus.INSERTED/UPDATED/DELETED)."),
    # save method taking single ReqDto instead of List<ResDto>
    (re.compile(r'public\s+\w+\s+save\w*\s*\(\s*(?:@\w+\s+)?(?:\w+ReqDto)\s+\w+\s*\)'),
     "save() method takes single ReqDto — WRONG. "
     "Save methods MUST accept List<ResDto> and use GridStatus + CommonUtils.filterByStatus() for CRUD routing."),
]

_FRONTEND_CHECKS = [
    (re.compile(r'scrollHeight\s*=\s*["\']flex["\']'), 'scrollHeight="flex" found — use scrollHeight="540px" with virtualScrollerOptions'),
    (re.compile(r'<script(?!\s+setup)[\s>]'), '<script> without setup — must use <script setup lang="ts">'),
    (re.compile(r'\balert\s*\('), 'alert() found — use Toast component instead'),
    (re.compile(r'\bconfirm\s*\('), 'confirm() found — use ConfirmDialog instead'),
    (re.compile(r'\bapi\.get\s*\('), 'api.get() found — CPMS /api/v1/ dispatcher only accepts POST. Use api.post() for ALL calls including search/select'),
    # Fabrication detection: common patterns of LLM-invented imports
    (re.compile(r"from\s+['\"]primevue/"), 'Direct PrimeVue import found — CPMS wraps PrimeVue components. Use CPMS common components from @/components/common/ instead'),
    (re.compile(r"import\s+.*\s+from\s+['\"]@/components/(?!common/)[^'\"]+['\"]"), 'Non-common component import — verify this path exists. CPMS shared components live under @/components/common/'),
    (re.compile(r"from\s+['\"]@/utils/(?!formatErrorMessage)[^'\"]+['\"]"), 'Unknown @/utils/ import — only formatErrorMessage is a verified utility. Check if this utility actually exists'),
]


def _check_forbidden_imports(gf: GeneratedFile) -> list[dict]:
    """Dynamically detect imports from libraries NOT in pom.xml."""
    if gf.layer != "backend" or not gf.file_path.endswith(".java"):
        return []

    allowed = get_allowed_import_prefixes()
    issues: list[dict] = []
    seen_packages: set[str] = set()

    for match in _IMPORT_RE.finditer(gf.content):
        fqcn = match.group(2)
        if _is_import_allowed(fqcn, allowed):
            continue
        pkg = fqcn.rsplit(".", 1)[0] if "." in fqcn else fqcn
        if pkg in seen_packages:
            continue
        seen_packages.add(pkg)
        issues.append({
            "file_path": gf.file_path,
            "issue": f"[STATIC] import {pkg}.* — library NOT in pom.xml, compilation will fail",
            "fix_instruction": (
                f"Remove ALL {pkg}.* usage from this file. "
                f"Replace with plain Java (java.util/java.io) or pom.xml-declared libraries. "
                f"Do NOT just remove the import — rewrite the code that uses {pkg} classes."
            ),
        })
    return issues


def _check_cross_file_consistency(files: list[GeneratedFile]) -> list[dict]:
    """Cross-check generated files for consistency: DTO fields, DAO methods, types."""
    issues: list[dict] = []

    _field_re = re.compile(r'private\s+\S+\s+(\w+)\s*;')
    _accessor_re = re.compile(r'(\w+)\.(get|set|is)([A-Z]\w*)\s*\(')
    _var_decl_re = re.compile(r'(\w[\w<>,\s]*?)\s+(\w+)\s*=')
    _method_def_re = re.compile(r'public\s+\S+\s+(\w+)\s*\(([^)]*)\)')
    _dao_call_re = re.compile(r'(\w+Dao(?:Impl)?)\s*\.\s*(\w+)\s*\(([^)]*)\)')
    _self_call_re = re.compile(
        r'(?:public|private|protected)\s+\S+\s+(\w+)\s*\([^)]*\)\s*\{[^}]*'
        r'(?:this\s*\.\s*\1|(\w+Dao)\s*\.\s*\1)\s*\(',
        re.DOTALL,
    )

    dto_fields: dict[str, set[str]] = {}
    dto_file_paths: dict[str, str] = {}  # class_name → file_path
    dao_methods: dict[str, set[str]] = {}
    dao_method_sigs: dict[str, dict[str, tuple]] = {}  # class_name → {method → (ret_type, params_str)}
    dao_file_paths: dict[str, str] = {}   # class_name → file_path
    service_files: list[GeneratedFile] = []
    dao_files: list[GeneratedFile] = []

    # Regex to capture full public method signatures (return type + params)
    _pub_sig_re = re.compile(
        r'public\s+([\w<>?,\[\] ]+?)\s+(\w+)\s*\(([^)]*)\)',
        re.MULTILINE,
    )

    for gf in files:
        if gf.layer != "backend" or not gf.file_path.endswith(".java"):
            continue
        class_name = gf.file_path.split("/")[-1].replace(".java", "")

        if "Dto" in class_name:
            fields = set()
            for m in _field_re.finditer(gf.content):
                fields.add(m.group(1))
            dto_fields[class_name] = fields
            dto_file_paths[class_name] = gf.file_path
        elif "DaoImpl" in class_name:
            methods = set()
            sigs: dict[str, tuple] = {}
            for m in _method_def_re.finditer(gf.content):
                methods.add(m.group(1))
            for m in _pub_sig_re.finditer(gf.content):
                ret = m.group(1).strip()
                mname = m.group(2)
                params = m.group(3).strip()
                if mname != class_name:  # skip constructor
                    sigs[mname] = (ret, params)
            dao_methods[class_name] = methods
            dao_method_sigs[class_name] = sigs
            dao_file_paths[class_name] = gf.file_path
            dao_files.append(gf)
        elif "ServiceImpl" in class_name:
            service_files.append(gf)

    # --- 1. DTO getter/setter field existence check ---
    var_type_re = re.compile(r'(?:final\s+)?(\w+(?:Dto\w*))\s+(\w+)\s*[=;,)]')

    for gf in service_files:
        var_to_dto: dict[str, str] = {}
        for m in var_type_re.finditer(gf.content):
            dto_type = m.group(1)
            var_name = m.group(2)
            if dto_type in dto_fields:
                var_to_dto[var_name] = dto_type

        for m in _accessor_re.finditer(gf.content):
            var_name = m.group(1)
            method_type = m.group(2)
            prop_upper = m.group(3)
            prop_name = prop_upper[0].lower() + prop_upper[1:]

            if var_name not in var_to_dto:
                continue
            dto_name = var_to_dto[var_name]
            fields = dto_fields.get(dto_name, set())
            if fields and prop_name not in fields:
                dto_file = dto_file_paths.get(dto_name, gf.file_path)
                issues.append({
                    "file_path": dto_file,  # Fix Agent will modify the DTO file
                    "issue": (
                        f"[STATIC] {var_name}.{method_type}{prop_upper}() called in {gf.file_path} "
                        f"but field '{prop_name}' does NOT exist in {dto_name}"
                    ),
                    "fix_instruction": (
                        f"ADD 'private String {prop_name};' inside the {dto_name} class body — "
                        f"do NOT remove the getter/setter call in ServiceImpl. "
                        f"The DTO must declare every field that ServiceImpl accesses. "
                        f"Currently declared fields: {', '.join(sorted(fields)[:15])}"
                    ),
                })

    # --- 2. ServiceImpl → DaoImpl method existence check ---
    # Regex to infer return type from the assignment in ServiceImpl:
    #   List<FooResDto> list = daoVar.missingMethod(param);
    _assign_call_re = re.compile(
        r'([\w<>?,\[\] ]+?)\s+\w+\s*=\s*\w+\.' + r'(\w+)\s*\(([^)]*)\)',
        re.MULTILINE,
    )

    for gf in service_files:
        # Build a lookup of (called_method → inferred return type + call args) from assignment expressions
        inferred: dict[str, tuple[str, str]] = {}
        for am in _assign_call_re.finditer(gf.content):
            ret = am.group(1).strip()
            mname = am.group(2)
            args = am.group(3).strip()
            inferred[mname] = (ret, args)

        for m in _dao_call_re.finditer(gf.content):
            dao_var = m.group(1)
            called_method = m.group(2)
            call_args = m.group(3).strip() if m.lastindex >= 3 else ""

            for dao_name, methods in dao_methods.items():
                dao_simple = dao_name[0].lower() + dao_name[1:]
                # Also match variable names without "Impl" suffix (e.g., cpmsEduPgmRsltLstDao)
                dao_without_impl = dao_simple[:-4] if dao_name.endswith("Impl") else dao_simple
                if dao_var in (dao_simple, dao_name, dao_without_impl):
                    if called_method not in methods:
                        # Infer type hint for the new DaoImpl method
                        inferred_ret, inferred_args = inferred.get(called_method, ("", call_args))
                        type_hint = (
                            f"  Inferred from ServiceImpl usage: returns '{inferred_ret}', args=({inferred_args})\n"
                            if inferred_ret else
                            f"  Infer the return type from how '{called_method}' result is used in ServiceImpl.\n"
                        )
                        dao_fp = dao_file_paths.get(dao_name, "")
                        issues.append({
                            "file_path": dao_fp or gf.file_path,
                            "issue": (
                                f"[STATIC] {dao_var}.{called_method}() is called in ServiceImpl "
                                f"but method '{called_method}' does NOT exist in {dao_name}"
                            ),
                            "fix_instruction": (
                                f"ADD the missing method '{called_method}' to {dao_name} (file: {dao_fp or dao_name + '.java'}).\n"
                                f"{type_hint}"
                                f"  Pattern: 'public <ReturnType> {called_method}(<ParamType> param) {{ return super.<op>(\"{called_method}\", param); }}'\n"
                                f"  Use super.selectList() for list queries, super.selectOne() for single/count,\n"
                                f"  super.insert() for inserts, super.update()/super.delete() for single CUD,\n"
                                f"  super.batchUpdateReturnSumAffectedRows() for List<> CUD.\n"
                                f"  Also add the corresponding SQL statement '<select|insert|update|delete id=\"{called_method}\"> "
                                f"to the Mapper XML if it does not already exist.\n"
                                f"  DO NOT remove the call in ServiceImpl — add the method where it is missing."
                            ),
                        })

    # --- 3. Return type / Object assignment check ---
    _bad_object_re = re.compile(
        r'Object\s+\w+\s*=\s*\w+\.\w+\s*\(',
    )
    for gf in service_files + dao_files:
        for m in _bad_object_re.finditer(gf.content):
            issues.append({
                "file_path": gf.file_path,
                "issue": f"[STATIC] 'Object' used as variable type for method return value — use proper typed variable",
                "fix_instruction": "Replace 'Object' with the actual return type (List<...>, int, etc.)",
            })

    # --- 4. MultipartFile in DAO parameter check ---
    _multipart_dao_re = re.compile(r'class\s+\w*DaoImpl\b.*?MultipartFile', re.DOTALL)
    for gf in dao_files:
        if 'MultipartFile' in gf.content:
            issues.append({
                "file_path": gf.file_path,
                "issue": "[STATIC] MultipartFile used in DAO layer — file handling belongs in Service layer",
                "fix_instruction": "Move file parsing logic to ServiceImpl; DAO should only handle DB operations via MyBatis",
            })

    # --- 5. ServiceImpl public methods without @ServiceId ---
    # Every public method in ServiceImpl MUST have @ServiceId immediately before it.
    # Methods without @ServiceId are either alias/wrapper methods (must be deleted) or forgot annotation.
    _pub_method_re = re.compile(
        r'^\s*public\s+(?:(?:static|final|synchronized)\s+)*'
        r'(?!class\b)(?!enum\b)(\S+)\s+(\w+)\s*\(',
        re.MULTILINE,
    )
    for gf in service_files:
        lines = gf.content.split('\n')
        for i, line in enumerate(lines):
            m = _pub_method_re.match(line)
            if not m:
                continue
            method_name = m.group(2)
            # Check preceding 6 lines for @ServiceId
            preceding = '\n'.join(lines[max(0, i - 6):i])
            if '@ServiceId' not in preceding:
                issues.append({
                    "file_path": gf.file_path,
                    "issue": (
                        f"[STATIC] Public method '{method_name}' in ServiceImpl has no @ServiceId — "
                        f"every public method MUST have @ServiceId and @ServiceName"
                    ),
                    "fix_instruction": (
                        f"If '{method_name}' is an alias/wrapper that just delegates to another method, "
                        f"DELETE it entirely. "
                        f"Otherwise add @ServiceId(\"ScreenCode/{method_name}\") and "
                        f"@ServiceName(\"Korean description\") immediately before it."
                    ),
                })

    return issues


def static_check(files: list[GeneratedFile]) -> list[dict]:
    """Run regex-based static checks + pom.xml import validation on generated files."""
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
        issues.extend(_check_forbidden_imports(gf))

    issues.extend(_check_cross_file_consistency(files))
    return issues


# ---------------------------------------------------------------------------
# Organize Imports (like STS / Eclipse "Organize Imports")
# ---------------------------------------------------------------------------

_IMPORT_REPLACEMENTS: list[tuple[str, str]] = [
    # Known framework renames (old package → new package, not resolvable from source scan)
    ("hone.bom.annotation.ServiceId", "aondev.framework.annotation.ServiceId"),
    ("hone.bom.annotation.ServiceName", "aondev.framework.annotation.ServiceName"),
    ("hone.bom.dao.mybatis.support.AbstractSqlSessionDaoSupport",
     "aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport"),
]

_IMPORT_RE = re.compile(r'^import\s+(static\s+)?([a-zA-Z0-9_.]+(?:\.\*)?)\s*;', re.MULTILINE)
_JAVA_IMPORT_ORDER = ["java.", "javax.", "org.", "com.", "aondev.", "biz.", ""]


def _import_sort_key(imp: str) -> tuple[int, str]:
    """Sort key: java → javax → org → com → aondev → biz → others."""
    for idx, prefix in enumerate(_JAVA_IMPORT_ORDER):
        if prefix and imp.startswith(prefix):
            return (idx, imp)
    return (len(_JAVA_IMPORT_ORDER), imp)


def _is_import_allowed(fqcn: str, allowed_prefixes: set[str]) -> bool:
    """Check if a fully-qualified class name is from a pom.xml-declared library."""
    for prefix in allowed_prefixes:
        if fqcn.startswith(prefix + ".") or fqcn == prefix:
            return True
    return False


def organize_imports(content: str) -> str:
    """Organize Java imports: pom.xml validation, replace, remove unused/duplicates, sort.

    Mimics STS/Eclipse Organize Imports with pom.xml enforcement:
    1. Replace known wrong imports (hone.bom → aondev.framework)
    2. BLOCK imports from libraries NOT in pom.xml (e.g., org.apache.poi)
    3. Remove duplicate imports
    4. Remove unused imports (not referenced in code body)
    5. Sort imports in standard Java order
    """
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

    # Workspace class map: ClassName → correct FQCN from actual PFY source files.
    # This is the STS "Organize Imports" oracle — no hardcoding needed.
    workspace_map = get_workspace_class_map()

    processed: dict[str, str] = {}
    for imp_line in import_lines:
        match = _IMPORT_RE.match(imp_line)
        if not match:
            continue
        static_prefix = match.group(1) or ""
        fqcn = match.group(2)

        # Step 1: apply known framework renames (e.g. hone.bom → aondev.framework)
        for old, new in _IMPORT_REPLACEMENTS:
            if fqcn == old:
                fqcn = new
                break

        # Step 2: heal wrong package using workspace source scan.
        # If the class name exists in the workspace with a *different* FQCN,
        # replace the import — just like STS resolves imports from the classpath.
        if "." in fqcn and not fqcn.endswith(".*"):
            simple_name = fqcn.rsplit(".", 1)[1]
            correct_fqcn = workspace_map.get(simple_name)
            if correct_fqcn and correct_fqcn != fqcn:
                logger.debug(
                    "[ORGANIZE_IMPORTS] auto-healed import: %s → %s", fqcn, correct_fqcn
                )
                fqcn = correct_fqcn

        if not _is_import_allowed(fqcn, allowed_prefixes):
            continue

        simple_name = fqcn.rsplit(".", 1)[-1] if "." in fqcn else fqcn
        if simple_name == "*" or simple_name in code_body:
            key = f"{static_prefix.strip()} {fqcn}".strip()
            if key not in processed:
                if static_prefix:
                    processed[key] = f"import static {fqcn};"
                else:
                    processed[key] = f"import {fqcn};"

    sorted_imports = sorted(processed.values(), key=lambda x: _import_sort_key(x.split()[-1].rstrip(";")))

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


def organize_imports_for_files(files: list[GeneratedFile]) -> None:
    """Apply organize_imports (with workspace-map healing) to all backend Java files in-place."""
    for gf in files:
        if gf.layer == "backend" and gf.file_path.endswith(".java"):
            gf.content = organize_imports(gf.content)


def postprocess_backend_files(files: list[GeneratedFile]) -> None:
    """Apply all programmatic post-processing to backend files in-place.

    Must be called after ANY code generation or fix that produces backend Java:
    - DaoImpl: rename bare CRUD method declarations to Mapper XML statement ids
    - ServiceImpl: fix bare DAO calls, remove log.error() before throw, enforce @Slf4j

    DaoImpl is ALWAYS processed first so that ServiceImpl can see the corrected method names.
    """
    dao_files = [gf for gf in files if gf.file_type == "dao_impl"]
    svc_files = [gf for gf in files if gf.file_type == "service_impl"
                 and gf.layer == "backend" and gf.file_path.endswith(".java")]

    # Phase 1: fix DaoImpl bare method declarations first
    for gf in dao_files:
        gf.content = _fix_bare_dao_method_decls(gf.content)

    # Phase 2: fix ServiceImpl (uses already-corrected DaoImpl method names)
    for gf in svc_files:
        gf.content = _fix_bare_dao_calls(gf.content, dao_files)
        gf.content = _remove_log_before_throw(gf.content)
        gf.content = _ensure_slf4j_service_impl(gf.content)
        gf.content = _ensure_log_debug_at_method_start(gf.content)
        gf.content = _remove_uuid_usage(gf.content)
        gf.content = _remove_manual_audit_fields(gf.content)


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


_BARE_DAO_CALL_RE = re.compile(
    r'(\w+(?:Dao|DaoImpl))\s*\.\s*'
    r'(insert|select|update|delete|selectOne|selectList|batchUpdateReturnSumAffectedRows)\s*\('
)

# Matches: super.selectList("realMethodName", ...) / super.insert("realMethodName", ...)
_SUPER_DELEGATE_RE = re.compile(
    r'super\s*\.\s*(?:selectList|selectOne|insert|update|delete|batchUpdateReturnSumAffectedRows)\s*\(\s*"(\w+)"'
)

# Matches bare DaoImpl method declarations:
#   public int insert(XxxResDto p) { ...
#   public List<XxxResDto> select(XxxReqDto p) { ...
_BARE_DAO_METHOD_DECL_RE = re.compile(
    r'(public\s+\S+\s+)(insert|update|delete|select|selectOne|selectList)(\s*\()'
)


def _fix_bare_dao_method_decls(content: str) -> str:
    """Rename bare CRUD method declarations in DaoImpl to the Mapper XML statement id.

    Looks at the super.xxx("realId", ...) inside each method body and renames the
    public method to match that realId.

    Before:
        public int insert(XxxResDto p) {
            return super.insert("insertEduPgm", p);
        }
    After:
        public int insertEduPgm(XxxResDto p) {
            return super.insert("insertEduPgm", p);
        }
    """
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    # Build a map: bare_method_name -> super delegate id (from method body)
    # We scan each method: find the declaration, then find the next super.xxx("id", ...) call
    lines = content.split('\n')
    bare_to_real: dict[str, str] = {}

    for i, line in enumerate(lines):
        m = _BARE_DAO_METHOD_DECL_RE.search(line)
        if not m:
            continue
        bare_name = m.group(2)
        # Search forward for super.xxx("realId", ...) within the next 5 lines
        for j in range(i, min(i + 6, len(lines))):
            sm = _SUPER_DELEGATE_RE.search(lines[j])
            if sm:
                real_id = sm.group(1)
                if real_id != bare_name:
                    bare_to_real[bare_name] = real_id
                break

    if not bare_to_real:
        return content

    def _replace_decl(m: re.Match) -> str:
        bare = m.group(2)
        real = bare_to_real.get(bare)
        if real:
            return m.group(1) + real + m.group(3)
        return m.group(0)

    return _BARE_DAO_METHOD_DECL_RE.sub(_replace_decl, content)


def _fix_bare_dao_calls(content: str, dao_files: list[GeneratedFile]) -> str:
    """Programmatically replace bare DAO base-class method calls with correct wrapper names.

    e.g.  cpmsEduRegLstDaoImpl.insert(dto)  →  cpmsEduRegLstDaoImpl.insertCpmsEduRegLst(dto)

    When a bare method maps to exactly one wrapper, replaces automatically.
    Ambiguous select* calls (multiple wrappers) are left unchanged for static_check to catch.
    """
    if not dao_files:
        return content

    # Build mapping: {dao_var_name: {bare_prefix: [wrapper_methods]}}
    var_to_map: dict[str, dict[str, list[str]]] = {}
    for gf in dao_files:
        class_match = re.search(r'public\s+class\s+(\w+DaoImpl)\b', gf.content)
        if not class_match:
            continue
        class_name = class_match.group(1)
        dao_var = class_name[0].lower() + class_name[1:]
        dao_var_short = (dao_var[:-4] if class_name.endswith("Impl") else dao_var)

        method_map: dict[str, list[str]] = {}
        for m in re.finditer(r'public\s+\S+\s+(\w+)\s*\(', gf.content):
            mname = m.group(1)
            if mname == class_name:
                continue
            for bare in ("insert", "select", "update", "delete"):
                if mname.lower().startswith(bare) and len(mname) > len(bare):
                    method_map.setdefault(bare, []).append(mname)

        for var in (dao_var, dao_var_short):
            var_to_map[var] = method_map

    def _replace(m: re.Match) -> str:
        dao_var = m.group(1)
        bare = m.group(2).lower()
        lookup = bare if bare in ("insert", "update", "delete") else "select"
        method_map = var_to_map.get(dao_var, {})
        wrappers = method_map.get(lookup, [])
        if len(wrappers) == 1:
            return f"{dao_var}.{wrappers[0]}("
        return m.group(0)

    return _BARE_DAO_CALL_RE.sub(_replace, content)


_LOG_USAGE_RE = re.compile(r'\blog\.(debug|info|warn|error|trace)\(')
_SLF4J_ANNOTATION_RE = re.compile(r'@Slf4j\b')
_SLF4J_IMPORT_RE = re.compile(r'import\s+lombok\.extern\.slf4j\.Slf4j\s*;')
_SERVICE_OR_REPO_ANNOTATION_RE = re.compile(r'(@(?:Service|Repository)\b)')
# Matches: log.error("...", e);\n    throw ...  (also log.warn)
_LOG_ERROR_BEFORE_THROW_RE = re.compile(
    r'[ \t]*log\.(?:error|warn)\s*\([^\n;]*\);\s*\n([ \t]*throw\s)',
    re.MULTILINE,
)


def _strip_old_logger(content: str) -> str:
    """Normalize line endings and remove manual Logger/LoggerFactory field + imports."""
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    has_logger_factory = 'LoggerFactory' in content
    has_logger_import = 'import org.slf4j.Logger' in content or 'import org.slf4j.LoggerFactory' in content
    if has_logger_factory or has_logger_import:
        logger.debug(
            "[STRIP_LOGGER] BEFORE strip — LoggerFactory present=%s, slf4j import present=%s",
            has_logger_factory, has_logger_import,
        )

    before = content
    # Remove: private static final Logger xxx = LoggerFactory.getLogger(...);
    content = re.sub(
        r'\n[ \t]*(?:private\s+)?static\s+final\s+Logger\s+\w+\s*=\s*LoggerFactory\.getLogger\s*\([^)]+\)\s*;[ \t]*',
        '\n',
        content,
    )
    if before != content:
        logger.debug("[STRIP_LOGGER] Logger field declaration removed successfully")
    elif has_logger_factory:
        # regex 미매치 — 원본 패턴 로깅 (ERROR 레벨로 반드시 남김)
        for line in before.splitlines():
            if 'LoggerFactory' in line:
                logger.error(
                    "[STRIP_LOGGER] !! regex DID NOT MATCH — raw line: %r", line
                )

    # Remove: import org.slf4j.Logger; / import org.slf4j.LoggerFactory;
    before2 = content
    content = re.sub(
        r'\nimport\s+org\.slf4j\.(?:Logger|LoggerFactory)\s*;[ \t]*',
        '\n',
        content,
    )
    if before2 != content:
        logger.debug("[STRIP_LOGGER] slf4j import(s) removed successfully")

    return content


def _ensure_slf4j_service_impl(content: str) -> str:
    """Unconditionally ensure @Slf4j annotation + import are present on a ServiceImpl.

    Every ServiceImpl MUST have @Slf4j — this is called regardless of whether log.xxx()
    calls exist, because _remove_log_before_throw may have already removed them.
    Steps:
      1. Strip old Logger/LoggerFactory field and imports.
      2. Inject @Slf4j before @Service/@Repository if not already present.
      3. Inject import lombok.extern.slf4j.Slf4j; after package declaration if not present.
    """
    content = _strip_old_logger(content)

    if not _SLF4J_ANNOTATION_RE.search(content):
        before = content
        content = _SERVICE_OR_REPO_ANNOTATION_RE.sub(
            lambda m: '@Slf4j\n' + m.group(1), content, count=1
        )
        if before == content:
            logger.error("[ENSURE_SLF4J] !! @Slf4j injection FAILED — @Service/@Repository not found in content")
        else:
            logger.debug("[ENSURE_SLF4J] @Slf4j annotation injected before @Service/@Repository")

    if not _SLF4J_IMPORT_RE.search(content):
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('package '):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, 'import lombok.extern.slf4j.Slf4j;')
        content = '\n'.join(lines)
        logger.debug("[ENSURE_SLF4J] import lombok.extern.slf4j.Slf4j; injected at line %d", insert_idx + 1)
    return content


_SERVICE_ID_METHOD_RE = re.compile(
    r'(@ServiceId\s*\([^)]+\)\s*\n'         # @ServiceId(...)
    r'(?:\s*@\w+(?:\([^)]*\))?\s*\n)*'      # optional other annotations (@ServiceName, @Transactional, etc.)
    r'\s*public\s+\S+\s+(\w+)\s*\('         # public ReturnType methodName(
    r'([^)]*)\)\s*\{)\s*\n'                 # params) {\n
    r'([ \t]*)',                              # capture indentation of first line in body
    re.MULTILINE,
)


def _ensure_log_debug_at_method_start(content: str) -> str:
    """Inject log.debug("Service Method : xxx, Input Param={}") at the start of every
    @ServiceId-annotated public method if not already present.
    """
    content = content.replace('\r\n', '\n').replace('\r', '\n')

    def _inject(m: re.Match) -> str:
        full_sig = m.group(1)
        method_name = m.group(2)
        params = m.group(3).strip()
        indent = m.group(4)

        # Check if log.debug already follows
        after_pos = m.end()
        next_chunk = content[after_pos:after_pos + 200]
        if next_chunk.lstrip().startswith('log.debug('):
            return m.group(0)

        # Build param name from first parameter: "CpmsXxxReqDto request" → "request"
        param_name = "param"
        if params:
            first_param = params.split(",")[0].strip()
            parts = first_param.split()
            if len(parts) >= 2:
                param_name = parts[-1]

        log_line = (
            f'{indent}log.debug("Service Method : {method_name}, '
            f'Input Param={{}}", {param_name}.toString());\n{indent}'
        )
        return full_sig + '\n' + log_line

    return _SERVICE_ID_METHOD_RE.sub(_inject, content)


def _remove_log_before_throw(content: str) -> str:
    """Remove log.error()/log.warn() lines immediately before any throw statement.

    These are redundant — the framework already logs thrown exceptions.
    Before:
        log.error("...", e);
        throw HscException.systemError("...", e);
    After:
        throw HscException.systemError("...", e);
    """
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    return _LOG_ERROR_BEFORE_THROW_RE.sub(lambda m: m.group(1), content)


# Matches: import java.util.UUID;
_UUID_IMPORT_RE = re.compile(r'\nimport\s+java\.util\.UUID\s*;[ \t]*', re.MULTILINE)
# Matches: UUID.randomUUID().toString()  or  UUID.randomUUID().toString().replace("-","")
_UUID_RANDOM_RE = re.compile(r'UUID\s*\.\s*randomUUID\s*\(\s*\)\s*\.toString\s*\(\s*\)(?:\s*\.\s*replace\s*\([^)]+\))?')
# Matches: lines that manually set audit fields — e.g. request.setFstCretDtm(...);\n
_MANUAL_AUDIT_LINE_RE = re.compile(
    r'^[ \t]*\w+\s*\.\s*set(?:FstCretDtm|FstCrtrId|LastMdfcDtm|LastMdfrId)\s*\([^)]*\)\s*;\s*\n',
    re.MULTILINE,
)
# Matches: DateTimeFormatter field declarations
_DATETIME_FORMATTER_FIELD_RE = re.compile(
    r'^[ \t]*private\s+static\s+final\s+DateTimeFormatter\s+\w+\s*=[^;]+;\s*\n',
    re.MULTILINE,
)
# Matches: import java.time.format.DateTimeFormatter;
_DATETIME_FORMATTER_IMPORT_RE = re.compile(
    r'\nimport\s+java\.time\.format\.DateTimeFormatter\s*;[ \t]*',
    re.MULTILINE,
)
# Matches if-blocks that check and set audit fields
_AUDIT_IF_BLOCK_RE = re.compile(
    r'^[ \t]*if\s*\(\s*\w+\.(?:getFstCretDtm|getFstCrtrId|getLastMdfcDtm|getLastMdfrId)\s*\(\s*\)'
    r'\s*(?:==\s*null|!=\s*null|\.isEmpty\s*\(\s*\))[^{]*\)\s*\{[^}]*'
    r'\.set(?:FstCretDtm|FstCrtrId|LastMdfcDtm|LastMdfrId)\s*\([^)]*\)\s*;[^}]*\}\s*\n',
    re.MULTILINE,
)


def _remove_uuid_usage(content: str) -> str:
    """Remove UUID import and replace UUID.randomUUID().toString() with empty string literal.

    LLM frequently generates UUID for ID fields despite being forbidden.
    The ID should come from DB sequence or already exist in the DTO.
    """
    content = _UUID_IMPORT_RE.sub('\n', content)
    content = _UUID_RANDOM_RE.sub('""', content)
    return content


def _remove_manual_audit_fields(content: str) -> str:
    """Remove manual audit field assignments and DateTimeFormatter usage.

    AuditBaseDto constructor handles fstCretDtm, fstCrtrId, lastMdfcDtm, lastMdfrId
    automatically. LLM frequently generates manual setting code that is redundant.
    """
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    content = _AUDIT_IF_BLOCK_RE.sub('', content)
    content = _MANUAL_AUDIT_LINE_RE.sub('', content)
    content = _DATETIME_FORMATTER_FIELD_RE.sub('', content)
    content = _DATETIME_FORMATTER_IMPORT_RE.sub('\n', content)
    # Clean up: remove now-unused LocalDateTime import if no other usage remains
    if 'LocalDateTime' not in content.replace('import java.time.LocalDateTime;', ''):
        content = re.sub(r'\nimport\s+java\.time\.LocalDateTime\s*;[ \t]*', '\n', content)
    return content


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
            "File types: dto_request|dto_response|dao_impl|service_impl|mapper_xml|db_init_sql|vue_types|vue_api|vue_search_form|vue_data_table|vue_data_table_utils|vue_sum_grid|vue_scss|vue_page\n"
            "NEVER generate dao or service interface files — ONLY dao_impl and service_impl.\n"
            "DaoImpl and ServiceImpl MUST NOT implement any interface. NO 'implements XxxDao' or 'implements XxxService'.\n\n"
            "FRONTEND MULTI-FILE STRUCTURE (CRITICAL — DO NOT generate a single monolithic vue_page):\n"
            "- vue_page:       index.vue — orchestrator ONLY (ContentHeader + provide/inject + import children). NO inline SearchForm/DataTable logic.\n"
            "- vue_search_form: SearchForm component (.vue) — search form UI + defineExpose + watch/setFieldValue\n"
            "- vue_data_table:  DataTable component (.vue) — grid display + virtual scroll + date preformat\n"
            "- vue_data_table_utils: utils/index.ts — getColumns, getRows helper functions for DataTable\n"
            "- vue_sum_grid:    SumGrid component (.vue) — CONDITIONAL, see rules below\n"
            "- vue_api:         API module (.ts) — axios calls, parameter conversion\n"
            "- vue_scss:        Page-level SCSS (.scss) — page layout styles\n"
            "- vue_types:       types.ts — TypeScript interfaces matching backend DTOs (generated by Data Engineer)\n"
            "Each vue_search_form, vue_data_table, vue_sum_grid component has its own paired .scss file (generated alongside the .vue).\n\n"
            "⚠️ vue_sum_grid GENERATION RULES (CRITICAL — DO NOT auto-generate):\n"
            "- Do NOT include vue_sum_grid unless the spec EXPLICITLY requires progress-status summary filters "
            "(e.g., clickable status counts like 저장/의뢰/요청확정/접수 that filter the data table).\n"
            "- Simple list screens, CRUD screens, excel upload screens, or screens without progress-status concepts "
            "MUST NOT have vue_sum_grid.\n"
            "- If unsure, do NOT include vue_sum_grid. It is better to omit it than to generate an unnecessary component.\n\n"
            "FRONTEND FILE NAMING RULES (CRITICAL — NO all-lowercase screenId):\n"
            "- screenId MUST be camelCase: e.g., cpmsEduPondgEdit (NOT cpmsedupondgedit)\n"
            "- PascalCase for Vue/SCSS component files: e.g., CpmsEduPondgEditSearchForm.vue / .scss\n"
            "- camelCase for API files: e.g., cpmsEduPondgEdit.ts\n"
            "- camelCase for component folder names: e.g., cpmsEduPondgEditSearchForm/\n\n"
            "Order by dependency chain: dto_request → dto_response → mapper_xml → dao_impl → service_impl → db_init_sql → vue_types → vue_api → vue_search_form → vue_data_table → vue_data_table_utils → vue_sum_grid → vue_scss → vue_page\n"
            "IMPORTANT: mapper_xml MUST be generated BEFORE dao_impl so that DaoImpl can reference all SQL statement IDs.\n"
            "IMPORTANT: db_init_sql MUST ALWAYS be included — every screen requires a MariaDB init SQL file at db/init.sql.\n"
            "IMPORTANT: Only plan files that are clearly derivable from the spec. If the spec does not mention a feature, do NOT plan files for it.\n"
            "  Do NOT invent screens, API endpoints, or components not in the spec. Omitting is better than guessing.\n"
            "dao_impl depends_on: [dto_request, dto_response, mapper_xml]\n"
            "service_impl depends_on: [dto_request, dto_response, dao_impl, mapper_xml]\n"
            "db_init_sql depends_on: [dto_request, dto_response]\n"
            "vue_api depends_on: [vue_types]\n"
            "vue_search_form depends_on: [vue_types, vue_api]\n"
            "vue_data_table depends_on: [vue_types, vue_api]\n"
            "vue_data_table_utils depends_on: [vue_types]\n"
            "vue_sum_grid depends_on: [vue_types, vue_api]  (only if needed)\n"
            "vue_scss depends_on: [vue_search_form, vue_data_table]\n"
            "vue_page depends_on: [vue_search_form, vue_data_table, vue_api, vue_scss]\n\n"
            "BACKEND FILE PATH RULES (follow biz/sample structure EXACTLY — NO screen-level subdirectory):\n"
            "  DAO Impl:        src/main/java/biz/{module}/dao/{ClassName}DaoImpl.java\n"
            "  Request DTO:     src/main/java/biz/{module}/dto/request/{ClassName}ReqDto.java\n"
            "  Response DTO:    src/main/java/biz/{module}/dto/response/{ClassName}ResDto.java\n"
            "  Service Impl:    src/main/java/biz/{module}/service/{ClassName}ServiceImpl.java\n"
            "  Mapper XML:      src/main/resources/biz/{module}/mybatis/mappers/{ClassName}Mapper.xml\n"
            "  DB Init SQL:     db/init.sql  (project root level — NOT under src/main/resources)\n\n"
            "BACKEND PACKAGE RULES (NO screen-level package):\n"
            "  dao_impl package:    biz.{module}.dao\n"
            "  dto_request package: biz.{module}.dto.request\n"
            "  dto_response package:biz.{module}.dto.response\n"
            "  service_impl package:biz.{module}.service\n\n"
            "Example for module 'edu':\n"
            "  src/main/java/biz/edu/dao/CpmsEduPgmRsltLstDaoImpl.java        (package biz.edu.dao)\n"
            "  src/main/java/biz/edu/dto/request/CpmsEduPgmRsltLstReqDto.java (package biz.edu.dto.request)\n"
            "  src/main/java/biz/edu/dto/response/CpmsEduPgmRsltLstResDto.java(package biz.edu.dto.response)\n"
            "  src/main/java/biz/edu/service/CpmsEduPgmRsltLstServiceImpl.java(package biz.edu.service)\n"
            "  src/main/resources/biz/edu/mybatis/mappers/CpmsEduPgmRsltLstMapper.xml\n\n"
            "FRONTEND FILE PATH RULES (all paths use camelCase screenId):\n"
            "  vue_page:             src/pages/{module}/{category}/{screenId}/index.vue\n"
            "  vue_scss:             src/pages/{module}/{category}/{screenId}/{screenId}.scss\n"
            "  vue_search_form:      src/pages/{module}/{category}/{screenId}/components/{screenId}SearchForm/{ScreenId}SearchForm.vue\n"
            "  vue_data_table:       src/pages/{module}/{category}/{screenId}/components/{screenId}DataTable/{ScreenId}DataTable.vue\n"
            "  vue_data_table_utils: src/pages/{module}/{category}/{screenId}/components/{screenId}DataTable/utils/index.ts\n"
            "  vue_sum_grid:         src/pages/{module}/{category}/{screenId}/components/{screenId}SumGrid/{ScreenId}SumGrid.vue\n"
            "  vue_api:              src/api/pages/{module}/{category}/{screenId}.ts\n"
            "  vue_types:            src/api/pages/{module}/{category}/{screenId}Types.ts\n"
            "  (ScreenId = PascalCase of screenId, e.g., screenId=cpmsEduPondgEdit → ScreenId=CpmsEduPondgEdit)\n\n"
            "FILE NAMING RULES (CRITICAL):\n"
            "- The file_path filename (without .java) MUST be the exact Java class name.\n"
            "- Class names: ReqDto suffix for request DTOs, ResDto suffix for response DTOs.\n"
            "- DAO impl class: {ClassName}DaoImpl  Service impl class: {ClassName}ServiceImpl\n"
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

    _BACKEND_TYPES = {"dto_request", "dto_response", "dao_impl", "service_impl", "mapper_xml"}

    _TYPE_ORDER = {
        "dto_request": 0,
        "dto_response": 1,
        "mapper_xml": 2,
        "dao_impl": 3,
        "service_impl": 4,
    }

    def _get_my_files(self, plan: CodeGenPlan) -> list[CodeGenPlanFile]:
        files = [f for f in plan.files if f.file_type in self._BACKEND_TYPES]
        files.sort(key=lambda f: self._TYPE_ORDER.get(f.file_type, 99))
        return files

    async def execute(self, ctx: SharedContext, on_chunk: callable | None = None) -> list[GeneratedFile]:
        assert ctx.plan is not None
        my_files = self._get_my_files(ctx.plan)
        naming = get_naming_context()

        system = (
            "You are a senior Backend Engineer specializing in PFY Spring Boot + MyBatis projects.\n"
            "You generate Java source files following PFY coding patterns strictly.\n\n"
            "╔══════════════════════════════════════════════════════════╗\n"
            "║  TOP-PRIORITY RULES — VIOLATING ANY = REJECTED CODE    ║\n"
            "╚══════════════════════════════════════════════════════════╝\n"
            "1. LOGGING: ServiceImpl MUST use @Slf4j (Lombok) — NEVER LoggerFactory.getLogger().\n"
            "   NEVER write: private static final Logger log = LoggerFactory.getLogger(Xxx.class);\n"
            "   NEVER import org.slf4j.Logger or org.slf4j.LoggerFactory.\n"
            "   EVERY public method MUST start with log.debug(\"Service Method : {methodName}, Input Param={}\", param.toString());\n\n"
            "2. EXCEPTION: NEVER log.error()/log.warn() before throw HscException.\n"
            "   WRONG:   log.error(\"msg\", e); throw HscException.systemError(\"msg\", e);\n"
            "   CORRECT: throw HscException.systemError(\"msg\", e);\n\n"
            "3. DAO METHOD NAMES: NEVER bare CRUD verb. Always append domain noun.\n"
            "   WRONG:  public int insert(...)       CORRECT: public int insertEduPgm(...)\n"
            "   WRONG:  public List select(...)      CORRECT: public List selectEduPgmList(...)\n\n"
            "4. SERVICE→DAO CALLS: NEVER call bare base-class methods on DAO variable.\n"
            "   WRONG:  daoImpl.insert(dto)          CORRECT: daoImpl.insertEduPgm(dto)\n"
            "   WRONG:  daoImpl.select(dto)          CORRECT: daoImpl.selectEduPgmList(dto)\n\n"
            "5. UUID: NEVER use java.util.UUID — NEVER import java.util.UUID. Use String for all ID fields.\n"
            "   WRONG:  request.setId(UUID.randomUUID().toString());\n"
            "   CORRECT: ID values come from DB sequence or are already in the DTO.\n\n"
            "6. SAVE METHOD: ServiceImpl save() MUST accept List<ResDto>, NOT single ReqDto.\n"
            "   Use ResDto.getStatus() + CommonUtils.filterByStatus() + GridStatus pattern.\n"
            "   WRONG:  public void save(ReqDto request) { if(status==\"I\") dao.insert(request); }\n"
            "   CORRECT: public void save(List<ResDto> list) {\n"
            "       List<ResDto> insertList = CommonUtils.filterByStatus(list, GridStatus.INSERTED);\n"
            "       List<ResDto> updateList = CommonUtils.filterByStatus(list, GridStatus.UPDATED);\n"
            "       List<ResDto> deleteList = CommonUtils.filterByStatus(list, GridStatus.DELETED);\n"
            "       for(ResDto dto : insertList) { dao.insertXxx(dto); }\n"
            "       dao.updateXxx(updateList); dao.deleteXxx(deleteList);\n"
            "   }\n\n"
            "7. AUDIT FIELDS: NEVER manually set fstCretDtm/lastMdfcDtm/fstCrtrId/lastMdfrId.\n"
            "   AuditBaseDto constructor sets these automatically. NEVER use DateTimeFormatter/LocalDateTime for audit.\n"
            "   WRONG:  request.setFstCretDtm(LocalDateTime.now().format(formatter));\n"
            "   WRONG:  request.setLastMdfrId(\"SYSTEM\");\n"
            "   CORRECT: (do nothing — AuditBaseDto handles it)\n\n"
            "8. DTO FIELD CONSISTENCY — CRITICAL: NEVER call getter/setter for a field that is not declared in the DTO.\n"
            "   Every dto.getXxx() and dto.setXxx() call MUST correspond to 'private <Type> xxx;' in the DTO class.\n"
            "   If you need a field in ServiceImpl that doesn't exist in the DTO, ADD it to the DTO (not remove the call).\n"
            "   WRONG:  dto.setDuplicate(true);              // if 'duplicate' field doesn't exist in DTO\n"
            "   WRONG:  String x = dto.getScreenCode();     // if 'screenCode' field doesn't exist in DTO\n"
            "   CORRECT: Add 'private Boolean duplicate;' to the DTO class, then call dto.setDuplicate(true);\n"
            "   RULE: When generating ServiceImpl, cross-check EVERY get/set call against the DTO fields you generated.\n\n"
            "9. SERVICE ↔ DAO TYPE CONTRACT — CRITICAL:\n"
            "   The parameter type and return type of every DaoImpl method call in ServiceImpl\n"
            "   MUST exactly match the DaoImpl method signature.\n"
            "   WRONG:  List<ResDto> list = daoImpl.selectList(request);  // if DaoImpl returns int\n"
            "   WRONG:  daoImpl.insertXxx(reqDto);  // if DaoImpl expects ResDto\n"
            "   CORRECT: Match types exactly — check the DaoImpl source in Dependencies below.\n"
            "   When writing ServiceImpl, for each daoImpl.xxx() call:\n"
            "     a) Verify the method EXISTS in DaoImpl. If not, you MUST also add it to DaoImpl.\n"
            "     b) Use the EXACT same parameter type DaoImpl declares.\n"
            "     c) Assign the result to a variable of the EXACT return type DaoImpl declares.\n\n"
            "10. GRID STATUS: NEVER use getSortDirection() or manual String comparison for CRUD status.\n"
            "   Use ResDto.getStatus() with GridStatus enum + CommonUtils.filterByStatus().\n"
            "   WRONG:  String status = request.getSortDirection(); if(\"D\".equals(status))...\n"
            "   CORRECT: CommonUtils.filterByStatus(list, GridStatus.DELETED)\n\n"
            "11. DO NOT GUESS OR FABRICATE — CRITICAL:\n"
            "   If you are unsure about a class name, package path, method signature, DTO field, annotation, or any API detail:\n"
            "   → OMIT it entirely. Leave a TODO comment instead.\n"
            "   → NEVER invent a class, method, field, import, or annotation that you have not seen in the provided context.\n"
            "   → NEVER guess a package path — if you don't know the exact package, do NOT generate the import.\n"
            "   → It is ALWAYS better to produce incomplete but correct code than complete but broken code.\n"
            "   WRONG:  import com.example.some.GuessedClass;  // fabricated because it 'seemed right'\n"
            "   CORRECT: // TODO: verify import for GuessedClass\n\n"
            f"--- NAMING CONVENTIONS ---\n{naming}\n--- END ---\n\n"
            f"--- pom.xml DEPENDENCIES (ONLY these are available — do NOT import anything else) ---\n{get_pom_dependencies()}\n--- END ---\n\n"
            "IMPORT RULES — NEVER VIOLATE (wrong imports = compilation failure):\n"
            "- ONLY import from libraries listed in pom.xml above. Any import from a library NOT in pom.xml will fail.\n"
            "- Key imports from pom.xml libraries (aondev-framework):\n"
            "    aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport  (aondev-framework-dao)\n"
            "    aondev.framework.annotation.ServiceId, aondev.framework.annotation.ServiceName (aondev-framework-core)\n"
            "    com.common.dto.base.SearchBaseDto, com.common.dto.base.AuditBaseDto (pfy-fw-base)\n"
            "    com.common.sy.CommonUtils, com.common.sy.GridStatus (pfy-fw-base — NOT com.common.dto.base)\n"
            "- NEVER import from hone.bom.* — use aondev.framework.* instead:\n"
            "    WRONG:   import hone.bom.annotation.ServiceId;      → CORRECT: import aondev.framework.annotation.ServiceId;\n"
            "    WRONG:   import hone.bom.annotation.ServiceName;    → CORRECT: import aondev.framework.annotation.ServiceName;\n"
            "    WRONG:   import hone.bom.dao.mybatis.support.*;     → CORRECT: import aondev.framework.dao.mybatis.support.*;\n"
            "- NEVER import CommonUtils or GridStatus from com.common.dto.base — correct package is com.common.sy:\n"
            "    WRONG:   import com.common.dto.base.CommonUtils;    → CORRECT: import com.common.sy.CommonUtils;\n"
            "    WRONG:   import com.common.dto.base.GridStatus;     → CORRECT: import com.common.sy.GridStatus;\n"
            "- NEVER import from: com.mnwise.*, com.posdata.*, has.fw.*, biz.common.dto.*\n"
            "- NEVER import AbstractSqlSessionDaoSupport from anywhere other than aondev.framework.dao.mybatis.support\n"
            "- For exception handling, use: import hsc.framework.online.error.HscException;\n\n"
            "CLASS/FILE NAME RULES — NEVER VIOLATE:\n"
            "- The Java class name MUST exactly match the file name (case-sensitive).\n"
            "- The package declaration MUST exactly match the directory structure (NO screen-level package):\n"
            "    dao_impl:     package biz.{module}.dao;\n"
            "    dto_request:  package biz.{module}.dto.request;\n"
            "    dto_response: package biz.{module}.dto.response;\n"
            "    service_impl: package biz.{module}.service;\n"
            "- When importing between files in same module, use full package path:\n"
            "    import biz.{module}.dto.request.{ClassName};\n"
            "    import biz.{module}.dto.response.{ClassName};\n"
            "- Mapper XML namespace MUST be the full DaoImpl class path:\n"
            "    e.g., namespace=\"biz.edu.dao.CpmsEduPgmRsltLstDaoImpl\"\n\n"
            "STRICT RULES:\n"
            "- Output ONLY the file content. No markdown fences. No BOM characters.\n"
            "- DTO: @Getter, @Setter, @ToString. Class name MUST exactly match the file name (e.g., file CpmsEduRegLstReqDto.java → class CpmsEduRegLstReqDto).\n"
            "- Request DTO extends SearchBaseDto (import com.common.dto.base.SearchBaseDto)\n"
            "- Response DTO extends AuditBaseDto (import com.common.dto.base.AuditBaseDto)\n"
            "- Service impl: @Service, @ServiceId(\"ScreenCode/method\"), @ServiceName(\"설명\"), @Transactional on CUD.\n"
            "- DAO impl: @Repository, extends AbstractSqlSessionDaoSupport ONLY. NO implements clause.\n"
            "    CORRECT:  public class XxxDaoImpl extends AbstractSqlSessionDaoSupport {\n"
            "    WRONG:    public class XxxDaoImpl extends AbstractSqlSessionDaoSupport implements XxxDao {\n"
            "  DaoImpl MUST NOT implement any interface. There is NO DAO interface — only DaoImpl.\n"
            "  Each DaoImpl method delegates to super.selectList/selectOne/insert/update/delete/batchUpdateReturnSumAffectedRows.\n"
            "\n"
            "CRITICAL DAO RULES — DaoImpl is NOT limited to basic CRUD:\n"
            "  DaoImpl MUST have a public Java method for EVERY <select>/<insert>/<update>/<delete> statement in the Mapper XML.\n"
            "  When a Mapper XML is provided as dependency, read ALL its SQL statement IDs and create a matching DAO method for each one.\n"
            "\n"
            "  ★ DaoImpl PUBLIC METHOD NAMING — ABSOLUTE RULE ★\n"
            "  NEVER name a public DaoImpl method with a bare CRUD verb alone.\n"
            "  ALWAYS append a domain noun that matches the Mapper XML statement id EXACTLY.\n"
            "  WRONG → CORRECT examples:\n"
            "    public int insert(...)      →  public int insertEduPgm(...)\n"
            "    public int update(...)      →  public int updateEduPgm(...)\n"
            "    public int delete(...)      →  public int deleteEduPgm(...)\n"
            "    public List<?> select(...)  →  public List<?> selectEduPgmList(...)\n"
            "    public List<?> selectList(...)  →  public List<?> selectEduPgmList(...)\n"
            "    public Xxx selectOne(...)   →  public Xxx selectEduPgm(...)\n"
            "  The public method name IS the Mapper XML <statement id>. They must match exactly.\n"
            "\n"
            "  ★ ServiceImpl DAO CALL RULE ★\n"
            "  ServiceImpl MUST call the EXACT public method name from DaoImpl — never the bare super-class methods.\n"
            "  WRONG: daoImpl.insert(dto)         →  CORRECT: daoImpl.insertEduPgm(dto)\n"
            "  WRONG: daoImpl.select(dto)         →  CORRECT: daoImpl.selectEduPgmList(dto)\n"
            "  WRONG: daoImpl.update(list)        →  CORRECT: daoImpl.updateEduPgm(list)\n"
            "  WRONG: daoImpl.delete(list)        →  CORRECT: daoImpl.deleteEduPgm(list)\n"
            "  WRONG: daoImpl.selectOne(dto)      →  CORRECT: daoImpl.selectEduPgm(dto)\n"
            "  WRONG: daoImpl.selectList(dto)     →  CORRECT: daoImpl.selectEduPgmList(dto)\n"
            "\n"
            "  Typical methods include (not limited to):\n"
            "    - selectXxxList(ReqDto)      → super.selectList(\"selectXxxList\", param)\n"
            "    - selectXxx(ReqDto)           → super.selectOne(\"selectXxx\", param)\n"
            "    - selectDuplicateCount(ResDto) → super.selectOne(\"selectDuplicateCount\", param)  // PK duplicate check\n"
            "    - selectXxxByYyy(ReqDto)      → super.selectOne(\"selectXxxByYyy\", param)       // specific lookup\n"
            "    - insertXxx(ResDto)           → super.insert(\"insertXxx\", param)\n"
            "    - updateXxx(List<ResDto>)     → super.batchUpdateReturnSumAffectedRows(\"updateXxx\", param)\n"
            "    - deleteXxx(List<ResDto>)     → super.batchUpdateReturnSumAffectedRows(\"deleteXxx\", param)\n"
            "  The first argument to super.selectList/selectOne/insert/update/delete MUST exactly match the Mapper XML statement id.\n"
            "  Example: Mapper has <select id=\"selectDuplicateCount\"> → DAO needs:\n"
            "    public int selectDuplicateCount(XxxResDto param) { return super.selectOne(\"selectDuplicateCount\", param); }\n"
            "  If the spec requires duplicate check, count queries, specific lookups, etc. — DAO MUST have those methods.\n"
            "  ServiceImpl will ONLY call methods that exist in DaoImpl, so DaoImpl must be complete.\n"
            "- Do NOT generate DAO interface or Service interface files — only DaoImpl and ServiceImpl.\n"
            "- All fields used in ServiceImpl MUST exist in the corresponding DTO.\n"
            "- NEVER call getter/setter for a field that does NOT exist in the DTO:\n"
            "    If DTO has 'private String eduNm;' → dto.getEduNm() and dto.setEduNm() are OK.\n"
            "    If DTO does NOT have 'page' field → dto.getPage() and dto.setPage() are COMPILATION ERRORS.\n"
            "    BEFORE writing any .getXxx() or .setXxx(), verify the field exists in the DTO you defined.\n"
            "- NEVER use java.util.UUID — use String for all ID fields.\n"
            "\nCRITICAL CODE QUALITY RULES (violations = immediate compilation failure):\n"
            "- ServiceImpl methods MUST only call DaoImpl methods that actually exist in the DaoImpl class you generated.\n"
            "- DAO layer handles ONLY DB operations (selectList/selectOne/insert/update/delete via MyBatis).\n"
            "  DAO MUST NOT handle file I/O, MultipartFile, HTTP, or any non-DB logic.\n"
            "- NEVER use 'Object' as variable type for method return values — use the actual typed return type.\n"
            "- NEVER create recursive/self-referencing calls — a method must not call itself.\n"
            "- Return type of a method MUST match the variable type that receives the result.\n"
            "- Parameter types in method calls MUST match the method signature.\n"
            "\nKNOWN ERROR PREVENTION (DO NOT):\n"
            "- DO NOT use bare @Service with bean name string parameter.\n"
            "- DO NOT omit @Transactional — add @Transactional(readOnly=true) for queries, @Transactional for CUD.\n"
            "- DO NOT forget @ServiceId and @ServiceName on every public Service method.\n"
            "- EVERY public method in ServiceImpl MUST have @ServiceId + @ServiceName directly above it.\n"
            "  WRONG: public void save(dto) { saveRecord(dto); }  ← alias with no annotation → DELETE\n"
            "  WRONG: public List search(req) { return getList(req); }  ← wrapper with no annotation → DELETE\n"
            "  These add zero value; if a method is public it MUST have @ServiceId. If it does not, remove it.\n"
            "- Private helper methods (e.g. private void validateXxx(), private void populateXxx()) are fine.\n"
            "- ServiceImpl logging: use @Slf4j + log.debug() at method start. (See TOP-PRIORITY RULES above)\n"
            "- DO NOT use bare < or > in Mapper XML — wrap in CDATA: <![CDATA[<=]]>\n"
            "- DO NOT hardcode all WHERE conditions — use <if test=\"param != null and param != ''\"> for optional filters.\n"
            "- DO NOT use String for amounts — use BigDecimal for monetary fields.\n"
            "- DO NOT use inconsistent package paths — package must exactly match directory path.\n"
            "\n"
            "╔══════════════════════════════════════════════════════════╗\n"
            "║  REMINDER — CHECK BEFORE EVERY FILE OUTPUT              ║\n"
            "╚══════════════════════════════════════════════════════════╝\n"
            "□ @Slf4j? (NO LoggerFactory, NO import org.slf4j.*)\n"
            "□ log.debug(\"Service Method : xxx\") as FIRST line in every public method?\n"
            "□ NO log.error/warn before throw?\n"
            "□ DaoImpl method name → domain noun? (NEVER bare insert/select/update/delete)\n"
            "□ ServiceImpl DAO call → full wrapper name? (NEVER daoImpl.insert())\n"
            "□ NO java.util.UUID — use String\n"
            "□ save() takes List<ResDto>? (NOT single ReqDto)\n"
            "□ GridStatus + CommonUtils.filterByStatus()? (NOT getSortDirection())\n"
            "□ NO manual fstCretDtm/lastMdfcDtm/fstCrtrId/lastMdfrId setting?\n"
            "□ NO DateTimeFormatter/LocalDateTime.now().format() in ServiceImpl?\n"
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

            # For dao_impl: always inject mapper_xml so DAO has every SQL statement ID
            if file_entry.file_type == "dao_impl":
                included_paths = {dp for dp in file_entry.depends_on}
                for path, gf in ctx.generated_files.items():
                    if gf.file_type == "mapper_xml" and path not in included_paths:
                        dep_parts.append(
                            f"--- {gf.file_path} (MAPPER XML — DaoImpl MUST have a method for EVERY SQL statement id in this file) ---\n{gf.content}"
                        )

            # For service_impl: always inject dao_impl + mapper_xml for cross-reference
            if file_entry.file_type == "service_impl":
                included_paths = {dp for dp in file_entry.depends_on}
                for path, gf in ctx.generated_files.items():
                    if gf.file_type in ("dao_impl", "mapper_xml") and path not in included_paths:
                        dep_parts.append(f"--- {gf.file_path} ---\n{gf.content}")

            if dep_parts:
                deps_text = "\n\n".join(dep_parts)

            # Include DB schema for context
            schema_ctx = f"\nDB Schema:\n{ctx.db_schema}\n" if ctx.db_schema else ""

            file_guide = get_context_for_file_type(file_entry.file_type)

            user = (
                f"Specification:\n{ctx.spec_markdown}\n{schema_ctx}\n"
            )
            if deps_text:
                user += f"Dependencies:\n{deps_text}\n\n"
            user += f"Generate: {file_entry.file_path}\nType: {file_entry.file_type}\nDescription: {file_entry.description}\n"

            if file_guide:
                user += f"\n--- CODING GUIDE ({file_entry.file_type}) ---\n{file_guide}\n--- END GUIDE ---\n"

            # Type-specific generation instructions
            if file_entry.file_type == "dao_impl":
                # Extract ALL SQL statement IDs from Mapper XML and list them explicitly
                mapper_ids: list[str] = []
                for path, gf in ctx.generated_files.items():
                    if gf.file_type == "mapper_xml":
                        for m in re.finditer(
                            r'<(select|insert|update|delete)\s+id\s*=\s*"([^"]+)"',
                            gf.content,
                        ):
                            mapper_ids.append(f"  - <{m.group(1)} id=\"{m.group(2)}\">")

                if mapper_ids:
                    ids_list = "\n".join(mapper_ids)
                    user += (
                        f"\n=== MANDATORY: DaoImpl must have ALL these methods ===\n"
                        f"The Mapper XML contains these SQL statements:\n{ids_list}\n\n"
                        f"You MUST create a public Java method for EACH statement above. "
                        f"There must be {len(mapper_ids)} methods in total (one per SQL statement).\n"
                        f"For <select> with resultType=int or COUNT → return type is int, use super.selectOne()\n"
                        f"For <select> with resultType=*Dto (single) → return type is Dto, use super.selectOne()\n"
                        f"For <select> with resultType=*Dto (list) → return type is List<Dto>, use super.selectList()\n"
                        f"For <insert> → return type is int, use super.insert()\n"
                        f"For <update>/<delete> with List param → return type is int, use super.batchUpdateReturnSumAffectedRows()\n"
                        f"For <update>/<delete> with single param → return type is int, use super.update() or super.delete()\n"
                        f"=== END MANDATORY ===\n"
                    )
                else:
                    user += (
                        "\nIMPORTANT: Read the Mapper XML dependency above carefully. "
                        "Create a public Java method for EVERY SQL statement ID in the Mapper XML. "
                        "Do NOT just create basic select/insert/update/delete.\n"
                    )

                user += (
                    "\n=== COMPLETE DaoImpl EXAMPLE (follow this pattern exactly) ===\n"
                    "package biz.sy.dao;\n\n"
                    "import org.springframework.stereotype.Repository;\n"
                    "import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;\n"
                    "import biz.sy.dto.request.WindowReqDto;\n"
                    "import biz.sy.dto.response.WindowResDto;\n\n"
                    "import java.util.List;\n\n"
                    "@Repository\n"
                    "public class SYAR030DaoImpl extends AbstractSqlSessionDaoSupport {\n\n"
                    "    public List<WindowResDto> selectWinList(WindowReqDto param) {\n"
                    "        return super.selectList(\"selectWinList\", param);\n"
                    "    }\n\n"
                    "    public boolean checkDuplicateWindowPk(WindowResDto param) {\n"
                    "        int check = super.selectOne(\"checkDuplicateWindowPk\", param);\n"
                    "        return (check != 0);\n"
                    "    }\n\n"
                    "    public int insertWindow(WindowResDto param) {\n"
                    "        return super.insert(\"insertWindow\", param);\n"
                    "    }\n\n"
                    "    public int updateWindow(List<WindowResDto> param) {\n"
                    "        return super.batchUpdateReturnSumAffectedRows(\"updateWindow\", param);\n"
                    "    }\n\n"
                    "    public int deleteWindow(List<WindowResDto> param) {\n"
                    "        return super.batchUpdateReturnSumAffectedRows(\"deleteWindow\", param);\n"
                    "    }\n"
                    "}\n"
                    "=== END EXAMPLE ===\n"
                    "NOTE: method names (selectWinList, insertWindow, etc.) match Mapper XML statement ids EXACTLY.\n"
                    "NEVER use bare names like insert(), select(), update(), delete().\n"
                )

            elif file_entry.file_type == "service_impl":
                # Extract DAO method signatures and list them explicitly
                dao_method_sigs: list[str] = []
                dao_var_name = ""
                for path, gf in ctx.generated_files.items():
                    if gf.file_type == "dao_impl":
                        class_match = re.search(r'public\s+class\s+(\w+DaoImpl)\b', gf.content)
                        class_name = class_match.group(1) if class_match else ""
                        if class_name:
                            dao_var_name = class_name[0].lower() + class_name[1:]
                        for m in re.finditer(
                            r'public\s+(\S+)\s+(\w+)\s*\(([^)]*)\)',
                            gf.content,
                        ):
                            ret_type = m.group(1)
                            method_name = m.group(2)
                            params = m.group(3).strip()
                            if class_name and method_name == class_name:
                                continue  # skip constructor
                            dao_method_sigs.append(
                                f"  {dao_var_name}.{method_name}({params})  // returns {ret_type}"
                            )

                if dao_method_sigs:
                    sigs_list = "\n".join(dao_method_sigs)
                    user += (
                        f"\n=== AVAILABLE DAO METHODS — TYPE CONTRACT (read carefully) ===\n"
                        f"Format: daoVar.methodName(paramType param)  // returns ReturnType\n"
                        f"{sigs_list}\n\n"
                        f"TYPE-MATCHING RULES (violations = compile error):\n"
                        f"  1. Assign the result to a variable whose type EXACTLY matches '// returns <X>'.\n"
                        f"     e.g. if returns List<FooResDto> → 'List<FooResDto> result = {dao_var_name}.selectFoo(req);'\n"
                        f"  2. Pass a parameter whose type matches the declared param type in '({{}})'\n"
                        f"     e.g. if param is 'FooReqDto req' → call with the ReqDto variable, NOT ResDto.\n"
                        f"  3. If a method you need is NOT in this list, you MUST add it to the DaoImpl as well.\n"
                        f"     Generate the missing DaoImpl method in the DaoImpl file at the same time.\n\n"
                        f"FORBIDDEN — DO NOT CALL THESE (AbstractSqlSessionDaoSupport internal methods, NOT accessible from Service):\n"
                        f"  {dao_var_name}.insert(...)     ← WRONG (bare base class method)\n"
                        f"  {dao_var_name}.select(...)     ← WRONG (bare base class method)\n"
                        f"  {dao_var_name}.update(...)     ← WRONG (bare base class method)\n"
                        f"  {dao_var_name}.delete(...)     ← WRONG (bare base class method)\n"
                        f"  {dao_var_name}.selectOne(...)  ← WRONG (bare base class method)\n"
                        f"  {dao_var_name}.selectList(...) ← WRONG (bare base class method)\n"
                        f"You MUST use the full wrapper method names listed above ONLY.\n\n"
                        f"=== PUBLIC METHOD RULE ===\n"
                        f"EVERY public method you write in this ServiceImpl MUST have @ServiceId + @ServiceName above it.\n"
                        f"DO NOT create alias/wrapper public methods that just delegate to other methods:\n"
                        f"  WRONG: public void save(dto) {{ saveRecord(dto); }}  ← DELETE THIS\n"
                        f"  WRONG: public List search(req) {{ return getList(req); }}  ← DELETE THIS\n"
                        f"If a public method has no @ServiceId, it will be caught as a static error and must be deleted.\n"
                        f"=== END ===\n"
                    )
                else:
                    user += (
                        "\nIMPORTANT: Read the DaoImpl dependency above carefully. "
                        "You MUST only call methods that actually exist in the DaoImpl class.\n"
                        "FORBIDDEN: Do NOT call bare insert()/select()/update()/delete() — "
                        "these are AbstractSqlSessionDaoSupport protected methods, not accessible from ServiceImpl.\n"
                        "Use the full wrapper method names defined in DaoImpl (e.g., insertCpmsXxx, selectCpmsXxxLst).\n"
                    )

                user += (
                    "\n=== COMPLETE ServiceImpl EXAMPLE (follow this pattern exactly) ===\n"
                    "package biz.sy.service;\n\n"
                    "import lombok.extern.slf4j.Slf4j;\n"
                    "import org.springframework.beans.factory.annotation.Autowired;\n"
                    "import org.springframework.stereotype.Service;\n"
                    "import org.springframework.transaction.annotation.Transactional;\n"
                    "import aondev.framework.annotation.ServiceId;\n"
                    "import aondev.framework.annotation.ServiceName;\n"
                    "import hsc.framework.online.error.HscException;\n"
                    "import biz.sy.dao.SYAR030DaoImpl;\n"
                    "import biz.sy.dto.request.WindowReqDto;\n"
                    "import biz.sy.dto.response.WindowResDto;\n"
                    "import com.common.sy.CommonUtils;\n"
                    "import com.common.sy.GridStatus;\n\n"
                    "import java.util.Arrays;\n"
                    "import java.util.List;\n\n"
                    "@Slf4j\n"
                    "@Service\n"
                    "public class SYAR030ServiceImpl {\n\n"
                    "    @Autowired\n"
                    "    private SYAR030DaoImpl syar030DaoImpl;\n\n"
                    "    @ServiceId(\"SYAR030/selectWindowList\")\n"
                    "    @ServiceName(\"화면 목록 조회\")\n"
                    "    @Transactional(readOnly = true)\n"
                    "    public List<WindowResDto> selectWindowList(WindowReqDto request) {\n"
                    "        log.debug(\"Service Method : selectWindowList, Input Param={}\", request.toString());\n"
                    "        try {\n"
                    "            return syar030DaoImpl.selectWinList(request);\n"
                    "        } catch (Exception e) {\n"
                    "            throw HscException.systemError(\"화면 목록 조회 중 오류가 발생했습니다\", e);\n"
                    "        }\n"
                    "    }\n\n"
                    "    @ServiceId(\"SYAR030/saveWindowList\")\n"
                    "    @ServiceName(\"화면 저장\")\n"
                    "    @Transactional\n"
                    "    public void saveWindowList(List<WindowResDto> list) {\n"
                    "        log.debug(\"Service Method : saveWindowList, Input Param={}\", list.toString());\n"
                    "        List<WindowResDto> insertList = CommonUtils.filterByStatus(list, GridStatus.INSERTED);\n"
                    "        List<WindowResDto> updateList = CommonUtils.filterByStatus(list, GridStatus.UPDATED);\n"
                    "        List<WindowResDto> deleteList = CommonUtils.filterByStatus(list, GridStatus.DELETED);\n\n"
                    "        for (WindowResDto dto : insertList) {\n"
                    "            if (syar030DaoImpl.checkDuplicateWindowPk(dto)) {\n"
                    "                throw new HscException(\"CM0001\");\n"
                    "            }\n"
                    "            syar030DaoImpl.insertWindow(dto);\n"
                    "        }\n"
                    "        syar030DaoImpl.updateWindow(updateList);\n"
                    "        syar030DaoImpl.deleteWindow(deleteList);\n"
                    "    }\n"
                    "}\n"
                    "=== END EXAMPLE ===\n"
                    "KEY PATTERNS — YOUR OUTPUT MUST MATCH ALL OF THESE:\n"
                    "- @Slf4j annotation (NO LoggerFactory, NO Logger field, NO org.slf4j imports)\n"
                    "- log.debug(\"Service Method : xxx, Input Param={}\") as FIRST line in every method\n"
                    "- catch block has ONLY throw — NO log.error() or log.warn() before throw\n"
                    "- DAO calls use FULL method names: syar030DaoImpl.selectWinList() NOT syar030DaoImpl.select()\n"
                    "- save() takes List<ResDto> NOT single ReqDto\n"
                    "- CommonUtils.filterByStatus(list, GridStatus.INSERTED/UPDATED/DELETED) for CRUD routing\n"
                    "- NO UUID.randomUUID() — NEVER import java.util.UUID\n"
                    "- NO manual fstCretDtm/lastMdfcDtm/fstCrtrId/lastMdfrId — AuditBaseDto handles it\n"
                    "- NO DateTimeFormatter or LocalDateTime.now().format() in ServiceImpl\n"
                )

            content_parts: list[str] = []
            stream = await codex_client.complete(system, user, stream=True, max_tokens=settings.CODEGEN_MAX_TOKENS)
            async for chunk in stream:
                content_parts.append(chunk)
                if on_chunk:
                    on_chunk(chunk)

            content = _strip_fences("".join(content_parts))
            if file_entry.file_type == "service_impl":
                raw_has_logfactory = 'LoggerFactory' in content
                if raw_has_logfactory:
                    logger.warning(
                        "[BACKEND_ENG] service_impl raw LLM output still has LoggerFactory — file=%s",
                        file_entry.file_path,
                    )
                    for ln in content.splitlines():
                        if 'LoggerFactory' in ln or 'Logger log' in ln or 'Logger LOGGER' in ln:
                            logger.warning("[BACKEND_ENG] raw Logger line: %r", ln)
                # Normalize immediately so streamed/generated snapshots do not expose LoggerFactory style.
                content = _ensure_slf4j_service_impl(content)
                if 'LoggerFactory' in content:
                    logger.error(
                        "[BACKEND_ENG] !! ensure_slf4j DID NOT remove LoggerFactory — file=%s",
                        file_entry.file_path,
                    )

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

    _FRONTEND_TYPES = {
        "vue_page", "vue_search_form", "vue_data_table",
        "vue_data_table_utils", "vue_sum_grid", "vue_api", "vue_scss",
    }

    _FILE_TYPE_PROMPTS: dict[str, str] = {
        "vue_page": (
            "Generate index.vue — the PAGE ORCHESTRATOR.\n"
            "This file MUST ONLY orchestrate child components. DO NOT put SearchForm/DataTable logic here.\n"
            "REQUIREMENTS:\n"
            "- Import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue'\n"
            "- Import child components using @/ absolute path alias (e.g., '@/pages/{module}/{category}/{screenId}/components/{screenId}SearchForm/{ScreenId}SearchForm.vue')\n"
            "- Import SumGrid ONLY if a vue_sum_grid file exists in the generation plan — do NOT import SumGrid if it was not planned\n"
            "- Import API functions from the API module (e.g., '@/api/pages/{module}/{category}/{screenId}')\n"
            "- Import types from '@/api/pages/{module}/{category}/{screenId}Types'\n"
            "- const searchParams = ref({...initial search params...})\n"
            "- provide('searchParams', searchParams)\n"
            "- Data fetching functions (fetchList, fetchSum) called from onMounted and child events\n"
            "- Use try/finally with loading ref for fetch calls\n"
            "- Pass fetched data as props to DataTable children (and SumGrid if it exists in plan)\n"
            "- <style scoped lang=\"scss\" src=\"./{screenId}.scss\"></style>\n"
            "- DO NOT provide('searchFormRef') — this is an obsolete pattern\n"
            "- DO NOT import or use components/composables/stores not listed in the guide — leave // TODO if unsure\n"
        ),
        "vue_search_form": (
            "Generate a SearchForm component (.vue file).\n"
            "The output MUST contain TWO sections separated by the exact line '---SCSS---':\n"
            "SECTION 1: The .vue file content\n"
            "---SCSS---\n"
            "SECTION 2: The paired .scss file content\n\n"
            "VUE FILE REQUIREMENTS:\n"
            "- <script setup lang=\"ts\">\n"
            "- Import { SearchForm, SearchFormContent, SearchFormField, SearchFormRow } from '@/components/common/searchForm'\n"
            "- Import SearchFormLabel from '@/components/common/searchForm/SearchFormLabel.vue'\n"
            "- Import { Button } from '@/components/common/button'\n"
            "- Import InputText from '@/components/common/inputText/InputText.vue'\n"
            "- Import Select from '@/components/common/select/Select.vue'\n"
            "- For date fields: Import { DatePicker } from '@/components/common/datePicker'\n"
            "  DATE FIELD COMPONENT RULE (CRITICAL):\n"
            "  - Date fields (일자, 기간, 날짜): use DatePicker. Single date: <DatePicker v-bind=\"props\" showIcon iconDisplay=\"input\" />. Date range: <DatePicker v-bind=\"props\" selectionMode=\"range\" :numberOfMonths=\"2\" showIcon iconDisplay=\"input\" />.\n"
            "  - DateTime fields (requires explicit time selection in requirements): use <input type=\"datetime-local\" class=\"p-inputtext p-component\">.\n"
            "  - When requirements say '일자', '기간', '날짜' without mentioning '시간' or 'time' → use DatePicker component. NEVER use <input type=\"date\">.\n"
            "- Import types from '@/api/pages/{module}/{category}/{screenId}Types'\n"
            "- const searchFormRef = ref()\n"
            "- const searchParams = inject<Ref<SearchParamsType>>('searchParams')\n"
            "- watch(() => searchParams.value?.field, (newVal) => { if (newVal !== undefined && searchFormRef.value?.form) searchFormRef.value.form.setFieldValue('field', newVal ?? '') })\n"
            "- defineExpose({ searchFormRef })\n"
            "- emit('search') on search button click\n"
            "- For common codes: const commonCodeStore = useCommonCodeStore(); await commonCodeStore.loadMulti([...]) in onMounted; options via computed\n"
            "- Correct ref path: searchFormRef.value.form.setFieldValue (NOT .value.value.form)\n"
            "- <style scoped lang=\"scss\" src=\"./{PascalName}SearchForm.scss\"></style>\n\n"
            "TEMPLATE LAYOUT (CRITICAL — fields must be horizontally arranged, NOT stacked vertically):\n"
            "- MUST wrap SearchFormField elements inside <SearchFormRow> for horizontal layout\n"
            "- Without SearchFormRow, fields stack vertically (broken layout)\n"
            "- Place 2-3 related fields per SearchFormRow for a grid-like horizontal arrangement\n"
            "- Use SearchFormFieldGroup to pair related fields (e.g., date type selector + date picker) within a single row\n"
            "- Template structure:\n"
            "  <SearchForm ref=\"searchFormRef\" @submit=\"handleSubmit\" @reset=\"handleReset\">\n"
            "    <SearchFormRow>\n"
            "      <SearchFormField name=\"field1\"><SearchFormLabel>Label1</SearchFormLabel><SearchFormContent>...</SearchFormContent></SearchFormField>\n"
            "      <SearchFormField name=\"field2\"><SearchFormLabel>Label2</SearchFormLabel><SearchFormContent>...</SearchFormContent></SearchFormField>\n"
            "      <SearchFormField name=\"field3\"><SearchFormLabel>Label3</SearchFormLabel><SearchFormContent>...</SearchFormContent></SearchFormField>\n"
            "    </SearchFormRow>\n"
            "    <SearchFormRow>\n"
            "      <SearchFormField name=\"field4\">...</SearchFormField>\n"
            "      <SearchFormField name=\"field5\">...</SearchFormField>\n"
            "    </SearchFormRow>\n"
            "  </SearchForm>\n\n"
            "SCSS FILE REQUIREMENTS:\n"
            "- Component-specific search form styles\n"
            "- Use CSS variables and :deep() for PrimeVue child components\n"
            "- DO NOT use PrimeVue components not listed in the guide — if unsure about a component, leave // TODO\n"
        ),
        "vue_data_table": (
            "Generate a DataTable component (.vue file).\n"
            "The output MUST contain TWO sections separated by the exact line '---SCSS---':\n"
            "SECTION 1: The .vue file content\n"
            "---SCSS---\n"
            "SECTION 2: The paired .scss file content\n\n"
            "VUE FILE REQUIREMENTS:\n"
            "- <script setup lang=\"ts\">\n"
            "- CRITICAL: Import { DataTable } from '@/components/common/dataTable2'  (named export, NOT default import from DataTable2.vue)\n"
            "- DO NOT import Column from 'primevue/column' — DataTable2 wrapper manages columns internally via :columns prop\n"
            "- DO NOT use <Column> child elements inside <DataTable> — they are IGNORED by DataTable2 wrapper\n"
            "- Import types from '@/api/pages/{module}/{category}/{screenId}Types'\n"
            "- Import { getColumns, getRows } from './utils'\n"
            "- Props: fetchedMainData array, loading state, totalRecords?, rows?, first?\n"
            "- const columns = getColumns()  — returns TableColumn[] from utils\n"
            "- const displayRows = computed(() => getRows(props.fetchedMainData))  — pre-formatted rows\n"
            "- MUST pass :columns=\"columns\" prop — this is how DataTable2 renders column headers\n"
            "- MUST pass title prop — shown in DataTableHeader above the table\n"
            "- MUST pass :totalCount=\"totalRecords\" — shown in DataTableHeader count area\n"
            "- MUST pass :enableRowCheck=\"true\" for checkbox selection (NOT selectionMode='multiple' Column)\n"
            "- MUST pass :utilOptions with appropriate buttons e.g. ['filter', 'settings', 'reset', 'downloadExcel']\n"
            "- MUST pass :scrollHeight=\"'540px'\" and :virtualScrollerOptions=\"{ itemSize: 46 }\" for virtual scroll\n"
            "- For paginated tables: pass paginator, :rows, :first, :totalRecords, lazy, @page directly (passed through via attrs)\n"
            "- Date pre-formatting is handled in utils/index.ts getRows() — NO watch+nextTick needed\n"
            "- <style scoped lang=\"scss\" src=\"./{PascalName}DataTable.scss\"></style>\n\n"
            "TEMPLATE PATTERN (use this exact structure):\n"
            "<DataTable\n"
            "  :value=\"displayRows\"\n"
            "  :columns=\"columns\"\n"
            "  dataKey=\"{primaryKeyField}\"\n"
            "  :loading=\"loading\"\n"
            "  title=\"{Korean screen title}\"\n"
            "  :totalCount=\"totalRecords\"\n"
            "  :enableRowCheck=\"true\"\n"
            "  :utilOptions=\"['filter', 'settings', 'reset', 'downloadExcel']\"\n"
            "  :scrollHeight=\"'540px'\"\n"
            "  :virtualScrollerOptions=\"{ itemSize: 46 }\"\n"
            "/>\n\n"
            "SCSS FILE REQUIREMENTS:\n"
            "- Wrap all DataTable styles inside .datatable-container :deep(.p-datatable) { ... }\n"
            "- GPU acceleration on tr: will-change: background-color\n"
            "- CSS containment on td: contain: layout style\n"
            "- Hover: :hover:not(.p-datatable-row-selected) { background-color: var(--primary-50); }\n"
            "- Use :deep() for all PrimeVue DataTable child elements\n"
            "- DO NOT add DataTable props or events not documented in the guide — leave // TODO if unsure\n"
        ),
        "vue_data_table_utils": (
            "Generate utils/index.ts for DataTable helper functions.\n"
            "REQUIREMENTS:\n"
            "- Import { TableColumn } from '@/components/common/dataTable2/types'  — MUST use this type, do NOT define custom column types\n"
            "- Import ResDto types from '@/api/pages/{module}/{category}/{screenId}Types'\n"
            "- Export DisplayRow type: ResDto & { fieldFormatted?: string } for pre-formatted date/number fields\n"
            "- Export getColumns(): TableColumn[]  — MUST use TableColumn type\n"
            "- Export getRows(data): DisplayRow[]  — pre-format dates and numbers here\n\n"
            "TableColumn SHAPE (all fields):\n"
            "  objectId: string    ← REQUIRED, use same value as field (e.g. 'userId')\n"
            "  field: string       ← data field name\n"
            "  header: string      ← column header label\n"
            "  width?: string      ← '140px' format (NOT minWidth!)\n"
            "  columnClass?: string ← header alignment: 'left' | 'center' | 'right'\n"
            "  rowClass?: string   ← body cell alignment: 'left' | 'center' | 'right'\n"
            "  visible?: boolean   ← REQUIRED true — column is HIDDEN if visible is not true\n"
            "  frozen?: boolean    ← left-pinned column\n"
            "  required?: boolean  ← marks column as required\n\n"
            "EXAMPLE getColumns():\n"
            "export const getColumns = (): TableColumn[] => [\n"
            "  { objectId: 'userId', field: 'userId', header: '사용자ID', width: '140px', frozen: true, columnClass: 'left', rowClass: 'left', visible: true },\n"
            "  { objectId: 'userName', field: 'userName', header: '사용자명', width: '140px', columnClass: 'left', rowClass: 'left', visible: true },\n"
            "  { objectId: 'eduDateFormatted', field: 'eduDateFormatted', header: '교육일자', width: '130px', columnClass: 'center', rowClass: 'center', visible: true },\n"
            "];\n\n"
            "EXAMPLE getRows() with date formatting:\n"
            "const formatDate = (v?: string | null): string => { if (!v) return ''; const p = v.replaceAll('-','').slice(0,8); return p.length===8 ? `${p.slice(0,4)}-${p.slice(4,6)}-${p.slice(6,8)}` : v; };\n"
            "export const getRows = (data?: XxxResDto[] | null): XxxDisplayRow[] => (data ?? []).map(row => ({ ...row, eduDateFormatted: formatDate(row.eduDate) }));\n\n"
            "- DO NOT add columns for fields not defined in the ResDto type or spec — leave // TODO if unsure about a field\n"
            "Output ONLY TypeScript code. No markdown fences.\n"
        ),
        "vue_sum_grid": (
            "Generate a SumGrid component (.vue file).\n"
            "The output MUST contain TWO sections separated by the exact line '---SCSS---':\n"
            "SECTION 1: The .vue file content\n"
            "---SCSS---\n"
            "SECTION 2: The paired .scss file content\n\n"
            "VUE FILE REQUIREMENTS:\n"
            "- <script setup lang=\"ts\">\n"
            "- const searchParams = inject<Ref<SearchParamsType>>('searchParams')\n"
            "- Props: summary data from parent\n"
            "- Click handlers ONLY mutate searchParams.value.field — do NOT call searchFormRef\n"
            "- 'All' filter: set field to null (NOT empty string '')\n"
            "- <style scoped lang=\"scss\" src=\"./{PascalName}SumGrid.scss\"></style>\n\n"
            "SCSS FILE REQUIREMENTS:\n"
            "- SumGrid layout styles aligned to design tokens\n"
            "- Use CSS variables for spacing and colors\n"
        ),
        "vue_api": (
            "Generate the API module (.ts file).\n"
            "REQUIREMENTS:\n"
            "- import api from '@/plugins/axios'\n"
            "- import { formatErrorMessage } from '@/utils/formatErrorMessage'\n"
            "- import type { ... } from './{screenId}Types'\n"
            "- API URL pattern: /api/v1/{SCREEN_CODE}-{method}\n"
            "- Export async functions for each API call (selectList, save, etc.)\n"
            "- CRITICAL: ALL API calls MUST use api.post() — NEVER use api.get(), api.put(), or api.delete()\n"
            "  The CPMS /api/v1/ dispatcher only accepts POST requests. Even search/select operations use POST.\n"
            "  WRONG: api.get(Api.selectList, { params })  ← this will fail with 404/405\n"
            "  CORRECT: api.post(Api.selectList, params)  ← always POST, params in request body\n"
            "- Pass camelCase params directly matching backend DTO field names (NO uppercase conversion)\n"
            "- For save endpoints: send array of ResDto objects with status field ('I'|'U'|'D') for GridStatus — NO wrapping in dsSearch/dsSave\n"
            "- Session params (sLangCd, userId) are handled server-side via UserContextUtil — do NOT add from frontend\n"
            "- Audit fields (fstCretDtm, lastMdfcDtm, fstCrtrId, lastMdfrId) are set by AuditBaseDto — do NOT send from frontend\n"
            "- Check responseCode === 'S0000' for success\n"
            "- Return response.data (full ApiResponse including header + payload)\n"
            "- Component accesses actual data via result.payload\n"
            "- DO NOT invent API endpoints or response structures not derivable from the spec and backend DTO definitions — leave // TODO if unsure\n"
            "- Output ONLY TypeScript code. No markdown fences.\n"
        ),
        "vue_scss": (
            "Generate the page-level SCSS file.\n"
            "REQUIREMENTS:\n"
            "- Page layout styles for the screen\n"
            "- Use CSS custom properties (--bg-*, --primary-*, spacing tokens)\n"
            "- :deep() for scoped child PrimeVue components\n"
            "- Responsive breakpoints/mixins if needed\n"
            "- Output ONLY SCSS code. No markdown fences.\n"
        ),
    }

    def _get_my_files(self, plan: CodeGenPlan) -> list[CodeGenPlanFile]:
        return [f for f in plan.files if f.file_type in self._FRONTEND_TYPES]

    async def execute(self, ctx: SharedContext, on_chunk: callable | None = None) -> list[GeneratedFile]:
        assert ctx.plan is not None
        my_files = self._get_my_files(ctx.plan)
        naming = get_naming_context()

        base_system = (
            "You are a senior Frontend Engineer specializing in CPMS Vue3 + PrimeVue projects.\n"
            "You generate MULTI-FILE frontend components following strict separation of concerns.\n"
            "Each screen is composed of: index.vue (orchestrator), SearchForm, DataTable (components), API module, SCSS files.\n"
            "SumGrid is OPTIONAL — include only if a vue_sum_grid file exists in the generation plan.\n\n"
            f"--- NAMING CONVENTIONS ---\n{naming}\n--- END ---\n\n"
            "STRICT RULES:\n"
            "- Output ONLY the file content. No markdown fences.\n"
            "- MUST use <script setup lang=\"ts\"> syntax for all .vue files.\n"
            "- screenId MUST be camelCase (e.g., cpmsEduPondgEdit NOT cpmsedupondgedit)\n"
            "- Vue/SCSS component files MUST be PascalCase (e.g., CpmsEduPondgEditSearchForm.vue)\n\n"
            "CRITICAL IMPORT PATHS:\n"
            "- ContentHeader: import ContentHeader from '@/components/common/contentHeader/ContentHeader.vue'\n"
            "- SearchForm: import { SearchForm, SearchFormField, SearchFormLabel, SearchFormContent } from '@/components/common/searchForm'\n"
            "- DataTable: import { DataTable } from '@/components/common/dataTable2'  ← named export, NOT default import\n"
            "- DataTable column type: import type { TableColumn } from '@/components/common/dataTable2/types'\n"
            "- Button: import { Button } from '@/components/common/button'\n"
            "- InputText: import InputText from '@/components/common/inputText/InputText.vue'\n"
            "- Select: import Select from '@/components/common/select/Select.vue'\n"
            "- axios: import api from '@/plugins/axios'\n"
            "- formatErrorMessage: import { formatErrorMessage } from '@/utils/formatErrorMessage'\n"
            "- CommonCodeStore: import { useCommonCodeStore } from '@/stores/commonCodeStore'\n"
            "- Toast: const toast = useToast() — NO alert()/confirm()/prompt()\n\n"
            "KNOWN ERROR PREVENTION (DO NOT):\n"
            "- DO NOT use <Column> children inside <DataTable> — DataTable2 wrapper ignores all slot children. Use :columns prop instead.\n"
            "- DO NOT import Column from 'primevue/column' in DataTable files — DataTable2 manages columns internally.\n"
            "- DO NOT pass selectionMode to DataTable — use :enableRowCheck=\"true\" for checkbox column.\n"
            "- DO NOT define custom column types — MUST use TableColumn from '@/components/common/dataTable2/types'.\n"
            "- DO NOT omit objectId in TableColumn — it is REQUIRED for DataTable2 to function correctly (use same value as field).\n"
            "- DO NOT omit visible: true in TableColumn — columns without visible: true are HIDDEN.\n"
            "- DO NOT use minWidth in TableColumn — use width: '140px' format instead.\n"
            "- DO NOT use scrollHeight=\"flex\" — MUST use :scrollHeight=\"'540px'\" with :virtualScrollerOptions=\"{ itemSize: 46 }\".\n"
            "- DO NOT format dates in template slots — pre-format in utils/index.ts getRows(), store as _Formatted fields.\n"
            "- DO NOT use watch+nextTick for date formatting — handle in getRows() instead.\n"
            "- DO NOT use if(newVal) in watch — use if(newVal !== undefined) to handle null/empty/0.\n"
            "- DO NOT access ref as .value.value.form — correct path is .value.form.\n"
            "- DO NOT use alert()/confirm()/prompt() — use Toast and ConfirmDialog.\n"
            "- DO NOT define UPPER_SNAKE_CASE TypeScript fields — match backend camelCase DTO field names exactly.\n"
            "- DO NOT forget await on commonCodeStore.loadMulti() in onMounted.\n"
            "- DO NOT define SelectBox options without computed() wrapper.\n"
            "- DO NOT omit GPU acceleration CSS — add will-change: background-color on tr, contain: layout style on td.\n"
            "- DO NOT apply hover styles to selected rows — use :hover:not(.p-datatable-row-selected).\n"
            "- DO NOT use <script> without setup — MUST be <script setup lang=\"ts\">.\n\n"
            "╔══════════════════════════════════════════════════════════════╗\n"
            "║  DO NOT GUESS OR FABRICATE — ABSOLUTE TOP-PRIORITY RULE     ║\n"
            "╚══════════════════════════════════════════════════════════════╝\n"
            "If you are NOT 100% certain about ANY of the following, DO NOT generate it — leave a // TODO comment instead:\n"
            "- Component names or import paths not listed in CRITICAL IMPORT PATHS above or the provided guide\n"
            "- Prop names, event names, or slot names you have not seen in the provided context\n"
            "- API endpoint URLs, HTTP methods, request/response structures not in the guide\n"
            "- PrimeVue component usage patterns not demonstrated in the guide\n"
            "- Vue composable names (useXxx) not listed in the guide\n"
            "- Store names or store method names not in the provided context\n"
            "- CSS class names or design tokens not shown in the guide\n\n"
            "INCOMPLETE but CORRECT code >>> COMPLETE but WRONG code.\n"
            "A file with 3 TODO comments is far better than a file with 3 fabricated imports that break at runtime.\n\n"
            "EXAMPLES:\n"
            "  WRONG:  import SomeGuessedDialog from '@/components/common/dialog/SomeGuessedDialog.vue'  // fabricated path\n"
            "  WRONG:  const { openModal } = useModalStore()  // fabricated composable\n"
            "  WRONG:  <ConfirmPopup :group=\"deleteGroup\" />  // fabricated prop\n"
            "  CORRECT: // TODO: verify import path for dialog component\n"
            "  CORRECT: // TODO: verify store method for modal\n"
        )

        results: list[GeneratedFile] = []
        for file_entry in my_files:
            file_type = file_entry.file_type
            guide_context = get_context_for_file_type(file_type)
            type_prompt = self._FILE_TYPE_PROMPTS.get(file_type, "")

            system = base_system
            if guide_context:
                system += f"\n--- FRONTEND CODING GUIDE (for {file_type}) ---\n{guide_context}\n--- END ---\n\n"
            if type_prompt:
                system += f"FILE-TYPE SPECIFIC INSTRUCTIONS ({file_type}):\n{type_prompt}\n"

            dep_parts = []
            if ctx.data_contracts:
                dep_parts.append(f"--- types.ts ---\n{ctx.data_contracts}")
            for gf in results[-5:]:
                dep_parts.append(f"--- {gf.file_path} ---\n{gf.content}")
            deps_text = "\n\n".join(dep_parts) if dep_parts else ""

            user = f"Specification:\n{ctx.spec_markdown}\n\n"
            if deps_text:
                user += f"Dependencies (already generated files):\n{deps_text}\n\n"
            user += f"Generate: {file_entry.file_path}\nType: {file_entry.file_type}\nDescription: {file_entry.description}\n"

            content_parts: list[str] = []
            stream = await codex_client.complete(system, user, stream=True, max_tokens=settings.CODEGEN_MAX_TOKENS)
            async for chunk in stream:
                content_parts.append(chunk)
                if on_chunk:
                    on_chunk(chunk)

            raw_content = _strip_fences("".join(content_parts))

            if file_type in ("vue_search_form", "vue_data_table", "vue_sum_grid") and "---SCSS---" in raw_content:
                vue_part, scss_part = raw_content.split("---SCSS---", 1)
                vue_part = _strip_fences(vue_part.strip())
                scss_part = _strip_fences(scss_part.strip())

                gf_vue = GeneratedFile(
                    file_path=file_entry.file_path,
                    file_type=file_entry.file_type,
                    content=vue_part,
                    layer="frontend",
                )
                results.append(gf_vue)
                ctx.generated_files[gf_vue.file_path] = gf_vue

                scss_path = file_entry.file_path.replace(".vue", ".scss")
                gf_scss = GeneratedFile(
                    file_path=scss_path,
                    file_type=file_entry.file_type + "_scss",
                    content=scss_part,
                    layer="frontend",
                )
                results.append(gf_scss)
                ctx.generated_files[gf_scss.file_path] = gf_scss
            else:
                gf = GeneratedFile(
                    file_path=file_entry.file_path,
                    file_type=file_entry.file_type,
                    content=raw_content,
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
            "- DTO class names MUST include full screen name prefix (e.g., CpmsEduRegLstReqDto, NOT EduRegLstReqDto). The class name MUST exactly match the file name.\n"
            "- @ServiceId format: @ServiceId(\"ScreenCode/methodName\")\n"
            "- @ServiceName with Korean description on every public service method\n"
            "- @Transactional on CUD methods, NOT on read-only methods\n"
            "- DAO impl: @Repository, extends AbstractSqlSessionDaoSupport ONLY — MUST NOT implement any interface (no 'implements XxxDao')\n"
            "- DaoImpl/ServiceImpl: NO interface files, NO implements clause\n"
            "- ONLY import from pom.xml libraries — any import from a library NOT in pom.xml is an issue\n"
            "- ServiceId/ServiceName MUST be imported from aondev.framework.annotation (NOT hone.bom.annotation)\n"
            "- AbstractSqlSessionDaoSupport MUST be imported from aondev.framework.dao.mybatis.support (NOT hone.bom.dao)\n"
            "- PACKAGE STRUCTURE (NO screen-level package — CRITICAL):\n"
            "    dao_impl     → package biz.{module}.dao;          (e.g., biz.edu.dao)\n"
            "    dto_request  → package biz.{module}.dto.request;  (e.g., biz.edu.dto.request)\n"
            "    dto_response → package biz.{module}.dto.response; (e.g., biz.edu.dto.response)\n"
            "    service_impl → package biz.{module}.service;      (e.g., biz.edu.service)\n"
            "  WRONG examples (DO NOT FLAG THESE AS ERRORS): biz.edu.dao is CORRECT, NOT biz.edu.cpmseduproglst.dao\n"
            "- Mapper XML: namespace = full DAO impl path WITHOUT screen-level: biz.{module}.dao.{ClassName}DaoImpl\n"
            "    e.g., namespace=\"biz.edu.dao.CpmsEduPgmRsltLstDaoImpl\"  (NOT biz.edu.cpmseduproglst.dao.XxxDaoImpl)\n"
            "- Mapper XML: <if test> for optional params, CDATA for < > operators\n"
            "- ServiceImpl must NOT call DTO getter/setter methods that don't exist in the DTO\n"
            "    CHECK EVERY .getXxx() and .setXxx() call — the corresponding field MUST exist in the DTO class\n"
            "    e.g., if DTO has no 'page' field, calling dto.setPage() or dto.getPage() is a BUG\n"
            "- ServiceImpl MUST only call DaoImpl methods that actually exist in the DaoImpl — cross-check method names\n"
            "- DAO layer handles ONLY MyBatis DB operations — DAO MUST NOT contain file I/O, MultipartFile, HTTP logic\n"
            "- NEVER use 'Object' as variable type for method return — use the actual return type (List<...>, int, etc.)\n"
            "- NEVER create recursive/self-referencing method calls\n"
            "- Return types and parameter types MUST be consistent between caller and callee\n"
            "- DAO methods must match Mapper XML statement IDs\n"
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
            "MULTI-FILE STRUCTURE COMPLIANCE (CRITICAL):\n"
            "- index.vue MUST only be an orchestrator: imports + provide/inject + data fetching. NO inline SearchForm/DataTable UI.\n"
            "- SearchForm, DataTable MUST be separate component files under components/ subdirectory\n"
            "- SumGrid MUST be a separate component ONLY if vue_sum_grid exists in the plan — do NOT flag missing SumGrid if it was not planned\n"
            "- Each component .vue MUST have a paired .scss file\n"
            "- provide/inject connections between parent (index.vue) and children must be consistent\n"
            "- index.vue provides searchParams via provide('searchParams', searchParams)\n"
            "- Children inject searchParams via inject<Ref<...>>('searchParams')\n"
            "- Import paths between components must use correct relative paths\n"
            "- types MUST be in src/api/pages/{module}/{category}/{screenId}Types.ts (NOT under page folder, NOT shared types.ts)\n"
            "- API file MUST be in src/api/pages/{module}/{category}/{screenId}.ts\n\n"
            "NAMING COMPLIANCE (CRITICAL):\n"
            "- screenId MUST be camelCase (NOT all lowercase) — e.g., cpmsEduPondgEdit NOT cpmsedupondgedit\n"
            "- Component folder names MUST be camelCase — e.g., cpmsEduPondgEditSearchForm/\n"
            "- Vue/SCSS component files MUST be PascalCase — e.g., CpmsEduPondgEditSearchForm.vue/.scss\n"
            "- API files MUST be camelCase — e.g., cpmsEduPondgEdit.ts\n\n"
            "CODING GUIDE COMPLIANCE:\n"
            "- MUST use <script setup lang=\"ts\"> syntax (Options API is forbidden)\n"
            "- DataTable MUST have scrollHeight=\"540px\" + virtualScrollerOptions (performance critical)\n"
            "- Date formatting MUST be pre-processed in utils/index.ts getRows() — NOT in template slots (causes 5000+ calls per render)\n"
            "- Import paths must be exact: ContentHeader from '@/components/common/contentHeader/ContentHeader.vue', etc.\n"
            "- API parameters must use camelCase matching backend DTO field names — NO uppercase conversion\n"
            "- Save endpoints: send array with status field ('I'|'U'|'D') directly — no dsSearch/dsSave wrapping\n"
            "- API functions must return response.data (full ApiResponse) — components access .payload\n"
            "- searchParams: must use provide/inject pattern correctly\n"
            "- Ref access: must be .value.form (NOT .value.value.form or .form.value)\n"
            "- Watch conditions: use !== undefined (NOT if(value) which fails for null/empty)\n"
            "- GPU acceleration CSS: will-change and contain properties for DataTable rows\n"
            "- TypeScript types must match backend DTO fields\n"
            "- SumGrid (if present): 'All' filter must set field to null, NOT empty string\n"
            "- DO NOT provide('searchFormRef') — obsolete pattern\n"
            "- DO NOT use alert()/confirm()/prompt() — use Toast and ConfirmDialog\n"
            "- SearchForm MUST defineExpose({ searchFormRef })\n\n"
            "FABRICATION DETECTION (CRITICAL — report as HIGH severity):\n"
            "- Flag any import path that does NOT match the CRITICAL IMPORT PATHS listed in the frontend guide\n"
            "- Flag any PrimeVue component usage not documented in the guide\n"
            "- Flag any composable (useXxx) not listed in the guide\n"
            "- Flag any API endpoint pattern that does not follow /api/v1/{SCREEN_CODE}-{method}\n"
            "- Flag any store method call not documented in the provided context\n"
            "- Flag api.get() calls — CPMS only uses api.post()\n"
            "- For each flagged item, fix_instruction MUST say: remove the fabricated code and replace with // TODO comment\n\n"
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
                if other.file_path == gf.file_path:
                    continue
                if other.file_path.startswith(file_dir):
                    dep_parts.append(f"--- {other.file_path} ---\n{other.content}")
            # ServiceImpl fix: always include DaoImpl, mapper XML, and DTOs
            if gf.file_type == "service_impl":
                for path, other in ctx.generated_files.items():
                    if other.file_type in ("dao_impl", "mapper_xml"):
                        dep_parts.append(f"--- {other.file_path} (USE THESE DAO METHODS) ---\n{other.content}")
                    elif other.file_type in ("dto_request", "dto_response"):
                        dep_parts.append(f"--- {other.file_path} (THESE ARE THE DTO FIELDS) ---\n{other.content}")
            # DaoImpl fix: always include mapper XML (to know SQL IDs) and ServiceImpl (to know what methods are needed)
            if gf.file_type == "dao_impl":
                for path, other in ctx.generated_files.items():
                    if other.file_type == "mapper_xml":
                        dep_parts.append(f"--- {other.file_path} (MAPPER XML — add SQL statement if adding new DAO method) ---\n{other.content}")
                    elif other.file_type == "service_impl":
                        dep_parts.append(f"--- {other.file_path} (ServiceImpl — shows how the missing method is called) ---\n{other.content}")
            # DTO fix: include ServiceImpl so Fix Agent can see what fields are needed
            if gf.file_type in ("dto_request", "dto_response"):
                for path, other in ctx.generated_files.items():
                    if other.file_type == "service_impl":
                        dep_parts.append(f"--- {other.file_path} (CHECK WHICH FIELDS ARE USED) ---\n{other.content}")
            deps_text = "\n\n".join(dep_parts[:10])

            system = (
                "You are an expert developer applying QA fixes to source code.\n"
                "Output ONLY the complete fixed file content. No markdown fences, no explanations.\n"
                "Apply ALL the fixes listed below while preserving the overall structure and logic.\n\n"
                "ABSOLUTE RULES (violating ANY of these = broken code):\n"
                "IMPORT RULES:\n"
                "- Use aondev.framework.annotation.ServiceId/ServiceName (NOT hone.bom.annotation.*).\n"
                "- Use aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport (NOT hone.bom.dao.*).\n"
                "- NEVER import org.slf4j.Logger or org.slf4j.LoggerFactory.\n"
                "- CommonUtils and GridStatus MUST be imported from com.common.sy (NOT com.common.dto.base):\n"
                "  CORRECT: import com.common.sy.CommonUtils;  import com.common.sy.GridStatus;\n\n"
                "LOGGING RULES:\n"
                "- ALWAYS use @Slf4j (Lombok) class annotation — NEVER declare Logger field with LoggerFactory.getLogger().\n"
                "  WRONG:   private static final Logger log = LoggerFactory.getLogger(XxxServiceImpl.class);\n"
                "  CORRECT: @Slf4j on the class, which auto-provides the 'log' field.\n"
                "- NEVER call log.error()/log.warn() immediately before throw HscException — the framework already logs.\n"
                "  WRONG:   log.error(\"...\", e); throw HscException.systemError(\"...\", e);\n"
                "  CORRECT: throw HscException.systemError(\"...\", e);\n\n"
                "DTO FIELD CONSISTENCY RULES:\n"
                "- NEVER call getter/setter for a field that is not declared in the DTO class.\n"
                "- If a fix says to add a field to a DTO: add 'private <Type> fieldName;' inside the DTO class body.\n"
                "- When fixing a DTO issue, output the UPDATED DTO file (not the ServiceImpl) with the new field added.\n"
                "- NEVER just remove the getter/setter call — always ADD the missing field to the DTO instead.\n\n"
                "DAO METHOD CALL RULES:\n"
                "- ServiceImpl MUST call the full wrapper method names defined in DaoImpl.\n"
                "- NEVER call bare insert()/select()/update()/delete()/selectOne()/selectList() on a DAO variable.\n"
                "  These are AbstractSqlSessionDaoSupport internal methods NOT accessible from ServiceImpl.\n"
                "  Look at the provided DaoImpl file to find the correct wrapper method names\n"
                "  (e.g., insertCpmsEduXxx, selectCpmsEduXxxLst, etc.) and use those.\n"
                "- DaoImpl method names MUST NOT be bare CRUD verbs — always append a domain noun.\n"
                "  WRONG: public int insert(...)  CORRECT: public int insertEduPgm(...)\n\n"
                "DAO METHOD MISSING — ADD TO DAOIMPL:\n"
                "- If the issue says a method does NOT exist in DaoImpl, DO NOT remove the call in ServiceImpl.\n"
                "  Instead, ADD the missing method to the DaoImpl file.\n"
                "- The file to fix will be the DaoImpl file (not ServiceImpl). Read the ServiceImpl context\n"
                "  to understand the expected return type and parameter type, then add the method.\n"
                "- Method pattern: 'public <ReturnType> <methodName>(<ParamType> param) { return super.<op>(\"<methodName>\", param); }'\n"
                "  where <op> = selectList (List queries), selectOne (single/int), insert, update, delete,\n"
                "  batchUpdateReturnSumAffectedRows (List CUD).\n"
                "- Also add the corresponding SQL statement to the Mapper XML if the issue mentions it.\n"
                "- TYPE CONTRACT: param type and return type MUST match how ServiceImpl uses the method.\n\n"
                "SERVICE ↔ DAO TYPE CONSISTENCY:\n"
                "- When fixing a DaoImpl method, match the return type to how ServiceImpl assigns the result.\n"
                "  e.g., if ServiceImpl has 'List<FooResDto> list = fooDao.selectFooList(req)'\n"
                "  then DaoImpl method MUST be: 'public List<FooResDto> selectFooList(FooReqDto req)'\n"
                "- When fixing a ServiceImpl call, verify the variable holding the result has the same type\n"
                "  as the DaoImpl method's declared return type.\n\n"
                "SERVICEID RULES:\n"
                "- EVERY public method in ServiceImpl MUST have @ServiceId + @ServiceName.\n"
                "- Public methods without @ServiceId are alias/wrapper methods and MUST be deleted.\n\n"
                "DO NOT GUESS OR FABRICATE — CRITICAL:\n"
                "- Only fix what is explicitly reported in the issues list. Do NOT 'improve' unrelated code.\n"
                "- If you are unsure how to fix an issue (e.g., missing class, unknown method), leave a TODO comment.\n"
                "- NEVER invent a class, method, import, or annotation that is not in the provided context.\n"
                "- It is ALWAYS better to leave a TODO than to fabricate a fix that introduces new errors.\n"
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
            "Fix ALL errors. If a method/field is missing in a DTO, ADD it.\n\n"
            "DO NOT GUESS OR FABRICATE — CRITICAL:\n"
            "- Only fix what the error log says. Do NOT 'improve' or restructure unrelated code.\n"
            "- If you are unsure about the correct fix, leave a TODO comment rather than inventing a solution.\n"
            "- NEVER invent a class, method, import, or annotation that is not visible in the provided context.\n"
            "- It is ALWAYS better to leave a TODO than to fabricate a fix that introduces new errors.\n\n"
            "ABSOLUTE RULES (violating ANY of these = broken code):\n"
            "- Use aondev.framework.annotation.ServiceId/ServiceName (NOT hone.bom.annotation.*).\n"
            "- Use aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport (NOT hone.bom.dao.*).\n"
            "- NEVER import org.slf4j.Logger or org.slf4j.LoggerFactory.\n"
            "- ALWAYS use @Slf4j (Lombok) class annotation — NEVER LoggerFactory.getLogger().\n"
            "- NEVER call log.error()/log.warn() before throw HscException — framework already logs.\n"
            "- ServiceImpl: NEVER call bare DAO base-class methods (insert/select/update/delete/selectOne/selectList).\n"
            "  Use the full wrapper method names defined in DaoImpl (e.g., insertEduPgm, selectEduPgmList).\n"
            "- DaoImpl method names MUST NOT be bare CRUD verbs — always append a domain noun.\n"
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
