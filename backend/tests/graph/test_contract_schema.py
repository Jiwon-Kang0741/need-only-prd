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
