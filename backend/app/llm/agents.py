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
    get_pom_group_ids,
    get_table_info,
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
    # HscException.systemError called with only a string literal (no Exception e as 2nd arg)
    (re.compile(r'HscException\.systemError\(\s*"[^"]*"\s*\)'),
     "HscException.systemError() called with only a String argument — WRONG. "
     "throw HscException.systemError() MUST ALWAYS be inside a try-catch block "
     "and MUST pass the caught exception as the second argument. "
     "WRONG: throw HscException.systemError(\"msg\"); "
     "CORRECT: try { ... } catch (Exception e) { throw HscException.systemError(\"msg\", e); }"),
    # UUID usage
    (re.compile(r'UUID\s*\.\s*randomUUID\s*\('),
     "UUID.randomUUID() found — NEVER use java.util.UUID. "
     "ID values come from DB sequence or are already in the DTO. Remove the UUID usage entirely."),
    # CommonUtils.getUuid() usage
    (re.compile(r'CommonUtils\s*\.\s*getUuid\s*\('),
     "CommonUtils.getUuid() found — NEVER use CommonUtils.getUuid(). "
     "ID values come from DB sequence or are already in the DTO. Remove the getUuid() usage entirely."),
    # CommonUtils invented methods — specific known non-existent methods
    (re.compile(r'CommonUtils\s*\.\s*(?:convertArrayToList|convertList|toList|parseList|mapList|toArray|listToArray)\s*\('),
     "CommonUtils.xxx() called with a method that does NOT exist in the framework. "
     "ONLY call CommonUtils methods that are actually defined in com.common.sy.CommonUtils. "
     "The documented method is filterByStatus(List, GridStatus...). "
     "For array/list conversion use standard Java: Arrays.asList(), List.of(), stream().collect(Collectors.toList()). "
     "NEVER invent new CommonUtils methods — they will cause compilation errors."),
    # Date / LocalDate / LocalDateTime as DTO field type — must always be String
    (re.compile(r'private\s+(?:java\.util\.Date|Date|LocalDate|LocalDateTime)\s+\w+\s*;'),
     "DTO field declared with type Date/LocalDate/LocalDateTime — WRONG. "
     "ALL date/datetime fields in ReqDto and ResDto MUST be String (e.g. 'private String educationDate;'). "
     "Never use java.util.Date, LocalDate, or LocalDateTime for DTO fields. "
     "Consequence: param.setEducationDate(request.getEducationDate()) must pass String→String, "
     "and validateDate(request.getEducationDate(), '교육일자') also accepts String, String."),
    # List<...> as DTO field type — causes Service type mismatch when used as String
    (re.compile(r'private\s+List\s*<[^>]+>\s+\w+\s*;'),
     "DTO field declared with type List<...> — WRONG. "
     "DTO fields MUST ONLY use simple scalar types: String, int, long, Integer, Long, BigDecimal, Boolean, boolean. "
     "NEVER declare List, Map, Date, LocalDate, LocalDateTime, or any complex type as a DTO field. "
     "If you need to pass multiple values (e.g. a list of IDs), use a comma-separated String field instead. "
     "Service/DAO handle collections (List<ResDto>) at the method parameter/return level — not inside the DTO."),
    # Map<...> as DTO field type — same issue
    (re.compile(r'private\s+Map\s*<[^>]+>\s+\w+\s*;'),
     "DTO field declared with type Map<...> — WRONG. "
     "DTO fields MUST ONLY use simple scalar types: String, int, long, Integer, Long, BigDecimal, Boolean, boolean. "
     "NEVER declare Map or any complex collection type as a DTO field."),
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
    # @PreAuthorize / @Secured in ServiceImpl — authorization belongs in controller layer
    (re.compile(r'@(?:PreAuthorize|Secured)\s*\('),
     "@PreAuthorize/@Secured annotation found in ServiceImpl — authorization annotations belong in the controller layer. "
     "Remove @PreAuthorize/@Secured from ServiceImpl and its import."),
    (re.compile(r'import\s+org\.springframework\.security\.'),
     "import org.springframework.security.* in ServiceImpl — Spring Security annotations are not used at Service layer. "
     "Remove this import."),
    # @Transactional in ServiceImpl — only @ServiceId + @ServiceName are allowed above public methods
    (re.compile(r'@Transactional(?:\s*\([^)]*\))?\s*\n'),
     "@Transactional annotation found in ServiceImpl — ONLY @ServiceId + @ServiceName are allowed above public methods. "
     "Remove @Transactional and its import."),
    (re.compile(r'import\s+org\.springframework\.transaction\.annotation\.Transactional\s*;'),
     "import Transactional in ServiceImpl — @Transactional is not used at Service layer. "
     "Remove this import."),
    # ResDto used as pagination container — Spring Page fields must never appear on a domain ResDto
    (re.compile(r'\.set(?:TotalElements|TotalPages|PageNumber|NumberOfElements|Last|First)\s*\('),
     "Pagination field setter found (setTotalElements/setTotalPages/setPageNumber/setNumberOfElements/setLast/setFirst) — "
     "NEVER use ResDto as a pagination container. "
     "Service methods MUST return List<ResDto> directly. "
     "Remove ALL pagination wrapping logic and change the method return type to List<ResDto>."),
    # ResDto used as batch-upload result container
    (re.compile(r'\.set(?:RowResults|ProcessedCount|DuplicateCount)\s*\('),
     "Batch-result container field setter found (setRowResults/setProcessedCount/setDuplicateCount) — "
     "NEVER use a domain ResDto as a result container. "
     "Create a dedicated result DTO (e.g. XxxUploadResultDto) for batch operation results, "
     "or return a plain Map / int count from the service method."),
    # Object parameter type in DaoImpl — forbidden, always use concrete DTO type
    (re.compile(r'public\s+\S+\s+\w+\s*\(\s*Object\s+\w+\s*\)'),
     "DaoImpl method has 'Object' as parameter type — NEVER use Object. "
     "Replace with the ACTUAL generated DTO class name (e.g. CpmsEduRegLstReqDto or CpmsEduRegLstResDto). "
     "For next-ID / sequence methods with no meaningful param, use empty params: public int selectXxxNextId() { ... null }"),
    # Explicit well-known wrong type names (saveDto, reqDto, resDto, dto, etc.)
    (re.compile(
        r'public\s+\S+\s+\w+\s*\(\s*'
        r'(?:saveDto|reqDto|resDto|dto|Dto|item|row|entity|record|data|obj|request|response|model|form|vo|bean|param)\s+\w+\s*\)',
        re.IGNORECASE,
     ),
     "DaoImpl method has a FORBIDDEN parameter type name (saveDto/reqDto/dto/item/row/entity/etc.) — "
     "these are NOT Java class names and cause compilation errors. "
     "Replace with the ACTUAL generated DTO class name. "
     "For select queries: use CpmsXxxReqDto. For CUD (insert/update/delete): use CpmsXxxResDto or List<CpmsXxxResDto>. "
     "WRONG: selectDuplicateCount(saveDto param). "
     "CORRECT: selectDuplicateCount(CpmsEduRegLstResDto param)."),
    # Lowercase or non-DTO single-word type name in DaoImpl method parameter (catch-all)
    # Allowed single-token types: concrete *ReqDto/*ResDto classes (CamelCase ending in Dto),
    #   String, int, long, Integer, Long, boolean, Boolean, double, Double
    (re.compile(
        r'public\s+\S+\s+\w+\s*\(\s*'
        r'(?!(?:String|int|long|Integer|Long|boolean|Boolean|double|Double|List)\b)'
        r'([a-z][a-zA-Z0-9]*|[A-Z][a-zA-Z0-9]*(?<!Dto)(?<!ReqDto)(?<!ResDto))\s+\w+\s*\)',
     ),
     "DaoImpl method has an invalid parameter type — only ACTUAL generated DTO classes (ending in ReqDto/ResDto), "
     "List<XxxResDto>, String/int/long/Integer/Long/boolean, or empty () are allowed. "
     "Replace with the ACTUAL generated DTO class name — check what DTO classes exist in the Dependencies section. "
     "WRONG: selectDuplicateCount(item param) / (row param) / (dto param) / (saveDto param). "
     "CORRECT: selectDuplicateCount(CpmsXxxResDto param)."),
    # delete-named DaoImpl method using super.update() — must use super.delete()
    (re.compile(r'public\s+\S+\s+delete\w+\s*\([^)]*\)\s*\{[^}]*super\s*\.\s*update\s*\(', re.DOTALL),
     "DaoImpl delete method uses super.update() — WRONG. "
     "delete-named methods MUST use super.delete() or super.batchUpdateReturnSumAffectedRows() for lists. "
     "CORRECT: return super.delete(\"deleteXxx\", param); or super.batchUpdateReturnSumAffectedRows(\"deleteXxx\", list)"),
    # update-named DaoImpl method using super.delete() — must use super.update()
    (re.compile(r'public\s+\S+\s+update\w+\s*\([^)]*\)\s*\{[^}]*super\s*\.\s*delete\s*\(', re.DOTALL),
     "DaoImpl update method uses super.delete() — WRONG. "
     "update-named methods MUST use super.update() or super.batchUpdateReturnSumAffectedRows() for lists."),
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
    """Dynamically detect imports from libraries NOT in pom.xml.

    Allowed prefixes are derived from pom.xml groupIds (plus java/javax/biz/hsc/aondev).
    Extra rules block imports that share a broad prefix with an unrelated dependency
    (e.g. org.apache.poi when only org.apache.maven.* is declared).
    """
    if gf.layer != "backend" or not gf.file_path.endswith(".java"):
        return []

    allowed = get_allowed_import_prefixes()
    issues: list[dict] = []
    seen_packages: set[str] = set()

    for match in _IMPORT_RE.finditer(gf.content):
        fqcn = match.group(2)
        if _java_import_allowed_under_pom(fqcn, allowed):
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


# Fields that indicate ResDto is being (mis)used as a pagination/batch-result container.
# These fields must NEVER be added to a domain ResDto — the fix must remove the container
# pattern from ServiceImpl and change the return type to List<ResDto>.
_PAGINATION_CONTAINER_FIELDS: frozenset[str] = frozenset({
    # Spring Page / Pageable metadata
    "totalElements", "totalPages", "pageNumber", "numberOfElements", "last", "first",
    # Batch-upload result container fields
    "rowResults", "processedCount", "duplicateCount",
    "uploadRowCount", "successCount", "failCount", "errorCount",
    "totalCount", "insertCount", "updateCount", "deleteCount",
    "skipCount", "resultList", "errorList", "successList",
})


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

    generated_dto_classes: set[str] = set(dto_fields.keys())

    # --- 1. DTO getter/setter field existence check ---
    var_type_re = re.compile(r'(?:final\s+)?(\w+(?:Dto\w*))\s+(\w+)\s*[=;,)]')

    for gf in service_files + dao_files:
        is_dao = gf in dao_files
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
                if prop_name in _PAGINATION_CONTAINER_FIELDS:
                    issues.append({
                        "file_path": gf.file_path,
                        "issue": (
                            f"[STATIC] {var_name}.{method_type}{prop_upper}() called in {gf.file_path} "
                            f"but '{prop_name}' is a pagination/batch-result container field that "
                            f"MUST NOT exist in {dto_name}. ResDto is a domain record DTO, not a container."
                        ),
                        "fix_instruction": (
                            f"REMOVE all pagination/container logic from {gf.file_path}. "
                            f"'{prop_name}' MUST NOT be added to {dto_name}. "
                            f"RULE: service methods that return a list MUST return List<{dto_name}> directly.\n"
                            f"WRONG:  {dto_name} result = new {dto_name}(); result.set{prop_upper}(...); return result;\n"
                            f"CORRECT: return List<{dto_name}> daoResult = dao.selectXxxList(req); return daoResult;\n"
                            f"Steps:\n"
                            f"  1. Change the method return type to List<{dto_name}>.\n"
                            f"  2. Remove the container object creation and all set{prop_upper}/setTotalElements/"
                            f"setTotalPages/setPageNumber/setLast/setContent/setRowResults/setProcessedCount/"
                            f"setDuplicateCount calls.\n"
                            f"  3. Return the DAO result List<{dto_name}> directly."
                        ),
                    })
                elif is_dao:
                    issues.append({
                        "file_path": gf.file_path,
                        "issue": (
                            f"[STATIC] {var_name}.{method_type}{prop_upper}() called in DaoImpl {gf.file_path} "
                            f"but field '{prop_name}' does NOT exist in {dto_name}. "
                            f"DaoImpl MUST NOT access non-existent DTO fields."
                        ),
                        "fix_instruction": (
                            f"REMOVE the {var_name}.{method_type}{prop_upper}() call from {gf.file_path}. "
                            f"DaoImpl methods should be simple one-liner delegations to super methods — "
                            f"they MUST NOT manipulate DTO fields. "
                            f"If the field is genuinely needed, ADD 'private String {prop_name};' to {dto_name} FIRST. "
                            f"Currently declared fields in {dto_name}: {', '.join(sorted(fields)[:15])}"
                        ),
                    })
                else:
                    issues.append({
                        "file_path": dto_file,
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

    # --- 2b. DaoImpl parameter type must be an ACTUAL generated DTO class ---
    _dao_param_type_re = re.compile(
        r'public\s+\S+\s+\w+\s*\(\s*(\w+)\s+\w+\s*\)'
    )
    _ALLOWED_PRIMITIVE_TYPES = {"String", "int", "long", "Integer", "Long", "boolean", "Boolean", "double", "Double"}
    for gf in dao_files:
        for m in _dao_param_type_re.finditer(gf.content):
            param_type = m.group(1)
            if param_type in _ALLOWED_PRIMITIVE_TYPES or param_type == "List":
                continue
            if param_type in generated_dto_classes:
                continue
            issues.append({
                "file_path": gf.file_path,
                "issue": (
                    f"[STATIC] DaoImpl method has parameter type '{param_type}' which is NOT "
                    f"one of the generated DTO classes: {', '.join(sorted(generated_dto_classes))}. "
                    f"This will cause a compilation error."
                ),
                "fix_instruction": (
                    f"Replace '{param_type}' with one of the ACTUAL generated DTO classes: "
                    f"{', '.join(sorted(generated_dto_classes))}. "
                    f"For select queries use the ReqDto class. For CUD (insert/update/delete) use the ResDto class. "
                    f"For sequence/next-ID methods with no meaningful param, use empty params and pass null."
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

    # --- 5. ServiceImpl imports a DTO class that was never generated ---
    _biz_import_re = re.compile(r'import\s+biz\.\w+\.dto\.\w+\.(\w+)\s*;')
    for gf in service_files:
        for m in _biz_import_re.finditer(gf.content):
            imported_class = m.group(1)
            if imported_class not in generated_dto_classes:
                issues.append({
                    "file_path": gf.file_path,
                    "issue": (
                        f"[STATIC] ServiceImpl imports '{imported_class}' but this DTO class was NEVER generated. "
                        f"Generated DTOs are: {', '.join(sorted(generated_dto_classes))}. "
                        f"ServiceImpl MUST NOT import or use non-existent DTO classes."
                    ),
                    "fix_instruction": (
                        f"REMOVE the import of '{imported_class}' and ALL usages of it in {gf.file_path}. "
                        f"Only use DTO classes that were actually generated: "
                        f"{', '.join(sorted(generated_dto_classes))}. "
                        f"If this DTO was needed for ExcelUpload / complex param passing, "
                        f"add the necessary fields to the existing ReqDto instead of inventing a new class."
                    ),
                })

    # --- 6. Mapper XML <if test="fieldName"> references non-existent DTO field ---
    _if_test_re = re.compile(r'<if\s+test\s*=\s*"(\w+)\s*!=\s*null', re.IGNORECASE)
    _mapper_param_type_re = re.compile(r'parameterType\s*=\s*"[^"]*\.(\w+)"')
    mapper_files = [gf for gf in files if gf.file_type == "mapper_xml"]
    for gf in mapper_files:
        param_types_used: set[str] = set()
        for pm in _mapper_param_type_re.finditer(gf.content):
            param_types_used.add(pm.group(1))
        all_related_dto_fields: set[str] = set()
        related_dto_name = ""
        for pt in param_types_used:
            if pt in dto_fields:
                all_related_dto_fields.update(dto_fields[pt])
                related_dto_name = pt
        if not all_related_dto_fields:
            for dn, df in dto_fields.items():
                all_related_dto_fields.update(df)
                if not related_dto_name:
                    related_dto_name = dn
        for m in _if_test_re.finditer(gf.content):
            field_name = m.group(1)
            if all_related_dto_fields and field_name not in all_related_dto_fields:
                issues.append({
                    "file_path": gf.file_path,
                    "issue": (
                        f"[STATIC] Mapper XML <if test=\"{field_name} != null\"> but field '{field_name}' "
                        f"does NOT exist in {related_dto_name}. "
                        f"This will cause a MyBatis reflection error at runtime."
                    ),
                    "fix_instruction": (
                        f"REMOVE the <if test=\"{field_name} != null\"> condition from the Mapper XML, "
                        f"or ADD 'private String {field_name};' to {related_dto_name}. "
                        f"Currently declared fields: {', '.join(sorted(all_related_dto_fields)[:15])}"
                    ),
                })

    # --- 7. ServiceImpl public methods without @ServiceId ---
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


_EXTENDS_RE = re.compile(r'\bextends\s+(\w+)')
_BAD_LOMBOK_RE = re.compile(r'@(Getter|Setter|ToString)\b')
_EQ_HASH_OK_RE = re.compile(r'@EqualsAndHashCode\s*\(\s*callSuper\s*=\s*false\s*\)')
_INNER_CLASS_RE = re.compile(r'\bstatic\s+class\s+\w+')
_FIELD_DECL_RE = re.compile(r'\bprivate\s+[^;]+?\b(\w+)\s*(?:=\s*[^;]+)?;')


def _check_dto_layer_conventions(files: list[GeneratedFile]) -> list[dict]:
    """Enforce Lombok style + no duplicate parent fields + no inner classes.

    Parent class fields are resolved DYNAMICALLY from workspace source files —
    no field names are hardcoded here.
    """
    issues: list[dict] = []

    for gf in files:
        if gf.layer != "backend" or not gf.file_path.endswith(".java"):
            continue
        if gf.file_type not in ("dto_request", "dto_response"):
            continue

        c = gf.content

        # --- Lombok style check (applies to all DTOs) ---
        if _BAD_LOMBOK_RE.search(c):
            issues.append({
                "file_path": gf.file_path,
                "issue": (
                    "[STATIC] DTO uses @Getter/@Setter/@ToString — "
                    "must use @Data + @EqualsAndHashCode(callSuper=false) only"
                ),
                "fix_instruction": (
                    "Remove @Getter, @Setter, @ToString. Use:\n"
                    "  import lombok.Data;\n"
                    "  import lombok.EqualsAndHashCode;\n"
                    "  @Data\n"
                    "  @EqualsAndHashCode(callSuper=false)"
                ),
            })
        if "@Data" not in c:
            issues.append({
                "file_path": gf.file_path,
                "issue": "[STATIC] DTO missing @Data",
                "fix_instruction": "Add @Data and import lombok.Data;",
            })

        # --- Empty class body check ---
        # A DTO that has a class declaration but zero 'private <type> field;' lines is
        # an incomplete skeleton — the LLM never filled in the fields.  Any ServiceImpl
        # that calls getters/setters on this DTO will fail to compile.
        has_class_decl = bool(re.search(r'\bpublic\s+class\s+\w+', c))
        has_any_private_field = bool(_FIELD_DECL_RE.search(c))
        if has_class_decl and not has_any_private_field:
            issues.append({
                "file_path": gf.file_path,
                "issue": (
                    "[STATIC] DTO class body is EMPTY — no 'private <Type> field;' declarations found. "
                    "ServiceImpl cannot call any getter/setter on this DTO until fields are added."
                ),
                "fix_instruction": (
                    "Open the paired ServiceImpl file (included in dependencies) and find EVERY "
                    "getter/setter call made on this DTO class (e.g. dto.getXxx(), dto.setXxx()). "
                    "For each one, add a matching 'private <Type> fieldName;' declaration inside "
                    "this DTO class body.\n"
                    "Example:\n"
                    "  private String userId;\n"
                    "  private String userName;\n"
                    "  private List<CpmsXxxExcelRowReqDto> rowList;\n"
                    "NEVER leave the class body empty — every getter/setter call in ServiceImpl "
                    "MUST have a corresponding field declared here."
                ),
            })
        if not _EQ_HASH_OK_RE.search(c):
            issues.append({
                "file_path": gf.file_path,
                "issue": "[STATIC] DTO missing @EqualsAndHashCode(callSuper=false)",
                "fix_instruction": "Add @EqualsAndHashCode(callSuper=false) and import lombok.EqualsAndHashCode;",
            })

        # --- Inner class check (applies to all DTOs) ---
        if _INNER_CLASS_RE.search(c):
            issues.append({
                "file_path": gf.file_path,
                "issue": "[STATIC] DTO contains an inner static class — FORBIDDEN. DTOs must be flat.",
                "fix_instruction": (
                    "Remove the inner static class entirely.\n"
                    "If a separate data structure is needed (e.g. ExcelRowDto), "
                    "create a SEPARATE top-level DTO file (e.g. CpmsXxxExcelRowReqDto.java).\n"
                    "Update all references to use the new top-level class."
                ),
            })

        # --- Duplicate parent field check (fully dynamic) ---
        extends_m = _EXTENDS_RE.search(c)
        if not extends_m:
            continue
        parent_class = extends_m.group(1)

        # Get parent fields from workspace source (cached after first call)
        parent_fields = get_parent_class_fields(parent_class)
        if not parent_fields:
            continue  # parent not in workspace or has no private fields

        # Collect declared field names in this DTO
        # We look for: private <type> <fieldName>;
        declared: set[str] = {m.group(1) for m in _FIELD_DECL_RE.finditer(c)}

        for fld in sorted(parent_fields & declared):
            issues.append({
                "file_path": gf.file_path,
                "issue": (
                    f"[STATIC] DTO redeclares '{fld}' — already declared in parent class {parent_class}. "
                    f"{parent_class} fields: {', '.join(sorted(parent_fields))}"
                ),
                "fix_instruction": (
                    f"Remove 'private ... {fld} ...' from this DTO. "
                    f"The field '{fld}' is inherited from {parent_class} and must NOT be redeclared.\n"
                    f"All {parent_class} inherited fields are: {', '.join(sorted(parent_fields))}.\n"
                    f"Only declare fields that are NOT in the above list."
                ),
            })

    return issues


def _check_java_class_structure(files: list[GeneratedFile]) -> list[dict]:
    """Check Java class name matches file name and package declaration matches directory path.

    Both mismatches cause 'class X is public, should be declared in a file named X.java'
    and 'package Y does not match expected package Z' compilation errors.
    """
    issues: list[dict] = []
    _class_decl_re = re.compile(r'\bpublic\s+class\s+(\w+)')
    _package_re = re.compile(r'^\s*package\s+([\w.]+)\s*;', re.MULTILINE)

    for gf in files:
        if gf.layer != "backend" or not gf.file_path.endswith(".java"):
            continue

        file_name = gf.file_path.split("/")[-1].replace(".java", "")

        # 1) Class name must match file name
        class_m = _class_decl_re.search(gf.content)
        if class_m:
            declared_class = class_m.group(1)
            if declared_class != file_name:
                issues.append({
                    "file_path": gf.file_path,
                    "issue": (
                        f"[STATIC] Java class name '{declared_class}' does NOT match file name "
                        f"'{file_name}.java'. Java requires the public class name to exactly match "
                        f"the file name — this is a compilation error."
                    ),
                    "fix_instruction": (
                        f"Rename the class declaration from 'public class {declared_class}' to "
                        f"'public class {file_name}'. Also update all import statements and references "
                        f"in other generated files that reference this class."
                    ),
                })

        # 2) Package declaration must match directory structure
        pkg_m = _package_re.search(gf.content)
        if pkg_m:
            declared_pkg = pkg_m.group(1)
            parts = gf.file_path.replace("\\", "/").split("/")
            if "java" in parts:
                java_idx = len(parts) - 1 - parts[::-1].index("java")
                expected_pkg_parts = parts[java_idx + 1:-1]
                expected_pkg = ".".join(expected_pkg_parts)
                if expected_pkg and declared_pkg != expected_pkg:
                    issues.append({
                        "file_path": gf.file_path,
                        "issue": (
                            f"[STATIC] Package declaration 'package {declared_pkg};' does NOT match "
                            f"directory structure (expected 'package {expected_pkg};'). "
                            f"This causes a compilation error."
                        ),
                        "fix_instruction": (
                            f"Change the first line from 'package {declared_pkg};' to "
                            f"'package {expected_pkg};'. The package must always match the directory path."
                        ),
                    })

    return issues


def _check_dao_service_return_types(files: list[GeneratedFile]) -> list[dict]:
    """Check that ServiceImpl assignment types match DaoImpl declared return types.

    Detects obvious type mismatches like:
      int count = daoImpl.selectXxxList(req);   ← DAO returns List but assigned to int
      List<Dto> list = daoImpl.selectXxxCount(req);  ← DAO returns int but assigned to List
    """
    issues: list[dict] = []

    # Build DaoImpl method signature map
    _pub_sig_re = re.compile(
        r'public\s+([\w<>?,\[\] ]+?)\s+(\w+)\s*\(([^)]*)\)',
        re.MULTILINE,
    )
    dao_sigs: dict[str, dict[str, str]] = {}  # {ClassName: {method: return_type}}
    dao_simple_map: dict[str, str] = {}       # {simpleVarName: ClassName}

    for gf in files:
        if gf.layer != "backend" or not gf.file_path.endswith(".java"):
            continue
        cname = gf.file_path.split("/")[-1].replace(".java", "")
        if "DaoImpl" not in cname:
            continue
        sigs: dict[str, str] = {}
        for m in _pub_sig_re.finditer(gf.content):
            ret = m.group(1).strip()
            mname = m.group(2)
            if mname != cname:  # skip constructor
                sigs[mname] = ret
        dao_sigs[cname] = sigs
        # Register camelCase and without-Impl variants
        simple = cname[0].lower() + cname[1:]
        dao_simple_map[simple] = cname
        if cname.endswith("Impl"):
            dao_simple_map[simple[:-4]] = cname  # without "Impl" suffix

    # Scan ServiceImpl for assignments of the form: TypeName varName = daoVar.method(...)
    _assign_dao_re = re.compile(
        r'([\w<>?,\[\] ]+?)\s+\w+\s*=\s*(\w+Dao(?:Impl)?)\s*\.\s*(\w+)\s*\(',
        re.MULTILINE,
    )

    def _is_list(t: str) -> bool:
        return "List<" in t or t.strip() == "List"

    def _is_scalar_num(t: str) -> bool:
        return t.strip() in {"int", "Integer", "long", "Long"}

    def _is_void(t: str) -> bool:
        return t.strip() == "void"

    for gf in files:
        if gf.layer != "backend" or not gf.file_path.endswith(".java"):
            continue
        cname = gf.file_path.split("/")[-1].replace(".java", "")
        if "ServiceImpl" not in cname:
            continue

        for m in _assign_dao_re.finditer(gf.content):
            assigned_type = m.group(1).strip()
            dao_var = m.group(2)
            called_method = m.group(3)

            # Find which DaoImpl this variable refers to
            dao_class = dao_simple_map.get(dao_var) or dao_simple_map.get(
                dao_var[:-4] if dao_var.endswith("Impl") else dao_var
            )
            if not dao_class:
                continue
            sigs = dao_sigs.get(dao_class, {})
            if called_method not in sigs:
                continue  # already caught by method-existence check

            declared_ret = sigs[called_method]

            # Detect obvious mismatches
            mismatch_desc = ""
            if _is_list(assigned_type) and not _is_list(declared_ret) and not _is_void(declared_ret):
                mismatch_desc = (
                    f"ServiceImpl assigns result to List but DaoImpl returns '{declared_ret}' (not a List)"
                )
            elif _is_scalar_num(assigned_type) and _is_list(declared_ret):
                mismatch_desc = (
                    f"ServiceImpl assigns result to '{assigned_type}' but DaoImpl returns '{declared_ret}' (a List)"
                )
            elif (
                "Dto" in assigned_type and "Dto" in declared_ret
                and not _is_list(assigned_type) and not _is_list(declared_ret)
                and assigned_type.strip() != declared_ret.strip()
            ):
                mismatch_desc = (
                    f"ServiceImpl assigns result to '{assigned_type}' but DaoImpl returns '{declared_ret}'"
                )

            if mismatch_desc:
                issues.append({
                    "file_path": gf.file_path,
                    "issue": (
                        f"[STATIC] Return type mismatch for {dao_var}.{called_method}(): "
                        f"{mismatch_desc}. This is a compilation error."
                    ),
                    "fix_instruction": (
                        f"Fix the type mismatch for {dao_var}.{called_method}().\n"
                        f"  DaoImpl declares: public {declared_ret} {called_method}(...)\n"
                        f"  ServiceImpl assigns to: {assigned_type}\n"
                        f"Options:\n"
                        f"  1. Change the variable type in ServiceImpl to match DaoImpl's return type '{declared_ret}'\n"
                        f"  2. OR change DaoImpl's return type to '{assigned_type}' and update "
                        f"     super.selectList()/selectOne() accordingly\n"
                        f"The two sides MUST match exactly."
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
    issues.extend(_check_java_class_structure(files))
    issues.extend(_check_dao_service_return_types(files))
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


def _java_import_allowed_under_pom(fqcn: str, allowed_prefixes: set[str]) -> bool:
    """POM-based import allowlist with fixes for two-segment groupId false positives.

    e.g. org.apache.maven.surefire → allowed prefix org.apache, which must NOT imply POI.
    """
    if fqcn.startswith("org.apache.poi"):
        return "org.apache.poi" in get_pom_group_ids()
    return _is_import_allowed(fqcn, allowed_prefixes)


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

        if not _java_import_allowed_under_pom(fqcn, allowed_prefixes):
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
            "╔══════════════════════════════════════════════════════════════════════════╗\n"
            "║  RULE 0 — THE MOST FUNDAMENTAL RULE (applies to EVERY line you write)  ║\n"
            "╚══════════════════════════════════════════════════════════════════════════╝\n"
            "BEFORE writing any import, @Autowired field, method call, or variable assignment:\n"
            "  (a) VERIFY IT EXISTS: The class, method, or field you are about to use MUST actually\n"
            "      exist in the codebase. Check the Dependencies section below for generated DTOs/DAOs.\n"
            "      Check pom.xml for available libraries. If you cannot confirm it exists — DO NOT USE IT.\n"
            "  (b) MATCH THE TYPES EXACTLY:\n"
            "      - Every method call MUST pass arguments whose types exactly match the method signature.\n"
            "      - Every variable that receives a return value MUST have the exact return type of the method.\n"
            "      - WRONG: validateDate(request.getEducationDate(), \"교육일자\")  ← if getEducationDate() returns Date but validateDate(String,String)\n"
            "      - CORRECT: declare all DTO date fields as String so getEducationDate() returns String\n"
            "  (c) NEVER INVENT METHODS: Do NOT call a method on any utility/library that you are not\n"
            "      100% certain exists. Invented method calls compile to 'method not found' errors.\n"
            "      WRONG: CommonUtils.convertArrayToList(ids, Dto.class, \"id\")  ← invented, does not exist\n"
            "      WRONG: CommonUtils.toList(array)                              ← invented, does not exist\n"
            "      CORRECT: use documented methods only — e.g. CommonUtils.filterByStatus(list, GridStatus.INSERTED)\n"
            "  (d) IMPORTS: Every import MUST correspond to a class that exists in pom.xml dependencies.\n"
            "      NEVER import a class you invented or that is not in the pom.xml library list.\n\n"
            "This rule exists because type mismatches and non-existent method calls are the #1 cause of\n"
            "compilation failures in generated code. Think before every line: 'Does this exist? Do the types match?'\n\n"
            "╔══════════════════════════════════════════════════════════╗\n"
            "║  TOP-PRIORITY RULES — VIOLATING ANY = REJECTED CODE    ║\n"
            "╚══════════════════════════════════════════════════════════╝\n"
            "1. LOGGING: ServiceImpl MUST use @Slf4j (Lombok) — NEVER LoggerFactory.getLogger().\n"
            "   NEVER write: private static final Logger log = LoggerFactory.getLogger(Xxx.class);\n"
            "   NEVER import org.slf4j.Logger or org.slf4j.LoggerFactory.\n"
            "   EVERY public method MUST start with log.debug(\"Service Method : {methodName}, Input Param={}\", param.toString());\n\n"
            "2. EXCEPTION HANDLING — ABSOLUTE RULES:\n"
            "   a) NEVER log.error()/log.warn() before throw HscException.\n"
            "      WRONG:   log.error(\"msg\", e); throw HscException.systemError(\"msg\", e);\n"
            "      CORRECT: throw HscException.systemError(\"msg\", e);\n"
            "   b) throw HscException.systemError() MUST ALWAYS be inside a try-catch block.\n"
            "      The second argument MUST be the caught Exception variable (e).\n"
            "      WRONG (bare throw, no e):   throw HscException.systemError(\"msg\");\n"
            "      WRONG (outside try-catch):  if (x == null) throw HscException.systemError(\"msg\");\n"
            "      CORRECT:\n"
            "          try {\n"
            "              // ... business logic ...\n"
            "          } catch (Exception e) {\n"
            "              throw HscException.systemError(\"msg\", e);\n"
            "          }\n"
            "   c) For validation (null checks, invalid values), throw IllegalArgumentException or\n"
            "      wrap the validating block in try-catch and use HscException.systemError(\"msg\", e).\n\n"
            "3. DAO METHOD NAMES: NEVER bare CRUD verb. Always append domain noun.\n"
            "   WRONG:  public int insert(...)       CORRECT: public int insertEduPgm(...)\n"
            "   WRONG:  public List select(...)      CORRECT: public List selectEduPgmList(...)\n\n"
            "4. SERVICE→DAO CALLS: NEVER call bare base-class methods on DAO variable.\n"
            "   WRONG:  daoImpl.insert(dto)          CORRECT: daoImpl.insertEduPgm(dto)\n"
            "   WRONG:  daoImpl.select(dto)          CORRECT: daoImpl.selectEduPgmList(dto)\n\n"
            "5. UUID: NEVER use java.util.UUID — NEVER import java.util.UUID. Use String for all ID fields.\n"
            "   WRONG:  request.setId(UUID.randomUUID().toString());\n"
            "   CORRECT: ID values come from DB sequence or are already in the DTO.\n\n"
            "5a. CommonUtils — ONLY CALL METHODS THAT ACTUALLY EXIST in com.common.sy.CommonUtils.\n"
            "   NEVER invent CommonUtils methods that are not documented — they cause compilation errors.\n"
            "   KNOWN non-existent methods (DO NOT call these):\n"
            "     CommonUtils.convertArrayToList(...)  ← DOES NOT EXIST\n"
            "     CommonUtils.convertList(...)          ← DOES NOT EXIST\n"
            "     CommonUtils.toList(...)               ← DOES NOT EXIST\n"
            "     CommonUtils.getUuid()                 ← DOES NOT EXIST\n"
            "   For array/list conversion use standard Java:\n"
            "     Arrays.asList(array)  /  List.of(...)  /  stream().collect(Collectors.toList())\n"
            "   When calling any CommonUtils method, VERIFY the parameter types match the method signature exactly.\n\n"
            "5b. DTO FIELD TYPES — STRICT WHITELIST (NEVER use anything outside this list):\n"
            "   ALLOWED DTO field types (ReqDto + ResDto):\n"
            "     String    ← use for ALL text, dates, datetimes, IDs, codes, flags, comma-separated values\n"
            "     int / Integer\n"
            "     long / Long\n"
            "     BigDecimal  ← ONLY for monetary/decimal amounts\n"
            "     boolean / Boolean\n"
            "   ABSOLUTELY FORBIDDEN as DTO field types:\n"
            "     Date, java.util.Date, LocalDate, LocalDateTime   → ALWAYS use String instead\n"
            "     List<...>, ArrayList<...>                        → NEVER in DTO; handled at Service/DAO level\n"
            "     Map<...>, HashMap<...>                           → NEVER in DTO\n"
            "     Object, any custom class, any enum               → NEVER in DTO\n"
            "   WRONG:  private Date educationDate;         → causes type mismatch everywhere\n"
            "   WRONG:  private LocalDate educationDate;    → causes type mismatch everywhere\n"
            "   WRONG:  private List<String> codeList;      → Service treats as List but caller sends String\n"
            "   WRONG:  private List<ResDto> children;      → NEVER embed lists inside DTO\n"
            "   WRONG:  private Map<String,Object> extra;   → NEVER put Map in DTO\n"
            "   CORRECT: private String educationDate;      → DB stores VARCHAR; pass as String everywhere\n"
            "   CORRECT: private String codeList;           → comma-separated '01,02,03' as String\n"
            "   REASON: If a DTO field is not a simple scalar, the Service cannot call getter/setter\n"
            "           with consistent types. The framework handles collections at the Service/DAO boundary.\n\n"
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
            "     c) Assign the result to a variable of the EXACT return type DaoImpl declares.\n"
            "   TYPE CHAIN RULE — FOLLOW THE DECLARED TYPE END-TO-END:\n"
            "     DTO field 'private String eduDate;' → getter returns String → pass as String everywhere.\n"
            "     NEVER coerce or cast a getter return value to a different type.\n"
            "     If you find yourself needing to cast (e.g. (Date) dto.getEduDate()), STOP:\n"
            "       — the DTO field type is wrong. Change the DTO field to String instead.\n"
            "     ALL DTO fields that represent dates, codes, or IDs must be String in the DTO.\n\n"
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
            "- NEVER import org.apache.poi.* — Apache POI is NOT in pom.xml and WILL cause compilation failure.\n"
            "  If the spec requires Excel export, do NOT use POI. Instead, return List<ResDto> from the service\n"
            "  and let the frontend handle Excel generation via the browser (PrimeVue DataTable export).\n"
            "  The service method signature for export should be identical to the search method.\n"
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
                    "\n"
                    "★ DaoImpl PARAMETER TYPE RULES — ABSOLUTE (VIOLATION = COMPILATION ERROR) ★\n"
                    "  The ONLY types allowed as DaoImpl method parameters are:\n"
                    "    1. The ACTUAL generated ReqDto class — e.g. CpmsEduRegLstReqDto\n"
                    "    2. The ACTUAL generated ResDto class — e.g. CpmsEduRegLstResDto\n"
                    "    3. List<CpmsXxxResDto> — List of the ACTUAL generated ResDto\n"
                    "    4. Java primitives/wrappers: String, int, long, Integer, Long, boolean\n"
                    "    5. () empty — no parameter at all (for sequence/next-ID)\n"
                    "  NOTHING ELSE IS ALLOWED. Period.\n\n"
                    "  ██ FORBIDDEN type names (NEVER use these as parameter types): ██\n"
                    "    saveDto, reqDto, resDto, dto, Dto, item, row, entity, record, param,\n"
                    "    request, response, data, obj, Object, Map, HashMap, model, form, vo, bean\n"
                    "  These are NOT Java class names — they cause compilation errors.\n\n"
                    "  WRONG: public int selectDuplicateCount(saveDto param)     → 'saveDto' is NOT a class\n"
                    "  WRONG: public int selectEduRegNextId(Object param)        → Object is forbidden\n"
                    "  WRONG: public ResDto selectUserInfo(row param)            → 'row' is NOT a class\n"
                    "  WRONG: public int insertEduReg(dto param)                → 'dto' is NOT a class\n"
                    "  WRONG: public int insertEduReg(reqDto param)             → 'reqDto' is NOT a class\n"
                    "  CORRECT: public int selectDuplicateCount(CpmsEduRegLstResDto param)  → actual class name\n"
                    "  CORRECT: public int selectEduRegNextId(CpmsEduRegLstReqDto param)    → actual class name\n"
                    "  CORRECT: public CpmsEduRegLstResDto selectUserInfo(CpmsEduRegLstReqDto param) → actual class names\n"
                    "  CORRECT: public int selectEduRegNextId() { return super.selectOne(\"selectEduRegNextId\", null); }\n\n"
                    "  ██ GETTER/SETTER RULE — ONLY call fields that EXIST in the DTO ██\n"
                    "  BEFORE writing param.getXxx() or param.setXxx() in DaoImpl or ServiceImpl,\n"
                    "  VERIFY the field 'xxx' exists as 'private <Type> xxx;' in the DTO class.\n"
                    "  If the field does NOT exist in the DTO, DO NOT call it. This is a compilation error.\n"
                    "  Example: If CpmsEduRegLstReqDto does NOT have 'uploadRowCount' field,\n"
                    "    WRONG:  param.getUploadRowCount()  → compilation error, field doesn't exist\n"
                    "\n"
                    "★ DaoImpl super.* MATCHING RULES — ABSOLUTE ★\n"
                    "  The super method MUST match the operation type of the Java method name:\n"
                    "  - selectXxx / selectXxxList  → super.selectOne() or super.selectList()\n"
                    "  - insertXxx                  → super.insert()\n"
                    "  - updateXxx (single row)     → super.update()\n"
                    "  - updateXxx (List param)     → super.batchUpdateReturnSumAffectedRows()\n"
                    "  - deleteXxx (single row)     → super.delete()   ← NOT super.update()!\n"
                    "  - deleteXxx (List param)     → super.batchUpdateReturnSumAffectedRows()\n"
                    "  WRONG: public int deleteEduReg(ResDto p) { return super.update(\"deleteEduReg\", p); }\n"
                    "  CORRECT: public int deleteEduReg(ResDto p) { return super.delete(\"deleteEduReg\", p); }\n"
            "- Do NOT generate DAO interface or Service interface files — only DaoImpl and ServiceImpl.\n"
            "- All fields used in ServiceImpl and DaoImpl MUST exist in the corresponding DTO.\n"
            "- NEVER call getter/setter for a field that does NOT exist in the DTO:\n"
            "    If DTO has 'private String eduNm;' → dto.getEduNm() and dto.setEduNm() are OK.\n"
            "    If DTO does NOT have 'uploadRowCount' → dto.getUploadRowCount() is a COMPILATION ERROR.\n"
            "    BEFORE writing any .getXxx() or .setXxx(), SCAN the DTO class in Dependencies below\n"
            "    and confirm the field is declared as 'private <Type> fieldName;'.\n"
            "    DO NOT invent fields like uploadRowCount, totalCount, successCount, failCount —\n"
            "    these are batch-result container fields that NEVER belong on a domain DTO.\n"
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
            "║  FINAL CHECKLIST — VERIFY EVERY ITEM BEFORE OUTPUT     ║\n"
            "╚══════════════════════════════════════════════════════════╝\n"
            "★ TYPE & EXISTENCE CHECK (RULE 0) ★\n"
            "□ Every import → class exists in pom.xml? (no invented imports)\n"
            "□ Every @Autowired field → class exists and is a real Spring bean?\n"
            "□ Every method call → method ACTUALLY EXISTS with that name on that class?\n"
            "   - CommonUtils: only call methods confirmed to exist (e.g. filterByStatus). NEVER invent new ones.\n"
            "   - DaoImpl: only call methods you generated in DaoImpl — no invented DAO methods.\n"
            "□ Every method call → argument types EXACTLY match method parameter types?\n"
            "   - If method signature is (String, String), pass (String, String) — NOT (Date, String)\n"
            "   - If DTO date field is String, getter returns String — use as String everywhere\n"
            "□ Every variable receiving a return value → type matches the method's declared return type?\n"
            "□ ALL DTO date fields are String? (NEVER Date/LocalDate/LocalDateTime — 'private String xxxDate;')\n"
            "□ DaoImpl parameter type is the ACTUAL DTO class name (e.g. CpmsXxxReqDto)?\n"
            "   FORBIDDEN: request, response, dto, reqDto, resDto, saveDto, param, item, row, Object\n"
            "   WRONG:   public Integer selectXxxCount(request param)     → 'request' is NOT a class\n"
            "   CORRECT: public Integer selectXxxCount(CpmsXxxReqDto param)\n"
            "\n"
            "★ STANDARD RULES ★\n"
            "□ @Slf4j? (NO LoggerFactory, NO import org.slf4j.*)\n"
            "□ log.debug(\"Service Method : xxx\") as FIRST line in every public method?\n"
            "□ NO log.error/warn before throw?\n"
            "□ DaoImpl method name → domain noun? (NEVER bare insert/select/update/delete)\n"
            "□ ServiceImpl DAO call → full wrapper name? (NEVER daoImpl.insert())\n"
            "□ NO java.util.UUID, NO CommonUtils.getUuid()\n"
            "□ save() takes List<ResDto>? (NOT single ReqDto)\n"
            "□ GridStatus + CommonUtils.filterByStatus()? (NOT getSortDirection())\n"
            "□ NO manual fstCretDtm/lastMdfcDtm/fstCrtrId/lastMdfrId setting?\n"
            "□ NO DateTimeFormatter/LocalDateTime.now().format() in ServiceImpl?\n"
            "□ EVERY dto.getXxx()/dto.setXxx() — field 'xxx' declared in the DTO?\n"
            "□ ServiceImpl ONLY uses DTO fields and DAO methods that actually exist?\n"
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

            # ── Pre-build DAO whitelist + DTO field whitelist for service_impl ──
            # Extracted BEFORE user is built so we can put it FIRST in the prompt.
            # LLMs give highest weight to content at the beginning of the message;
            # the whitelist must appear before the spec so constraints are clear
            # before the model starts generating.
            _pre_whitelist_block = ""
            _pre_allowed_methods: set[str] = set()
            _pre_dao_var_name: str = ""
            if file_entry.file_type == "service_impl":
                _pre_dao_sigs: list[str] = []
                # ── DTO field extraction ───────────────────────────────────────
                # Extract ACTUAL fields from the generated DTO files so the LLM
                # can ONLY use field names that truly exist.
                _dto_field_lines: list[str] = []
                for _path, _gf in ctx.generated_files.items():
                    if _gf.file_type in ("dto_request", "dto_response"):
                        _cls_m = re.search(r'public\s+class\s+(\w+(?:Req|Res)Dto)\b', _gf.content)
                        _cls_name = _cls_m.group(1) if _cls_m else _gf.file_path.split("/")[-1].replace(".java", "")
                        fields: list[str] = []
                        for _fm in re.finditer(
                            r'private\s+(\S+(?:<[^>]+>)?)\s+(\w+)\s*;', _gf.content
                        ):
                            fields.append(f"    {_fm.group(1)} {_fm.group(2)}")
                        if fields:
                            _dto_field_lines.append(f"  {_cls_name}:")
                            _dto_field_lines.extend(fields)

                # ── DAO method extraction ──────────────────────────────────────
                for _path, _gf in ctx.generated_files.items():
                    if _gf.file_type == "dao_impl":
                        _cm = re.search(r'public\s+class\s+(\w+DaoImpl)\b', _gf.content)
                        _cls = _cm.group(1) if _cm else ""
                        if _cls:
                            _pre_dao_var_name = _cls[0].lower() + _cls[1:]
                        for _m in re.finditer(r'public\s+(\S+)\s+(\w+)\s*\(([^)]*)\)', _gf.content):
                            _rtype, _mname, _params = _m.group(1), _m.group(2), _m.group(3).strip()
                            if _cls and _mname == _cls:
                                continue
                            _pre_dao_sigs.append(f"  {_pre_dao_var_name}.{_mname}({_params})  // returns {_rtype}")
                if _pre_dao_sigs:
                    _pre_allowed_methods = {s.split(".")[1].split("(")[0].strip() for s in _pre_dao_sigs}
                    _dto_whitelist_block = ""
                    if _dto_field_lines:
                        _dto_whitelist_block = (
                            "╔══════════════════════════════════════════════════════════════════╗\n"
                            "║  DTO FIELD WHITELIST — ABSOLUTE CONSTRAINT                      ║\n"
                            "║  ServiceImpl MUST ONLY use getters/setters for fields below.    ║\n"
                            "║  Using a getter/setter for a NON-LISTED field = COMPILE ERROR.  ║\n"
                            "╚══════════════════════════════════════════════════════════════════╝\n"
                            "Actual DTO fields (these are the ONLY valid fields):\n"
                            + "\n".join(_dto_field_lines) + "\n\n"
                            "ABSOLUTE DTO RULES:\n"
                            "  ★ NEVER call reqDto.getXxx() or resDto.setXxx() for a field NOT listed above.\n"
                            "  ★ If you need a new field, you CANNOT add it — the DTOs are already generated.\n"
                            "  ★ If the spec mentions a field not in the list, IGNORE that field or\n"
                            "    use the closest existing field from the list above.\n"
                            "  ★ Forbidden getter/setter examples: anything not in the list above.\n"
                            "══════════════════════════════════════════════════════════════════════\n\n"
                        )
                    _pre_whitelist_block = (
                        _dto_whitelist_block
                        + "╔══════════════════════════════════════════════════════════════════╗\n"
                        "║  DAO METHOD WHITELIST — ABSOLUTE CONSTRAINT                     ║\n"
                        "║  ServiceImpl MUST ONLY call the methods listed below.           ║\n"
                        "║  Calling ANY other method = COMPILATION FAILURE.                ║\n"
                        "╚══════════════════════════════════════════════════════════════════╝\n"
                        f"Allowed DAO variable: {_pre_dao_var_name}\n"
                        f"Allowed method names: {', '.join(sorted(_pre_allowed_methods))}\n\n"
                        "Full signatures:\n"
                        + "\n".join(_pre_dao_sigs) + "\n\n"
                        "ABSOLUTE RULES (read before looking at the spec):\n"
                        "  ★ ONLY call methods from the whitelist above.\n"
                        "  ★ NEVER invent a new DAO method name not in the whitelist.\n"
                        "  ★ If the spec seems to require an operation not in the whitelist,\n"
                        "    implement it using ONLY the methods above (e.g. loop over allowed call).\n"
                        "  ★ Forbidden: any daoVar.xxx() where xxx is not in 'Allowed method names'.\n"
                        "══════════════════════════════════════════════════════════════════════\n\n"
                    )

            # Build user message — whitelist FIRST for service_impl
            if _pre_whitelist_block:
                user = _pre_whitelist_block
                user += f"Specification:\n{ctx.spec_markdown}\n{schema_ctx}\n{table_ctx}"
            else:
                user = (
                    f"Specification:\n{ctx.spec_markdown}\n{schema_ctx}\n"
                    f"{table_ctx}"
                )
            if deps_text:
                user += f"Dependencies:\n{deps_text}\n\n"
            user += f"Generate: {file_entry.file_path}\nType: {file_entry.file_type}\nDescription: {file_entry.description}\n"

            if file_guide:
                user += f"\n--- CODING GUIDE ({file_entry.file_type}) ---\n{file_guide}\n--- END GUIDE ---\n"

            # Type-specific generation instructions
            if file_entry.file_type == "dao_impl":
                # ── Inject concrete DTO class names so LLM never writes 'dto' as a type ──
                _dao_req_classes: list[str] = []
                _dao_res_classes: list[str] = []
                for _p, _gf in ctx.generated_files.items():
                    if _gf.file_type == "dto_request":
                        _cm2 = re.search(r'public\s+class\s+(\w+ReqDto)\b', _gf.content)
                        if _cm2:
                            _dao_req_classes.append(_cm2.group(1))
                    elif _gf.file_type == "dto_response":
                        _cm2 = re.search(r'public\s+class\s+(\w+ResDto)\b', _gf.content)
                        if _cm2:
                            _dao_res_classes.append(_cm2.group(1))

                if _dao_req_classes or _dao_res_classes:
                    _req_list = ", ".join(_dao_req_classes) if _dao_req_classes else "(none)"
                    _res_list = ", ".join(_dao_res_classes) if _dao_res_classes else "(none)"
                    _ex_res = _dao_res_classes[0] if _dao_res_classes else "XxxResDto"
                    _ex_req = _dao_req_classes[0] if _dao_req_classes else "XxxReqDto"
                    user += (
                        f"\n╔══════════════════════════════════════════════════════════╗\n"
                        f"║  PARAMETER TYPE WHITELIST — ABSOLUTE CONSTRAINT          ║\n"
                        f"╚══════════════════════════════════════════════════════════╝\n"
                        f"DaoImpl method parameters MUST use ONLY these types:\n"
                        f"  • ReqDto  → {_req_list}\n"
                        f"  • ResDto  → {_res_list}\n"
                        f"  • List<ResDto> → List<{_ex_res}>\n"
                        f"  • Primitives  → String, int, long, Integer, Long, boolean\n"
                        f"  • No-param    → () — use super.selectOne(\"id\", null) internally\n\n"
                        f"FORBIDDEN parameter types (NOT Java classes — will not compile):\n"
                        f"  ✗ saveDto, dto, Dto, reqDto, resDto   ✗ item, row, entity, record\n"
                        f"  ✗ Object, param (as type name)        ✗ data, obj, model, form, vo, bean\n"
                        f"  ✗ request, response                   ✗ any other non-DTO word\n\n"
                        f"CORRECT examples using YOUR actual class names:\n"
                        f"  public List<{_ex_res}> selectXxxList({_ex_req} param)\n"
                        f"  public {_ex_res} selectXxx({_ex_req} param)\n"
                        f"  public int selectDuplicateCount({_ex_res} param)\n"
                        f"  public int insertXxx({_ex_res} param)\n"
                        f"  public int updateXxx(List<{_ex_res}> param)\n"
                        f"  public int deleteXxx(List<{_ex_res}> param)\n"
                        f"  public int selectNextId()  ← no param, pass null internally\n\n"
                        f"WRONG examples (these will ALL fail to compile):\n"
                        f"  ✗ public int selectDuplicateCount(saveDto param)  ← 'saveDto' is NOT a class!\n"
                        f"  ✗ public int selectDuplicateCount(dto param)      ← 'dto' is not a class\n"
                        f"  ✗ public int selectDuplicateCount(item param)     ← 'item' is not a class\n"
                        f"  ✗ public int selectDuplicateCount(row param)      ← 'row' is not a class\n"
                        f"  ✗ public int selectNextId(Object param)           ← Object is forbidden\n"
                        f"══════════════════════════════════════════════════════════════\n\n"
                    )

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

            elif file_entry.file_type == "mapper_xml":
                user += (
                    "\n╔══════════════════════════════════════════════════════════╗\n"
                    "║  MANDATORY: Mapper XML MUST include ALL CRUD operations  ║\n"
                    "╚══════════════════════════════════════════════════════════╝\n"
                    "A complete Mapper XML MUST contain ALL of the following SQL statements:\n"
                    "  1. <select id=\"selectXxxList\">  — list query with optional <if test> filters\n"
                    "  2. <select id=\"selectXxx\">      — single row query by PK\n"
                    "  3. <insert id=\"insertXxx\">      — insert single row\n"
                    "  4. <update id=\"updateXxx\">      — batch update via <foreach> (for grid save)\n"
                    "  5. <delete id=\"deleteXxx\">      — batch delete via <foreach> (for grid save)\n\n"
                    "Where 'Xxx' is the domain noun (e.g. EduPgm, Window, User — match the entity name).\n"
                    "ALL 5 SQL statements are MANDATORY regardless of spec wording.\n"
                    "ServiceImpl's save() method depends on update + delete statements — omitting them\n"
                    "causes ServiceImpl to invent non-existent DAO methods and fail to compile.\n\n"
                    "Additional SQL to add when spec requires:\n"
                    "  - Duplicate check: <select id=\"selectDuplicateCount\" resultType=\"int\">\n"
                    "  - Lookup by non-PK key: <select id=\"selectXxxByYyy\">\n"
                    "  - Bulk insert: <insert id=\"insertXxxList\"> with <foreach>\n\n"
                    "NAMING RULES (must match DaoImpl method names exactly):\n"
                    "  CORRECT: <update id=\"updateEduPgm\">   → DaoImpl: public int updateEduPgm(List<ResDto> p)\n"
                    "  WRONG:   <update id=\"update\">         → DaoImpl cannot use bare verb 'update'\n"
                    "  WRONG:   <update id=\"updateList\">     → domain noun missing (must be updateEduPgmList or updateEduPgm)\n\n"
                    "TECHNICAL RULES:\n"
                    "  - namespace MUST be the full DaoImpl class path: e.g., namespace=\"biz.edu.dao.EduA001DaoImpl\"\n"
                    "  - parameterType: use the full DTO class path (biz.edu.dto.request.XxxReqDto)\n"
                    "  - resultType: use the full DTO class path (biz.edu.dto.response.XxxResDto)\n"
                    "  - NEVER use bare < or > — wrap in CDATA: <![CDATA[<=]]>\n"
                    "  - Use <if test=\"param != null and param != ''\"> for optional WHERE filters\n"
                    "  - batch update/delete: use <foreach collection=\"list\" item=\"item\"> pattern\n\n"
                    "★ <if test> FIELD EXISTENCE RULE — ABSOLUTE ★\n"
                    "  Every field name used in <if test=\"fieldName != null\"> MUST exist as a declared field\n"
                    "  in the parameterType DTO (ReqDto or ResDto). Check the DTO in Dependencies below.\n"
                    "  WRONG: <if test=\"uploadRowCount != null\"> — if uploadRowCount is NOT in the DTO\n"
                    "  WRONG: <if test=\"totalCount != null\"> — if totalCount is NOT in the DTO\n"
                    "  Before adding any <if test>, VERIFY the field exists in the DTO.\n"
                    "=== END MAPPER XML MANDATORY RULES ===\n"
                )

            elif file_entry.file_type == "dto_request":
                user += (
                    "\n=== MANDATORY: Request DTO — match biz.sample.dto.request.UserReqDto ===\n"
                    "Imports (use lombok.Data + lombok.EqualsAndHashCode + SearchBaseDto only for Lombok/base):\n"
                    "  import lombok.Data;\n"
                    "  import lombok.EqualsAndHashCode;\n"
                    "  import com.common.dto.base.SearchBaseDto;\n\n"
                    "Class annotations (exactly, no @Getter/@Setter/@ToString):\n"
                    "  @Data\n"
                    "  @EqualsAndHashCode(callSuper=false)\n"
                    "  public class <ScreenPrefix>ReqDto extends SearchBaseDto {\n\n"
                    "Declare ONLY screen-specific search fields.\n"
                    f"FORBIDDEN — inherited from SearchBaseDto, DO NOT redeclare:\n"
                    f"  {get_parent_class_source_block('SearchBaseDto')}\n"
                    "FORBIDDEN: @Getter @Setter @ToString — use @Data + @EqualsAndHashCode(callSuper=false) only.\n"
                    "FORBIDDEN: inner static class inside DTO — if you need ExcelRowDto or similar,\n"
                    "  create a SEPARATE top-level DTO file (e.g. CpmsXxxExcelRowReqDto.java).\n"
                    "=== END ===\n"
                )

            elif file_entry.file_type == "dto_response":
                user += (
                    "\n=== MANDATORY: Response DTO — same Lombok pattern as UserReqDto ===\n"
                    "  import lombok.Data;\n"
                    "  import lombok.EqualsAndHashCode;\n"
                    "  import com.common.dto.base.AuditBaseDto;\n"
                    "  (add import java.io.Serializable; and 'implements Serializable' + serialVersionUID if used)\n\n"
                    "  @Data\n"
                    "  @EqualsAndHashCode(callSuper=false)\n"
                    "  public class <ScreenPrefix>ResDto extends AuditBaseDto implements Serializable {\n\n"
                    "FORBIDDEN: redeclare AuditBaseDto fields: fstCretDtm, fstCrtrId, lastMdfcDtm, lastMdfrId\n"
                    "FORBIDDEN: @Getter @Setter @ToString on class — use @Data + @EqualsAndHashCode(callSuper=false)\n"
                    "=== END ===\n"
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

                # ── Store for post-generation inline whitelist check ──────────
                _svc_allowed_methods: set[str] = set()
                _svc_dao_var_name: str = dao_var_name

                if dao_method_sigs:
                    sigs_list = "\n".join(dao_method_sigs)
                    allowed_method_names = sorted({
                        sig.split(".")[1].split("(")[0].strip()
                        for sig in dao_method_sigs
                    })
                    _svc_allowed_methods = set(allowed_method_names)
                    allowed_list = ", ".join(allowed_method_names)
                    user += (
                        f"\n=== AVAILABLE DAO METHODS — TYPE CONTRACT (read carefully) ===\n"
                        f"Format: daoVar.methodName(paramType param)  // returns ReturnType\n"
                        f"{sigs_list}\n\n"
                        f"RULES — ALL mandatory:\n"
                        f"  1. ONLY call methods from the whitelist above. NEVER invent a new method name.\n"
                        f"  2. Assign result to a variable whose type EXACTLY matches '// returns <X>'.\n"
                        f"  3. Pass parameter whose type matches the declared param type shown above.\n"
                        f"  4. ★ ABSOLUTE: If a method is NOT in the whitelist, you MUST NOT call it — period.\n"
                        f"     The whitelist is derived from the actual DaoImpl generated for this screen.\n"
                        f"     Calling a non-whitelisted method = immediate compilation failure.\n"
                        f"     If you need batch update/delete, look for updateXxx or deleteXxx in the whitelist.\n"
                        f"     If they are absent from the whitelist, use the closest available method\n"
                        f"     (e.g. call updateXxx in a for-loop for single-row updates, or skip if unsupported).\n"
                        f"     DO NOT invent a new DAO call under any circumstances.\n\n"
                        f"FORBIDDEN CALLS (will fail to compile):\n"
                        f"  {dao_var_name}.insert(...)     ← base class — forbidden\n"
                        f"  {dao_var_name}.select(...)     ← base class — forbidden\n"
                        f"  {dao_var_name}.update(...)     ← base class — forbidden\n"
                        f"  {dao_var_name}.delete(...)     ← base class — forbidden\n"
                        f"  {dao_var_name}.selectOne(...)  ← base class — forbidden\n"
                        f"  {dao_var_name}.selectList(...) ← base class — forbidden\n"
                        f"  ANY method NOT in the whitelist above ← forbidden\n\n"
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
                        "these are AbstractSqlSessionDaoSupport protected methods.\n"
                    )

                # Extract DTO fields and inject explicitly to prevent undefined getter/setter calls
                _dto_field_re = re.compile(r'private\s+\S+\s+(\w+)\s*;')
                dto_field_lines: list[str] = []
                for path, gf in ctx.generated_files.items():
                    if gf.file_type in ("dto_request", "dto_response"):
                        cls = gf.file_path.split("/")[-1].replace(".java", "")
                        fields = [m.group(1) for m in _dto_field_re.finditer(gf.content)]
                        if fields:
                            dto_field_lines.append(f"  {cls}: {', '.join(fields)}")
                        else:
                            # Empty DTO — class was generated with no fields.
                            # Still inject it so the LLM knows it must ADD fields before
                            # calling any getter/setter.  This is intentional: suppressing
                            # it (old behaviour) caused the LLM to freely invent accessors
                            # with no compile-time feedback.
                            dto_field_lines.append(
                                f"  {cls}: *** NO FIELDS DECLARED *** — "
                                f"you MUST add 'private <Type> fieldName;' to {cls} "
                                f"for EVERY getter/setter you call on it. "
                                f"Calling any getter/setter on an empty DTO = compile error."
                            )

                if dto_field_lines:
                    # Also build the list of available DTO class names
                    dto_class_names = [
                        gf2.file_path.split("/")[-1].replace(".java", "")
                        for gf2 in ctx.generated_files.values()
                        if gf2.file_type in ("dto_request", "dto_response")
                    ]
                    dto_class_list = ", ".join(sorted(dto_class_names))
                    user += (
                        f"\n╔══════════════════════════════════════════════════════════╗\n"
                        f"║  DTO CLASS WHITELIST — CRITICAL                          ║\n"
                        f"╚══════════════════════════════════════════════════════════╝\n"
                        f"AVAILABLE DTO CLASSES (ONLY these exist): {dto_class_list}\n\n"
                        f"ABSOLUTE RULES:\n"
                        f"  - DO NOT invent new DTO classes (e.g. CpmsXxxSaveReqDto, XxxUploadReqDto, XxxExcelRowReqDto)\n"
                        f"  - The save method MUST use List<ResDto> as parameter — NEVER a new ReqDto wrapper\n"
                        f"  - Import ONLY from the classes listed above — any other biz.*.dto.* import = compile error\n"
                        f"  - If spec needs ExcelUpload/batch insert, add the extra fields to the EXISTING ReqDto.\n"
                        f"    WRONG: import biz.edu.dto.request.CpmsEduExcelRowReqDto;  ← this class doesn't exist\n"
                        f"    CORRECT: add 'private List<String> excelRows;' to CpmsEduReqDto instead\n\n"
                        f"=== AVAILABLE DTO FIELDS — ONLY call getter/setter for these ===\n"
                        + "\n".join(dto_field_lines) + "\n\n"
                        "RULE: Before writing any dto.getXxx() or dto.setXxx() call,\n"
                        "      verify the field name appears in the list above for that DTO class.\n"
                        "      If you need a field NOT in the list (e.g. processedCount), you MUST:\n"
                        "        1) ADD 'private <Type> fieldName;' to the DTO class (shown in Dependencies)\n"
                        "        2) Then and only then call dto.getFieldName() / dto.setFieldName()\n"
                        "      NEVER call a getter/setter for a field not declared in the DTO — compile error!\n"
                        "=== END DTO FIELDS ===\n"
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

                # ── 3. Inline DAO whitelist check + auto-fix ─────────────────
                # Even with a detailed whitelist in the prompt, the LLM sometimes
                # still generates calls to non-existent DAO methods.  Catch them
                # immediately and request a targeted fix before storing the file.
                # Use the pre-built whitelist if available, otherwise fall back to
                # the one extracted inside the elif block.
                _eff_allowed = _pre_allowed_methods or _svc_allowed_methods
                _eff_dao_var = _pre_dao_var_name or _svc_dao_var_name
                if _eff_allowed and _eff_dao_var:
                    _dao_call_pat = re.compile(
                        rf'\b{re.escape(_eff_dao_var)}\.(\w+)\s*\('
                    )
                    violations = sorted({
                        m.group(1)
                        for m in _dao_call_pat.finditer(content)
                        if m.group(1) not in _eff_allowed
                    })
                    if violations:
                        logger.warning(
                            "[BACKEND_ENG] service_impl calls non-existent DAO methods %s — "
                            "running inline whitelist fix for %s",
                            violations, file_entry.file_path,
                        )
                        _fix_prompt = (
                            f"The ServiceImpl below calls these DAO methods that DO NOT EXIST "
                            f"in the DaoImpl: {violations}\n\n"
                            f"ALLOWED DAO method names (all that exist in DaoImpl): "
                            f"{sorted(_eff_allowed)}\n\n"
                            f"TASK — fix the ServiceImpl:\n"
                            f"  • Remove or replace EVERY call to the forbidden methods listed above.\n"
                            f"  • Substitute with the closest semantically matching ALLOWED method if one exists.\n"
                            f"  • If no equivalent exists, remove the block that uses the forbidden call.\n"
                            f"  • NEVER call any method not in the ALLOWED list.\n"
                            f"  • Preserve all other code exactly as-is.\n"
                            f"Output ONLY the complete corrected Java source (no markdown fences):\n\n"
                            f"{content}"
                        )
                        try:
                            fixed = await codex_client.complete(
                                system, _fix_prompt, stream=False,
                                max_tokens=settings.CODEGEN_MAX_TOKENS,
                            )
                            if fixed and isinstance(fixed, str):
                                content = _strip_fences(fixed)
                                logger.info(
                                    "[BACKEND_ENG] inline whitelist fix applied — removed forbidden calls %s",
                                    violations,
                                )
                        except Exception as _exc:
                            logger.warning(
                                "[BACKEND_ENG] inline whitelist fix call failed: %s", _exc
                            )

                # ── DTO field violation check for service_impl ────────────────
                # After the DAO whitelist fix, also verify that every getter/setter
                # call on a DTO object references a FIELD THAT ACTUALLY EXISTS.
                # Build the complete set of valid DTO fields from generated DTOs.
                if file_entry.file_type == "service_impl" and _dto_field_lines:
                    # Rebuild the set of valid fields from generated DTOs
                    _valid_dto_fields: set[str] = set()
                    for _path, _gf in ctx.generated_files.items():
                        if _gf.file_type in ("dto_request", "dto_response"):
                            for _fm in re.finditer(
                                r'private\s+\S+(?:<[^>]+>)?\s+(\w+)\s*;', _gf.content
                            ):
                                _valid_dto_fields.add(_fm.group(1))

                    # Detect invalid getters/setters (getXxx/setXxx where xxx not in valid fields)
                    _dto_violations: list[str] = []
                    for _gm in re.finditer(r'\b(?:get|set)([A-Z]\w*)\s*\(', content):
                        _field = _gm.group(1)[0].lower() + _gm.group(1)[1:]
                        if _field not in _valid_dto_fields:
                            _dto_violations.append(f"get/set{_gm.group(1)}")

                    if _dto_violations:
                        _unique_violations = sorted(set(_dto_violations))
                        logger.warning(
                            "[BACKEND_ENG] service_impl uses non-existent DTO fields %s — "
                            "running inline DTO field fix for %s",
                            _unique_violations, file_entry.file_path,
                        )
                        _valid_list = sorted(_valid_dto_fields)
                        _dto_fix_prompt = (
                            f"The ServiceImpl below calls getters/setters for DTO fields that DO NOT EXIST:\n"
                            f"  Invalid calls: {_unique_violations}\n\n"
                            f"VALID DTO fields (ONLY these exist — these are the ONLY fields you may use):\n"
                            f"  {_valid_list}\n\n"
                            f"TASK — fix the ServiceImpl:\n"
                            f"  • Remove or comment out every line that calls a getter/setter NOT in the valid list.\n"
                            f"  • If the logic requires a value from a non-existent field, use the closest\n"
                            f"    existing field from the valid list, or remove that logic block entirely.\n"
                            f"  • NEVER call getXxx()/setXxx() for a field not in the valid list.\n"
                            f"  • Preserve all other code exactly as-is.\n"
                            f"Output ONLY the complete corrected Java source (no markdown fences):\n\n"
                            f"{content}"
                        )
                        try:
                            fixed = await codex_client.complete(
                                system, _dto_fix_prompt, stream=False,
                                max_tokens=settings.CODEGEN_MAX_TOKENS,
                            )
                            if fixed and isinstance(fixed, str):
                                content = _strip_fences(fixed)
                                logger.info(
                                    "[BACKEND_ENG] DTO field fix applied — removed invalid getters/setters %s",
                                    _unique_violations,
                                )
                        except Exception as _exc:
                            logger.warning(
                                "[BACKEND_ENG] DTO field fix call failed: %s", _exc
                            )

            gf = GeneratedFile(
                file_path=file_entry.file_path,
                file_type=file_entry.file_type,
                content=content,
                layer="backend",
            )
            results.append(gf)
            ctx.generated_files[gf.file_path] = gf

            # ----------------------------------------------------------
            # CRITICAL: Post-process DaoImpl IMMEDIATELY after generation,
            # BEFORE service_impl is generated.
            # Without this, the ServiceImpl whitelist would see bare method
            # names (insert/select) instead of the real names (insertEduPgm/
            # selectEduPgmList), causing permanent mismatches.
            # ----------------------------------------------------------
            if file_entry.file_type == "dao_impl":
                gf.content = _fix_bare_dao_method_decls(gf.content)

                # ── Fix invalid parameter types — WHITELIST approach ──────────
                # Only these types are legal as DaoImpl method parameters:
                #   - Concrete DTO classes generated for this screen (ReqDto / ResDto)
                #   - Java primitives / common types: String, int, long, Integer, Long, boolean, Boolean
                # Everything else (dto, Dto, item, row, entity, Object, param-as-type, …)
                # is replaced with the correct DTO class deterministically.
                _known_res = _dao_res_classes[0] if _dao_res_classes else None
                _known_req = _dao_req_classes[0] if _dao_req_classes else None

                # FALLBACK: if ctx didn't have DTOs yet, extract from the DaoImpl's own imports.
                # This handles edge cases where _dao_res_classes/_dao_req_classes are empty.
                if not _known_res:
                    _im = re.search(r'import\s+[\w.]+\.(Cpms\w+ResDto)\s*;', gf.content)
                    if _im:
                        _known_res = _im.group(1)
                if not _known_req:
                    _im = re.search(r'import\s+[\w.]+\.(Cpms\w+ReqDto)\s*;', gf.content)
                    if _im:
                        _known_req = _im.group(1)

                if _known_res or _known_req:
                    # Build the full set of allowed single-token parameter types.
                    _allowed_param_types: set[str] = {
                        "String", "int", "long", "Integer", "Long",
                        "boolean", "Boolean", "double", "Double",
                    }
                    for _c in _dao_req_classes + _dao_res_classes:
                        _allowed_param_types.add(_c)
                    # Also allow any DTO class referenced in the DaoImpl's own imports
                    for _im in re.finditer(r'import\s+[\w.]+\.(Cpms\w+(?:Req|Res)Dto)\s*;', gf.content):
                        _allowed_param_types.add(_im.group(1))

                    def _fix_dao_param_type(match: re.Match) -> str:  # noqa: F811
                        full = match.group(0)
                        param_type = match.group(1)
                        if param_type in _allowed_param_types:
                            return full
                        mname_m = re.search(r'public\s+\S+\s+(\w+)\s*\(', full)
                        if mname_m:
                            mname = mname_m.group(1).lower()
                            _uses_res = any(k in mname for k in (
                                "duplicate", "count", "insert", "update", "delete",
                            ))
                            if _uses_res and _known_res:
                                replacement = _known_res
                            elif mname.startswith("select") and _known_req:
                                replacement = _known_req
                            else:
                                replacement = _known_res or _known_req
                        else:
                            replacement = _known_res or _known_req
                        fixed = full.replace(f"({param_type} ", f"({replacement} ", 1)
                        logger.warning(
                            "[BACKEND_ENG] Fixed invalid DAO param type '%s' → '%s' in %s",
                            param_type, replacement, gf.file_path,
                        )
                        return fixed

                    # Match: public <ReturnType> <methodName>(<SingleType> <varName>)
                    # Only single-token (non-generic) parameter types — List<X> is fine as-is
                    _bad_param_re = re.compile(
                        r'(public\s+\S+\s+\w+\s*\(\s*)([A-Za-z][A-Za-z0-9]*)(\s+\w+\s*\))',
                    )

                    def _apply_fix(m: re.Match) -> str:
                        prefix, param_type, suffix = m.group(1), m.group(2), m.group(3)
                        if param_type in _allowed_param_types:
                            return m.group(0)
                        # Determine best replacement
                        mname_m = re.search(r'public\s+\S+\s+(\w+)\s*\(', prefix)
                        if mname_m:
                            mname = mname_m.group(1).lower()
                            _uses_res = any(k in mname for k in (
                                "duplicate", "count", "insert", "update", "delete",
                            ))
                            if _uses_res and _known_res:
                                replacement = _known_res
                            elif mname.startswith("select") and _known_req:
                                replacement = _known_req
                            else:
                                replacement = _known_res or _known_req
                        else:
                            replacement = _known_res or _known_req
                        # ALWAYS replace — even if replacement is None fallback to ResDto
                        if not replacement:
                            replacement = _known_res or _known_req or "Object"
                        if replacement != param_type:
                            logger.warning(
                                "[BACKEND_ENG] Fixed invalid DAO param type '%s' → '%s' in %s",
                                param_type, replacement, gf.file_path,
                            )
                            return f"{prefix}{replacement}{suffix}"
                        return m.group(0)

                    gf.content = _bad_param_re.sub(_apply_fix, gf.content)

                ctx.generated_files[gf.file_path] = gf
                logger.info(
                    "[BACKEND_ENG] DaoImpl post-processed BEFORE service_impl generation: %s",
                    gf.file_path,
                )

        # Apply remaining programmatic post-processing on all files.
        # DaoImpl bare decls are already fixed above, but this catches
        # ServiceImpl bare calls, @Slf4j, log.debug, UUID removal, etc.
        try:
            postprocess_backend_files(results)
        except Exception as e:
            logger.exception("[BACKEND_ENG] postprocess_backend_files FAILED — this is critical: %s", e)
        # Sync post-processed content back into ctx.generated_files
        for gf in results:
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
            "- NEVER use CommonUtils.getUuid() — ID values come from DB sequence, not generated in code\n"
            "- ServiceImpl MUST ONLY use DTO fields and DAO methods that actually exist — no invented methods or fields\n"
            "- ServiceImpl = DTO + DAO ONLY: no new wrapper DTOs, no helper methods bypassing DAO, no extra arguments\n"
            "- Mapper XML: all parameter properties must have matching javaType if not String (avoid jdbcType=null errors)\n"
            "- DTO FIELD TYPE WHITELIST — flag any DTO field that is NOT one of the allowed types:\n"
            "    ALLOWED: String, int, Integer, long, Long, BigDecimal, boolean, Boolean\n"
            "    FORBIDDEN: Date, LocalDate, LocalDateTime, List<...>, Map<...>, Object, any class/enum\n"
            "    e.g. 'private List<String> codeList;' in a DTO is a BUG — use 'private String codeList;' (comma-separated)\n"
            "    e.g. 'private Date eduDate;' in a DTO is a BUG — use 'private String eduDate;'\n"
            "- TYPE CHAIN CONSISTENCY: if DTO field is String, ALL usages (getter calls, method args) must treat it as String.\n"
            "    Flag any cast or conversion that indicates a type mismatch between DTO declaration and usage.\n\n"
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
                "- NEVER call log.error()/log.warn() immediately before throw HscException.\n\n"
                "EXCEPTION HANDLING RULES:\n"
                "- throw HscException.systemError() MUST ALWAYS be inside a try-catch block.\n"
                "- The second argument MUST be the caught Exception variable (e).\n"
                "- WRONG: throw HscException.systemError(\"msg\");  ← no exception arg = compile error at runtime\n"
                "- WRONG: if (x == null) throw HscException.systemError(\"msg\");  ← outside try-catch = forbidden\n"
                "- CORRECT: try { ... } catch (Exception e) { throw HscException.systemError(\"msg\", e); }\n"
                "- If the original code has bare validation throws (without try-catch), wrap the method body in try-catch.\n\n"
                "POM.XML COMPLIANCE RULES:\n"
                "- ONLY import from libraries declared in pom.xml. Any other import = compilation failure.\n"
                "- NEVER import org.apache.poi.* — Apache POI is NOT in pom.xml.\n"
                "  If fixing an Excel-related method: remove all POI code, change the method to return List<ResDto>\n"
                "  (same as the search method), and remove the Excel-specific DTO fields (fileName, fileContent, rowCount).\n"
                "  The frontend handles Excel export via PrimeVue DataTable — the backend only provides the data.\n\n"
                "DTO FIELD CONSISTENCY RULES:\n"
                "- NEVER call getter/setter for a field that is not declared in the DTO class.\n"
                "- If a fix says to add a field to a DTO: add 'private <Type> fieldName;' inside the DTO class body.\n"
                "- When fixing a DTO issue, output the UPDATED DTO file (not the ServiceImpl) with the new field added.\n"
                "- NEVER just remove the getter/setter call — always ADD the missing field to the DTO instead.\n"
                "DTO FIELD TYPE WHITELIST — when adding or fixing DTO fields, ONLY these types are allowed:\n"
                "  ALLOWED: String, int, Integer, long, Long, BigDecimal, boolean, Boolean\n"
                "  FORBIDDEN: Date, LocalDate, LocalDateTime → use String instead\n"
                "  FORBIDDEN: List<...>, Map<...>, Object, any complex type → use String (comma-separated) instead\n"
                "  NEVER introduce a List or Date typed field into a DTO, even if the issue says to add it.\n"
                "  If the issue involves a date field, declare it as 'private String fieldName;'.\n"
                "  If the issue involves a list/collection field, declare it as 'private String fieldName;' (comma-separated).\n"
                "TYPE CHAIN: once a DTO field is declared as String, ALL code that calls its getter must treat it as String.\n"
                "  If ServiceImpl does 'String x = dto.getEduDate()' → that is correct (String→String).\n"
                "  If ServiceImpl does 'Date x = dto.getEduDate()' → WRONG, must be 'String x = dto.getEduDate()'.\n\n"
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
                f"=== ALL BACKEND FILES (cross-reference for compile consistency) ===\n"
                f"{all_backend_context}\n"
                f"=== END ALL BACKEND FILES ===\n\n"
                f"IMPORTANT: Before outputting the fixed file, mentally verify ALL of the following:\n"
                f"  1. Every DAO method called in ServiceImpl exists in the DaoImpl file above\n"
                f"  2. Every DTO getter/setter called in ServiceImpl has a matching field in the DTO file above\n"
                f"  3. No CommonUtils.getUuid() or UUID.randomUUID() anywhere\n"
                f"  4. No invented methods or fields that don't exist in DTO/DAO\n"
                f"  5. COMPILE CHECK — Every import must be from a library in pom.xml (no org.apache.poi.*, etc.)\n"
                f"  6. COMPILE CHECK — Every HscException.systemError() call has TWO args: (\"msg\", e)\n"
                f"     and is inside a catch block. Single-arg calls like systemError(\"msg\") are compile errors.\n"
                f"  7. COMPILE CHECK — Every class, method, and field referenced in the file actually exists.\n"
                f"     No phantom classes, no missing imports, no undefined variables.\n\n"
                f"Output the complete fixed file."
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
