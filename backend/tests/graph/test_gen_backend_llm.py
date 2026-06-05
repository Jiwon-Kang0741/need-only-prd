import pytest
from app.llm.graph import gen_backend as gb

pytestmark = pytest.mark.asyncio

_CONTRACT = {
    "identity": {"module": "edu", "category": "pondg",
                 "screen_id": "cpmsEduPondgLst", "class_name": "CpmsEduPondgLst",
                 "program_id": "CPMSEDUPONDGLST"},
    "archetype": "list-detail",
    "ops": ["selectList", "count", "selectOne", "insert", "update", "delete"],
    "table": {"name": "cptb_edu_pondg", "pk": ["pondg_id"],
              "columns": [{"snake": "emp_nm", "camel": "empNm", "db_type": "varchar(100)",
                           "java_type": "String", "searchable": True}]},
    "fields": {"request": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String",
                            "filter": "ILIKE"}],
               "response": [{"camel": "empNm", "snake": "emp_nm", "java_type": "String"}]},
    "bindings": {
        "statement_ids": ["selectCpmsEduPondgLstList", "selectCpmsEduPondgLstCount",
                          "selectCpmsEduPondgLst", "insertCpmsEduPondgLst",
                          "updateCpmsEduPondgLst", "deleteCpmsEduPondgLst"],
        "namespace": "biz.edu.dao.CpmsEduPondgLstDaoImpl",
        "packages": {"dao_impl": "biz.edu.dao", "dto_request": "biz.edu.dto.request",
                     "dto_response": "biz.edu.dto.response", "service_impl": "biz.edu.service"},
        "paths": {"dto_request": "src/main/java/biz/edu/dto/request/CpmsEduPondgLstReqDto.java",
                  "dto_response": "src/main/java/biz/edu/dto/response/CpmsEduPondgLstResDto.java",
                  "mapper_xml": "src/main/resources/biz/edu/mybatis/mappers/CpmsEduPondgLstMapper.xml",
                  "service_impl": "src/main/java/biz/edu/service/CpmsEduPondgLstServiceImpl.java"},
    },
}


class _Scripted:
    def __init__(self, reply):
        self.reply = reply
        self.last_user = None
        self.calls = 0
    async def complete(self, system, user, max_tokens=16384):
        self.calls += 1
        self.last_user = user
        return self.reply


async def test_gen_dtos_returns_two_files_fence_stripped(monkeypatch):
    c = _Scripted("```java\npackage x;\nclass X {}\n```")
    monkeypatch.setattr(gb, "gpt55_client", c)
    out = await gb.gen_dtos(_CONTRACT, guide="GUIDE")
    assert _CONTRACT["bindings"]["paths"]["dto_request"] in out
    assert _CONTRACT["bindings"]["paths"]["dto_response"] in out
    assert all("```" not in v for v in out.values())
    assert c.calls == 2          # one per DTO


async def test_gen_mapper_grounds_in_bindings_columns_and_deps(monkeypatch):
    c = _Scripted("<mapper namespace=\"biz.edu.dao.CpmsEduPondgLstDaoImpl\"></mapper>")
    monkeypatch.setattr(gb, "gpt55_client", c)
    out = await gb.gen_mapper(_CONTRACT, guide="GUIDE", dtos={"req.java": "class ReqDto{}"})
    assert _CONTRACT["bindings"]["paths"]["mapper_xml"] in out
    u = c.last_user
    assert "biz.edu.dao.CpmsEduPondgLstDaoImpl" in u   # namespace
    assert "selectCpmsEduPondgLstList" in u            # statement id
    assert "emp_nm" in u                               # real DB column
    assert "GUIDE" in u                                # guide injected
    assert "class ReqDto" in u                         # dep DTO content


async def test_gen_service_grounds_in_dao_methods(monkeypatch):
    c = _Scripted("class S {}")
    monkeypatch.setattr(gb, "gpt55_client", c)
    dao_src = "class CpmsEduPondgLstDaoImpl { public int insertCpmsEduPondgLst(){} }"
    out = await gb.gen_service(_CONTRACT, guide="GUIDE", dao=dao_src, dtos={"r": "class ReqDto{}"})
    assert _CONTRACT["bindings"]["paths"]["service_impl"] in out
    u = c.last_user
    assert "insertCpmsEduPondgLst" in u                # must call real dao methods
    assert "CpmsEduPondgLst/" in u                     # ServiceId hint {class}/{method}
    assert "GUIDE" in u


async def test_gen_service_prompt_calls_out_transactional_and_trycatch(monkeypatch):
    c = _Scripted("class S {}")
    monkeypatch.setattr(gb, "gpt55_client", c)
    await gb.gen_service(_CONTRACT, guide="GUIDE",
                         dao="class D { public int insertCpmsEduPondgLst(){} }", dtos={})
    u = c.last_user
    assert "@Transactional" in u
    assert "try" in u and "HscException.systemError" in u
