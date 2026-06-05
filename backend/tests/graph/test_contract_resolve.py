import json
import pytest

from app.llm.graph import contract_resolve as cr

pytestmark = pytest.mark.asyncio

_VALID = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list",
    "ops": ["selectList", "count"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm",
                           "db_type": "varchar(100)", "java_type": "String"}]},
    "frontend": {"components": ["SearchForm", "DataTable"]},
}


class _Scripted:
    """Fake gpt55_client returning queued replies; records calls."""
    def __init__(self, *replies):
        self._replies = list(replies)
        self.calls = []
    async def complete(self, system, user, max_tokens=16384):
        self.calls.append((system, user))
        return self._replies.pop(0)


def _state(page_type="list"):
    return {"spec_markdown": "spec", "confirmed_vue": "<template/>",
            "table_info": "cptb_edu_pondg cols...", "page_type": page_type}


async def test_contract_resolve_returns_validated_contract(monkeypatch):
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(_VALID)))
    out = await cr.contract_resolve(_state())
    c = out["contract"]
    assert c["identity"]["module"] == "edu"        # O1
    assert c["identity"]["category"] == "pondg"    # O1
    assert c["archetype"] == "list"
    assert c["table"]["name"] == "cptb_edu_pondg"


async def test_contract_resolve_retries_once_on_bad_json(monkeypatch):
    client = _Scripted("not json {", json.dumps(_VALID))
    monkeypatch.setattr(cr, "gpt55_client", client)
    out = await cr.contract_resolve(_state())
    assert out["contract"]["identity"]["class_name"] == "CpmsEduPondgLst"
    assert len(client.calls) == 2


async def test_contract_resolve_retries_once_on_schema_violation(monkeypatch):
    bad = {**_VALID, "identity": {k: v for k, v in _VALID["identity"].items() if k != "module"}}
    client = _Scripted(json.dumps(bad), json.dumps(_VALID))
    monkeypatch.setattr(cr, "gpt55_client", client)
    out = await cr.contract_resolve(_state())
    assert out["contract"]["identity"]["module"] == "edu"
    assert len(client.calls) == 2


async def test_contract_resolve_raises_after_two_failures(monkeypatch):
    monkeypatch.setattr(cr, "gpt55_client", _Scripted("nope", "still nope"))
    with pytest.raises(ValueError):
        await cr.contract_resolve(_state())


async def test_contract_resolve_emits_contract_event(monkeypatch):
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(_VALID)))
    out = await cr.contract_resolve(_state())
    assert any(e.get("type") == "contract" for e in out["events"])


async def test_contract_resolve_page_type_overrides_archetype(monkeypatch):
    # confirmed mockup page_type wins over the model's archetype guess (when it is a
    # valid archetype). LLM said "list" but the confirmed page is "list-detail".
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(_VALID)))
    out = await cr.contract_resolve(_state(page_type="list-detail"))
    assert out["contract"]["archetype"] == "list-detail"


async def test_contract_resolve_ignores_invalid_page_type(monkeypatch):
    # an unrecognized page_type must NOT be injected (would corrupt the validated
    # archetype); keep the LLM's validated value instead.
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(_VALID)))
    out = await cr.contract_resolve(_state(page_type="bogus"))
    assert out["contract"]["archetype"] == "list"


async def test_contract_resolve_raises_on_refusal(monkeypatch):
    # A refusal / non-JSON reply is not silently accepted — both attempts fail -> raise.
    client = _Scripted("I'm sorry, I can't help with that.", "Still refusing.")
    monkeypatch.setattr(cr, "gpt55_client", client)
    with pytest.raises(ValueError, match="contract_resolve"):
        await cr.contract_resolve(_state())
    assert len(client.calls) == 2


async def test_contract_resolve_build_user_coalesces_none(monkeypatch):
    # a None-valued state field must not become the literal string "None" in the prompt
    captured = {}

    class _Capture:
        async def complete(self, system, user, max_tokens=16384):
            captured["user"] = user
            import json as _j
            return _j.dumps(_VALID)

    monkeypatch.setattr(cr, "gpt55_client", _Capture())
    await cr.contract_resolve({"spec_markdown": None, "confirmed_vue": None,
                               "table_info": None, "page_type": None})
    assert "None" not in captured["user"]


async def test_contract_resolve_tolerates_null_optional_fields(monkeypatch):
    # Real gpt-5.5 emits null for optional fields; the resolver drops nulls so
    # pydantic uses defaults instead of raising string_type/dict_type errors.
    contract = json.loads(json.dumps(_VALID))
    contract["identity"]["menu_id"] = None              # optional str -> null
    contract["seed"] = {"menu": None, "labels": None, "pgm_url": None}  # dict/list/str nulls
    contract["api"] = None                              # optional list -> null
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(contract)))
    out = await cr.contract_resolve(_state())
    c = out["contract"]
    assert c["identity"]["menu_id"] == ""               # default applied
    assert c["seed"]["menu"] == {} and c["seed"]["labels"] == []
    assert c["api"] == []


async def test_contract_resolve_null_required_field_still_fails(monkeypatch):
    # a REQUIRED field set to null is dropped -> 'field required' -> retry -> raise
    bad = json.loads(json.dumps(_VALID)); bad["identity"]["module"] = None
    monkeypatch.setattr(cr, "gpt55_client", _Scripted(json.dumps(bad), json.dumps(bad)))
    with pytest.raises(ValueError):
        await cr.contract_resolve(_state())


async def test_resolver_prompt_mandates_field_shapes():
    # Approach A: the PROMPT (not post-coercion) is the source of the contract shapes.
    p = cr.CONTRACT_RESOLVER_SYSTEM
    assert "NEVER a boolean" in p                       # table.columns[].code
    assert "field-NAME STRINGS" in p                    # frontend.search_fields
    assert "DataTable\n  columns" in p or "DataTable" in p  # frontend.columns rule present
    assert "ensureLoadedMulti" in p                     # frontend.common_code_load choices
