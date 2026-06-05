from app.llm.graph.paths import Identity, backend_path, frontend_paths, data_path

# CPMS domain-function family: screenId camelCase, className PascalCase.
CPMS = Identity(module="edu", category="pondg",
                screen_id="cpmsEduPondgLst", class_name="CpmsEduPondgLst")


def test_backend_path_dto_request():
    assert backend_path("dto_request", CPMS) == (
        "src/main/java/biz/edu/dto/request/CpmsEduPondgLstReqDto.java")


def test_backend_path_mapper_xml():
    assert backend_path("mapper_xml", CPMS) == (
        "src/main/resources/biz/edu/mybatis/mappers/CpmsEduPondgLstMapper.xml")


def test_backend_path_unknown_type_returns_none():
    assert backend_path("not_a_type", CPMS) is None


def test_data_path():
    assert data_path() == "db/init.sql"


# SY system-module family golden example from FrontendGuide (pmdp020 / PMDP020).
SY = Identity(module="sy", category="ds",
              screen_id="pmdp020", class_name="PMDP020")


def test_frontend_paths_page_and_types_and_api():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable"])
    assert fe["vue_page"] == "src/pages/sy/ds/pmdp020/index.vue"
    assert fe["vue_page_scss"] == "src/pages/sy/ds/pmdp020/pmdp020.scss"
    assert fe["vue_types"] == "src/api/pages/sy/ds/types.ts"          # category-shared
    assert fe["vue_api"] == "src/api/pages/sy/ds/pmdp020.ts"


def test_frontend_paths_components_folder_camel_file_pascal():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable"])
    assert fe["vue_searchform"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020SearchForm/PMDP020SearchForm.vue")
    assert fe["vue_searchform_scss"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020SearchForm/PMDP020SearchForm.scss")
    assert fe["vue_datatable"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020DataTable/PMDP020DataTable.vue")
    # only DataTable has a utils/index.ts
    assert fe["vue_datatable_utils"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020DataTable/utils/index.ts")


def test_frontend_paths_omits_sumgrid_when_not_requested():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable"])
    assert "vue_sumgrid" not in fe


def test_frontend_paths_includes_sumgrid_when_requested():
    fe = frontend_paths(SY, components=["SearchForm", "DataTable", "SumGrid"])
    assert fe["vue_sumgrid"] == (
        "src/pages/sy/ds/pmdp020/components/pmdp020SumGrid/PMDP020SumGrid.vue")
    assert "vue_datatable_utils" in fe   # SumGrid does NOT add a utils dir
    assert "vue_sumgrid_utils" not in fe
