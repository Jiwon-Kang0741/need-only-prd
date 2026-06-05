import pytest
from pydantic import ValidationError

from app.llm.graph.contract_schema import Contract, Identity, parse_contract

_MIN = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list",
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm",
                           "db_type": "varchar(100)", "java_type": "String"}]},
}


def test_parse_contract_minimal_ok():
    c = parse_contract(_MIN)
    assert isinstance(c, Contract)
    assert c.identity.module == "edu"
    assert c.identity.category == "pondg"
    assert c.archetype == "list"
    assert c.api == [] and c.frontend.components == [] and c.bindings.paths == {}


def test_parse_contract_missing_identity_module_raises():
    bad = {**_MIN, "identity": {**_MIN["identity"]}}
    del bad["identity"]["module"]
    with pytest.raises(ValidationError):
        parse_contract(bad)


def test_parse_contract_missing_category_raises():
    bad = {**_MIN, "identity": {**_MIN["identity"]}}
    del bad["identity"]["category"]
    with pytest.raises(ValidationError):
        parse_contract(bad)


def test_parse_contract_rejects_non_dict():
    with pytest.raises(ValidationError):
        parse_contract("not a dict")


def test_contract_round_trips_to_dict():
    c = parse_contract(_MIN)
    d = c.model_dump()
    assert d["identity"]["screen_id"] == "cpmsEduPondgLst"
    assert parse_contract(d).identity.class_name == "CpmsEduPondgLst"


def test_parse_contract_rejects_unknown_archetype():
    bad = {**_MIN, "archetype": "crud"}          # not in the Literal set
    with pytest.raises(ValidationError):
        parse_contract(bad)


def test_parse_contract_accepts_popup_archetype():
    ok = {**_MIN, "archetype": "popup"}
    assert parse_contract(ok).archetype == "popup"


def test_parse_contract_rejects_unknown_req_filter():
    bad = {**_MIN, "fields": {"request": [
        {"camel": "empNm", "snake": "emp_nm", "filter": "between"}]}}
    with pytest.raises(ValidationError):
        parse_contract(bad)


def test_parse_contract_accepts_valid_req_filter():
    ok = {**_MIN, "fields": {"request": [
        {"camel": "empNm", "snake": "emp_nm", "filter": "ILIKE"}]}}
    assert parse_contract(ok).fields.request[0].filter == "ILIKE"


def test_column_code_bool_coerced_to_none():
    # gpt-5.5 returns Column.code as a bool ("is coded?"); schema coerces -> None
    c = {**_MIN, "table": {"name": "cptb_x", "pk": ["id"], "columns": [
        {"snake": "a", "camel": "a", "code": False},
        {"snake": "b", "camel": "b", "code": True}]}}
    cols = parse_contract(c).table.columns
    assert cols[0].code is None and cols[1].code is None


def test_column_code_string_preserved():
    c = {**_MIN, "table": {"name": "cptb_x", "pk": ["id"], "columns": [
        {"snake": "a", "camel": "a", "code": "riskClsfCd"}]}}
    assert parse_contract(c).table.columns[0].code == "riskClsfCd"


def test_frontend_search_fields_accepts_dicts_and_strings():
    c = {**_MIN, "frontend": {"search_fields": [
        {"camel": "riskNm", "snake": "risk_nm", "filter": "ILIKE"}, "plainName"]}}
    sf = parse_contract(c).frontend.search_fields
    assert len(sf) == 2 and isinstance(sf[0], dict) and sf[1] == "plainName"


def test_frontend_common_code_load_accepts_list_or_str():
    c = {**_MIN, "frontend": {"common_code_load": ["riskClsfCd", "riskStsCd"]}}
    assert parse_contract(c).frontend.common_code_load == ["riskClsfCd", "riskStsCd"]
    c2 = {**_MIN, "frontend": {"common_code_load": "ensureLoaded"}}
    assert parse_contract(c2).frontend.common_code_load == "ensureLoaded"
