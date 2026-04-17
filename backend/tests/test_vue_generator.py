from app.llm.vue_generator import generate_vue_page


def test_generate_list_detail_page():
    result = generate_vue_page(
        screen_id="MNET010",
        screen_name="신고 관리",
        page_type="list-detail",
        fields=[
            {"key": "reportType", "label": "신고유형", "type": "select",
             "searchable": True, "listable": True, "detailable": True,
             "options": [{"label": "내부", "value": "INTERNAL"}, {"label": "외부", "value": "EXTERNAL"}]},
            {"key": "title", "label": "제목", "type": "text",
             "searchable": True, "listable": True, "detailable": True},
            {"key": "content", "label": "내용", "type": "textarea",
             "detailable": True, "editable": True},
        ],
    )
    assert "<template>" in result
    assert "MNET010" in result
    assert "신고 관리" in result
    assert "ContentHeader" in result
    assert "SearchForm" in result
    assert "DataTable" in result
    assert "searchParams" in result
    assert "MOCK_DATA" in result


def test_generate_list_page():
    result = generate_vue_page(
        screen_id="MNET020",
        screen_name="처리 현황",
        page_type="list",
        fields=[
            {"key": "name", "label": "이름", "type": "text", "searchable": True, "listable": True},
        ],
    )
    assert "<template>" in result
    assert "SearchForm" in result


def test_generate_edit_page():
    result = generate_vue_page(
        screen_id="MNET030",
        screen_name="신고 등록",
        page_type="edit",
        fields=[
            {"key": "title", "label": "제목", "type": "text", "editable": True, "required": True},
            {"key": "content", "label": "내용", "type": "textarea", "editable": True},
        ],
    )
    assert "<template>" in result
    assert "MNET030" in result
    assert "editForm" in result
    assert "onSave" in result


def test_generate_tab_detail_page():
    result = generate_vue_page(
        screen_id="MNET040",
        screen_name="상세 탭",
        page_type="tab-detail",
        fields=[
            {"key": "name", "label": "이름", "type": "text", "searchable": True, "listable": True},
        ],
        tabs=[
            {"key": "basic", "label": "기본정보", "fields": [
                {"key": "name", "label": "이름", "type": "text", "detailable": True},
            ]},
            {"key": "detail", "label": "상세정보", "fields": [
                {"key": "memo", "label": "메모", "type": "textarea", "detailable": True},
            ]},
        ],
    )
    assert "<template>" in result
    assert "TABS" in result
    assert "basic" in result
    assert "detail" in result
