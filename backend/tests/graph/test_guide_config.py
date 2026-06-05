from app.llm.graph import guide_config as gc

_BACKEND_114 = """\
### 11.4 파일 경로 규칙 (코드 생성 시)

| 파일 유형 | 경로 패턴 |
|-----------|-----------|
| DB Init SQL | `db/init.sql` |
| DTO Request | `src/main/java/biz/{module}/dto/request/{ClassName}ReqDto.java` |
| DTO Response | `src/main/java/biz/{module}/dto/response/{ClassName}ResDto.java` |
| DAO Impl | `src/main/java/biz/{module}/dao/{ClassName}DaoImpl.java` |
| Service Impl | `src/main/java/biz/{module}/service/{ClassName}ServiceImpl.java` |
| Mapper XML | `src/main/resources/biz/{module}/mybatis/mappers/{ClassName}Mapper.xml` |

### 11.5 다음 섹션
"""


def test_parse_backend_path_templates_normalizes_labels():
    out = gc._parse_backend_path_templates(_BACKEND_114)
    assert out["db_init_sql"] == "db/init.sql"
    assert out["dto_request"] == "src/main/java/biz/{module}/dto/request/{ClassName}ReqDto.java"
    assert out["dto_response"] == "src/main/java/biz/{module}/dto/response/{ClassName}ResDto.java"
    assert out["dao_impl"] == "src/main/java/biz/{module}/dao/{ClassName}DaoImpl.java"
    assert out["service_impl"] == "src/main/java/biz/{module}/service/{ClassName}ServiceImpl.java"
    assert out["mapper_xml"] == "src/main/resources/biz/{module}/mybatis/mappers/{ClassName}Mapper.xml"


def test_parse_backend_path_templates_drops_header_and_separator():
    out = gc._parse_backend_path_templates(_BACKEND_114)
    assert "파일_유형" not in out
    assert len(out) == 6


def test_parse_backend_path_templates_empty_when_section_absent():
    assert gc._parse_backend_path_templates("# no 11.4 here\n| a | b |\n") == {}


_SEED = """\
# 5. Natural Key 규칙

| 테이블 | Natural Key |
|--------|-------------|
| `cmn_class` | `(lang_cd, cls_id)` |
| `cmn_code` | `(cls_id, code_cd)` |
| `cmn_lbl` | `(lbl_cd, lang_cd)` |
| `cmn_menu` | `menu_id` |
| `cmn_pgm` | `pgm_id` |
| `cmn_role_menu` | `(role_id, menu_id)` |
| `cmn_role_pgm` | `(role_id, pgm_id)` |

모든 Upsert는 위 Key 기준 사용한다.

# 3. 생성 순서

1. `cmn_class`
2. `cmn_code`
3. `cmn_lbl`
4. `cmn_pgm`
5. `cmn_menu`
6. `cmn_role_pgm`
7. `cmn_role_menu`

순서 변경 금지.
"""


def test_parse_seed_natural_keys():
    out = gc._parse_seed_natural_keys(_SEED)
    assert out["cmn_class"] == ["lang_cd", "cls_id"]
    assert out["cmn_code"] == ["cls_id", "code_cd"]
    assert out["cmn_menu"] == ["menu_id"]
    assert out["cmn_role_pgm"] == ["role_id", "pgm_id"]
    assert len(out) == 7


def test_parse_seed_order():
    out = gc._parse_seed_order(_SEED)
    assert out == ["cmn_class", "cmn_code", "cmn_lbl", "cmn_pgm",
                   "cmn_menu", "cmn_role_pgm", "cmn_role_menu"]


def test_load_backend_path_templates_from_real_guide():
    # The fixed BackendGuide/표준.md §11.4 must yield all 6 generated backend/data types.
    out = gc.load_backend_path_templates()
    for ft in ("db_init_sql", "dto_request", "dto_response",
               "dao_impl", "service_impl", "mapper_xml"):
        assert ft in out, f"missing {ft} in §11.4 parse: {list(out)}"
    assert out["dto_request"].startswith("src/main/java/biz/{module}/dto/request/")


def test_load_seed_order_from_real_guide():
    assert gc.load_seed_order() == [
        "cmn_class", "cmn_code", "cmn_lbl", "cmn_pgm",
        "cmn_menu", "cmn_role_pgm", "cmn_role_menu"]


def test_load_seed_natural_keys_from_real_guide():
    nk = gc.load_seed_natural_keys()
    assert nk.get("cmn_lbl") == ["lbl_cd", "lang_cd"]
    assert nk.get("cmn_role_pgm") == ["role_id", "pgm_id"]
    assert set(nk) >= {"cmn_class", "cmn_code", "cmn_lbl", "cmn_pgm",
                       "cmn_menu", "cmn_role_menu", "cmn_role_pgm"}


# ---------------------------------------------------------------------------
# Fix I2 — section-absent returns empty (TDD: add first, must fail)
# ---------------------------------------------------------------------------

def test_parse_seed_natural_keys_empty_when_section_absent():
    assert gc._parse_seed_natural_keys("# no relevant section\n| `cmn_x` | `a` |\n") == {}


def test_parse_seed_order_empty_when_section_absent():
    assert gc._parse_seed_order("# nope\n1. `cmn_class`\n2. `cmn_code`\n") == []


# ---------------------------------------------------------------------------
# Fix I1 — digit-safe column names
# ---------------------------------------------------------------------------

def test_parse_seed_natural_keys_preserves_digits_in_column_names():
    text = "# 5. Natural Key\n| 테이블 | Natural Key |\n|--|--|\n| cmn_x | (col_1, id2) |\n"
    assert gc._parse_seed_natural_keys(text) == {"cmn_x": ["col_1", "id2"]}


# ---------------------------------------------------------------------------
# Fix M3 — bare-word NK values (no backticks)
# ---------------------------------------------------------------------------

def test_parse_seed_natural_keys_handles_bare_word_values():
    text = ("# 5. Natural Key\n| 테이블 | Natural Key |\n|--|--|\n"
            "| cmn_menu | menu_id |\n| cmn_code | (cls_id, code_cd) |\n")
    out = gc._parse_seed_natural_keys(text)
    assert out == {"cmn_menu": ["menu_id"], "cmn_code": ["cls_id", "code_cd"]}
