"""Backend code generators (DAO deterministic; DTO/Mapper/Service via gpt-5.5 — later tasks).

Consumes the Phase-2 Contract + bindings. DAO is a pure template (BackendGuide
§4.4.3) — no LLM.
"""

from __future__ import annotations

import json

from app.llm.graph import naming
from app.llm.graph.llm import gpt55_client
from app.llm.graph.prompts import GENERATOR_SYSTEM
from app.llm.graph._text import strip_fences as _strip_fences

# op -> (super method, return type template, param type template)
_DAO_OP = {
    "selectList": ("selectList", "java.util.List<{Res}>", "{Req} param"),
    "count":      ("selectOne", "int", "{Req} param"),
    "selectOne":  ("selectOne", "{Res}", "{Req} param"),
    "insert":     ("insert", "int", "{Req} param"),
    "update":     ("batchUpdateReturnSumAffectedRows", "int", "java.util.List<{Req}> param"),
    "delete":     ("batchUpdateReturnSumAffectedRows", "int", "java.util.List<{Req}> param"),
}


def render_dao(contract: dict) -> str:
    """Deterministic DaoImpl source from the contract + bindings (§4.4.3)."""
    ident = contract["identity"]
    screen = ident["class_name"]
    b = contract["bindings"]
    pkgs = b["packages"]
    dao_pkg = pkgs.get("dao_impl", f"biz.{ident['module']}.dao")
    req_pkg = pkgs.get("dto_request", f"biz.{ident['module']}.dto.request")
    res_pkg = pkgs.get("dto_response", f"biz.{ident['module']}.dto.response")
    req, res = f"{screen}ReqDto", f"{screen}ResDto"

    methods = []
    for op in (contract.get("ops") or naming.ops_for_screen_type(contract.get("archetype", "list"))):
        spec = _DAO_OP.get(op)
        if not spec:
            continue
        super_m, ret_t, param_t = spec
        sid = naming.statement_id(op, screen)
        ret = ret_t.replace("{Res}", res).replace("{Req}", req)
        param = param_t.replace("{Res}", res).replace("{Req}", req)
        methods.append(
            f"    public {ret} {sid}({param}) {{\n"
            f'        return super.{super_m}("{sid}", param);\n'
            f"    }}")

    return (
        f"package {dao_pkg};\n\n"
        f"import org.springframework.stereotype.Repository;\n"
        f"import aondev.framework.dao.mybatis.support.AbstractSqlSessionDaoSupport;\n"
        f"import {req_pkg}.{req};\n"
        f"import {res_pkg}.{res};\n\n"
        f"@Repository\n"
        f"public class {screen}DaoImpl extends AbstractSqlSessionDaoSupport {{\n\n"
        + "\n\n".join(methods)
        + "\n}\n"
    )


# ---------------------------------------------------------------------------
# LLM generators (Phase 4 Task 2)
# ---------------------------------------------------------------------------

async def gen_dtos(contract: dict, guide: str) -> dict:
    """Generate ReqDto and ResDto via gpt-5.5. Returns {path: content} for both."""
    ident = contract["identity"]
    screen = ident["class_name"]
    b = contract["bindings"]
    pkgs = b["packages"]
    paths = b["paths"]
    fields = contract["fields"]

    results: dict = {}

    # --- ReqDto ---
    req_pkg = pkgs["dto_request"]
    req_class = f"{screen}ReqDto"
    req_fields_json = json.dumps(fields["request"], ensure_ascii=False)
    req_user = (
        f"=== GUIDE ===\n{guide}\n\n"
        f"=== TASK ===\n"
        f"Generate a flat Java Request DTO file.\n"
        f"Package: {req_pkg}\n"
        f"Class: {req_class}\n"
        f"Extend: SearchBaseDto\n"
        f"Fields (camelCase, javaType):\n{req_fields_json}\n\n"
        f"Rules:\n"
        f"- Flat DTO only (no nested/inner classes)\n"
        f"- All date/ID fields as String\n"
        f"- Use exact field names from the fields list above\n"
        f"- Add Lombok @Data and @EqualsAndHashCode(callSuper=false)\n"
        f"Output ONLY the Java file content."
    )
    req_reply = await gpt55_client.complete(GENERATOR_SYSTEM, req_user)
    results[paths["dto_request"]] = _strip_fences(req_reply)

    # --- ResDto ---
    res_pkg = pkgs["dto_response"]
    res_class = f"{screen}ResDto"
    res_fields_json = json.dumps(fields["response"], ensure_ascii=False)
    res_user = (
        f"=== GUIDE ===\n{guide}\n\n"
        f"=== TASK ===\n"
        f"Generate a flat Java Response DTO file.\n"
        f"Package: {res_pkg}\n"
        f"Class: {res_class}\n"
        f"Extend: AuditBaseDto\n"
        f"Fields (camelCase, javaType):\n{res_fields_json}\n\n"
        f"Rules:\n"
        f"- Flat DTO only (no nested/inner classes)\n"
        f"- All date/ID fields as String\n"
        f"- Use exact field names from the fields list above\n"
        f"- Add Lombok @Data and @EqualsAndHashCode(callSuper=false)\n"
        f"Output ONLY the Java file content."
    )
    res_reply = await gpt55_client.complete(GENERATOR_SYSTEM, res_user)
    results[paths["dto_response"]] = _strip_fences(res_reply)

    return results


async def gen_mapper(contract: dict, guide: str, dtos: dict) -> dict:
    """Generate MyBatis Mapper XML via gpt-5.5. Returns {path: content}."""
    ident = contract["identity"]
    b = contract["bindings"]
    paths = b["paths"]

    namespace = b["namespace"]
    statement_ids = b["statement_ids"]
    table = contract["table"]
    columns = table["columns"]
    fields = contract["fields"]

    # Gather dep DTO source content
    dep_sources = "\n\n".join(dtos.values())

    # Build column details: include snake names so "emp_nm" is explicitly present
    columns_detail = "\n".join(
        f"  - {col['snake']} ({col.get('db_type', '')}) -> {col.get('camel', '')} [{col.get('java_type', '')}]"
        for col in columns
    )
    stmt_ids_str = "\n".join(f"  - {sid}" for sid in statement_ids)
    req_fields_json = json.dumps(fields["request"], ensure_ascii=False)
    res_fields_json = json.dumps(fields["response"], ensure_ascii=False)

    user = (
        f"=== GUIDE ===\n{guide}\n\n"
        f"=== TASK ===\n"
        f"Generate a MyBatis Mapper XML file.\n\n"
        f"REQUIRED IDENTIFIERS (use exactly as-is):\n"
        f"namespace: {namespace}\n"
        f"statement ids:\n{stmt_ids_str}\n\n"
        f"TABLE: {table['name']}\n"
        f"COLUMNS (snake_case -> camelCase):\n{columns_detail}\n\n"
        f"REQUEST FIELDS:\n{req_fields_json}\n\n"
        f"RESPONSE FIELDS:\n{res_fields_json}\n\n"
        f"=== DEPENDENCY DTOs ===\n{dep_sources}\n\n"
        f"Rules:\n"
        f"- Use CDATA for < and > in SQL conditions\n"
        f"- Use <if test='...'> for optional params\n"
        f"- Match every statement_id above exactly\n"
        f"Output ONLY the XML file content."
    )
    reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    return {paths["mapper_xml"]: _strip_fences(reply)}


async def gen_service(contract: dict, guide: str, dao: str, dtos: dict) -> dict:
    """Generate ServiceImpl via gpt-5.5. Returns {path: content}."""
    ident = contract["identity"]
    screen = ident["class_name"]
    b = contract["bindings"]
    pkgs = b["packages"]
    paths = b["paths"]

    svc_pkg = pkgs["service_impl"]
    statement_ids = b["statement_ids"]

    # Gather dep DTO source content
    dep_sources = "\n\n".join(dtos.values())

    stmt_ids_str = "\n".join(f"  - {sid}" for sid in statement_ids)

    user = (
        f"=== GUIDE ===\n{guide}\n\n"
        f"=== TASK ===\n"
        f"Generate a Spring Service implementation Java file.\n"
        f"Package: {svc_pkg}\n"
        f"Class: {screen}ServiceImpl\n\n"
        f"REQUIRED IDENTIFIERS:\n"
        f"DAO statement/method names:\n{stmt_ids_str}\n\n"
        f"@ServiceId pattern: \"{screen}/<method>\" (e.g. {screen}/selectList)\n"
        f"@ServiceName: use a descriptive Korean label per method\n\n"
        f"=== DAO SOURCE (use these exact method names) ===\n{dao}\n\n"
        f"=== DEPENDENCY DTOs ===\n{dep_sources}\n\n"
        f"Rules:\n"
        f"- Every public method must have @ServiceId(\"{screen}/<method>\") and @ServiceName(\"...\") annotations\n"
        f"- Inject the DaoImpl via constructor injection\n"
        f"- Delegate each service method to the corresponding DAO method above\n"
        f"Output ONLY the Java file content."
    )
    reply = await gpt55_client.complete(GENERATOR_SYSTEM, user)
    return {paths["service_impl"]: _strip_fences(reply)}
