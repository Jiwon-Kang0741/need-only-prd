"""Backend code generators (DAO deterministic; DTO/Mapper/Service via gpt-5.5 — later tasks).

Consumes the Phase-2 Contract + bindings. DAO is a pure template (BackendGuide
§4.4.3) — no LLM.
"""

from __future__ import annotations

from app.llm.graph import naming

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
