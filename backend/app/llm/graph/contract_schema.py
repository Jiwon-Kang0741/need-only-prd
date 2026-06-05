"""The Contract — the single shared artifact every generator consumes.

Defined as pydantic models so the LLM resolver output is validated at one
boundary (parse_contract). `bindings` is filled deterministically later
(plan_and_bind), so it defaults empty here. Mirrors the design spec §3.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Identity(BaseModel):
    module: str                 # LV1, e.g. "edu"  (REQUIRED — decision O1)
    category: str               # LV2, e.g. "pondg" (REQUIRED — decision O1)
    screen_id: str              # camelCase, e.g. "cpmsEduPondgLst"
    class_name: str             # PascalCase, e.g. "CpmsEduPondgLst"
    program_id: str             # SPEC #1 verbatim (seed lbl_cd prefix SSOT)
    window_id: str = ""
    menu_id: str = ""
    p_menu_id: str = ""


class Column(BaseModel):
    snake: str
    camel: str
    db_type: str = ""
    java_type: str = ""
    pk: bool = False
    nullable: bool = True
    searchable: bool = False
    audit: bool = False
    code: str | None = None     # cls_id when common-coded (then *_nm is JOIN-resolved)


class Table(BaseModel):
    name: str
    pk: list[str] = []
    columns: list[Column] = []


class ReqField(BaseModel):
    camel: str
    snake: str
    java_type: str = "String"
    optional: bool = True
    filter: Literal["ILIKE", "eq", "range", ""] = ""


class ResField(BaseModel):
    camel: str
    snake: str
    java_type: str = "String"
    is_status: bool = False


class Fields(BaseModel):
    request: list[ReqField] = []
    response: list[ResField] = []


class ApiSig(BaseModel):
    method: str
    service_id: str = ""
    url: str = ""
    req_dto: str = ""
    res_dto: str = ""
    authority: str = ""


class FrontendPlan(BaseModel):
    components: list[str] = []
    search_fields: list[str] = []
    columns: list[dict] = []
    common_code_load: str = ""


class SeedMeta(BaseModel):
    labels: list[dict] = []
    menu: dict = {}
    common_codes: list[dict] = []
    pgm_url: str = ""


class Bindings(BaseModel):
    statement_ids: list[str] = []
    dao_methods: list[str] = []
    namespace: str = ""
    packages: dict[str, str] = {}
    audit_map: dict[str, str] = {}      # populated in Phase 4 (Mapper gen)
    paths: dict[str, str] = {}
    files: list[dict] = []


class Contract(BaseModel):
    identity: Identity
    archetype: Literal["list", "list-detail", "edit", "popup", "tab-detail"]
    ops: list[str] = []
    table: Table
    fields: Fields = Fields()
    api: list[ApiSig] = []
    frontend: FrontendPlan = FrontendPlan()
    seed: SeedMeta = SeedMeta()
    bindings: Bindings = Bindings()


def parse_contract(data: object) -> Contract:
    """Validate raw (LLM-parsed) data into a Contract. Raises pydantic ValidationError."""
    return Contract.model_validate(data)
