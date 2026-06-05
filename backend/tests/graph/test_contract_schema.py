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
