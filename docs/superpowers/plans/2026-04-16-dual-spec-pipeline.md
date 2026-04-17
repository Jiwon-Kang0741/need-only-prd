# Dual Spec Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 텍스트 입력과 Mockup 생성 두 가지 spec 생성 경로를 탭 UI로 제공하고, 두 경로 모두 동일한 코드 생성 파이프라인으로 연결한다.

**Architecture:** FastAPI 백엔드에 Mockup 파이프라인 6개 API를 추가하고, React 프론트엔드에 탭 전환 + 6단계 스텝퍼 UI를 구현한다. 두 경로 모두 `session.spec_markdown`에 최종 결과를 저장하여 기존 SpecViewer/ChatPanel/CodeGenPanel을 재사용한다.

**Tech Stack:** Python/FastAPI, React 19/TypeScript, Zustand, Tailwind CSS v4, SSE

---

## File Structure

### Backend (신규 생성)
- `backend/app/llm/mockup_pipeline.py` — MockupPipeline 클래스 (6단계 오케스트레이션)
- `backend/app/llm/mockup_prompts.py` — pfy-front 프롬프트 Python 포팅
- `backend/app/llm/vue_generator.py` — VuePageGenerator + MockDataGenerator Python 포팅
- `backend/app/routers/mockup.py` — `/api/mockup/*` 6개 엔드포인트

### Backend (수정)
- `backend/app/models.py` — MockupState 모델 추가, SessionState 확장
- `backend/app/main.py` — mockup 라우터 등록

### Frontend (신규 생성)
- `frontend/src/components/SpecModeSelector.tsx` — 탭 전환 컴포넌트
- `frontend/src/components/mockup/MockupPipeline.tsx` — 6단계 스텝퍼 컨테이너
- `frontend/src/components/mockup/StepIndicator.tsx` — 상단 스텝퍼 바
- `frontend/src/components/mockup/Step1AiGenerate.tsx` — 화면 설계 입력 + 결과
- `frontend/src/components/mockup/Step2Scaffold.tsx` — Vue 코드 미리보기
- `frontend/src/components/mockup/Step3Annotate.tsx` — 주석 결과
- `frontend/src/components/mockup/Step4Interview.tsx` — 인터뷰 질문/답변
- `frontend/src/components/mockup/Step5InterviewResult.tsx` — InterviewNote 결과
- `frontend/src/components/mockup/Step6SpecGenerate.tsx` — spec 생성 스트리밍

### Frontend (수정)
- `frontend/src/types/index.ts` — Mockup 관련 타입 추가
- `frontend/src/api/client.ts` — Mockup API 함수 추가
- `frontend/src/store/sessionStore.ts` — mockup 상태/액션 추가
- `frontend/src/App.tsx` — InputPanel → SpecModeSelector 교체

### Tests
- `backend/tests/test_mockup_models.py` — MockupState 모델 테스트
- `backend/tests/test_vue_generator.py` — Vue 코드 생성 테스트
- `backend/tests/test_mockup_router.py` — Mockup API 엔드포인트 테스트

---

## Task 1: Backend 모델 확장 (MockupState + SessionState)

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/tests/test_mockup_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_mockup_models.py
from app.models import MockupState, SessionState, FieldOption, FieldDef


def test_mockup_state_defaults():
    state = MockupState(
        screen_id="MNET010",
        screen_name="신고 관리",
        page_type="list-detail",
        fields=[],
    )
    assert state.screen_id == "MNET010"
    assert state.vue_code is None
    assert state.annotations is None
    assert state.interview_questions is None
    assert state.current_step == 1


def test_mockup_state_full():
    state = MockupState(
        screen_id="MNET010",
        screen_name="신고 관리",
        page_type="list",
        fields=[{"key": "name", "label": "이름", "type": "text"}],
        vue_code="<template>...</template>",
        annotations=[{"id": "input-name", "type": "input"}],
        annotation_markdown="| id | type |\n|---|---|\n| input-name | input |",
        interview_questions=[{"no": 1, "question": "Q1"}],
        interview_answers=[{"no": 1, "answer": "A1"}],
        current_step=4,
    )
    assert state.current_step == 4
    assert len(state.fields) == 1
    assert state.vue_code is not None


def test_session_state_with_mockup():
    from datetime import datetime, timezone
    session = SessionState(
        session_id="test-123",
        created_at=datetime.now(timezone.utc),
        spec_source="mockup",
        mockup_state=MockupState(
            screen_id="MNET010",
            screen_name="테스트",
            page_type="list",
            fields=[],
        ),
    )
    assert session.spec_source == "mockup"
    assert session.mockup_state is not None
    assert session.mockup_state.screen_id == "MNET010"


def test_session_state_without_mockup():
    from datetime import datetime, timezone
    session = SessionState(
        session_id="test-456",
        created_at=datetime.now(timezone.utc),
    )
    assert session.spec_source is None
    assert session.mockup_state is None


def test_field_def_model():
    field = FieldDef(
        key="reportType",
        label="신고유형",
        type="select",
        searchable=True,
        listable=True,
        options=[
            FieldOption(label="전체", value=""),
            FieldOption(label="내부", value="INTERNAL"),
        ],
    )
    assert field.key == "reportType"
    assert len(field.options) == 2


def test_field_def_minimal():
    field = FieldDef(key="name", label="이름", type="text")
    assert field.searchable is False
    assert field.options is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_mockup_models.py -v`
Expected: FAIL — `MockupState`, `FieldDef`, `FieldOption` not defined in `app.models`

- [ ] **Step 3: Add models to models.py**

Add the following to `backend/app/models.py` after the existing `CodeGenState` class:

```python
# --- Mockup Pipeline Models ---


class FieldOption(BaseModel):
    label: str
    value: str
    color: str | None = None


class FieldDef(BaseModel):
    key: str
    label: str
    type: Literal["text", "number", "select", "radio", "badge", "date", "daterange", "textarea", "checkbox"]
    searchable: bool = False
    listable: bool = False
    detailable: bool = False
    editable: bool = False
    required: bool = False
    options: list[FieldOption] | None = None
    width: str | None = None


class TabDef(BaseModel):
    key: str
    label: str
    fields: list[FieldDef]


class MockupState(BaseModel):
    screen_id: str
    screen_name: str
    page_type: Literal["list-detail", "list", "edit", "tab-detail"]
    fields: list[dict] = Field(default_factory=list)
    tabs: list[TabDef] | None = None
    vue_code: str | None = None
    annotations: list[dict] | None = None
    annotation_markdown: str | None = None
    interview_questions: list[dict] | None = None
    interview_answers: list[dict] | None = None
    raw_interview_text: str | None = None
    interview_note_md: str | None = None
    current_step: int = 1
```

Add `spec_source` and `mockup_state` to `SessionState`:

```python
class SessionState(BaseModel):
    session_id: str
    created_at: datetime
    raw_input: RawInput | None = None
    extracted_requirements: ExtractedRequirements | None = None
    spec_markdown: str | None = None
    spec_version: int = 0
    chat_history: list[ChatMessage] = Field(default_factory=list)
    validation_result: ValidationResult | None = None
    llm_call_count: int = 0
    codegen: CodeGenState | None = None
    spec_source: Literal["text", "mockup"] | None = None
    mockup_state: MockupState | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_mockup_models.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_mockup_models.py
git commit -m "feat(models): add MockupState, FieldDef models and extend SessionState"
```

---

## Task 2: Vue 코드 생성기 Python 포팅

**Files:**
- Create: `backend/app/llm/vue_generator.py`
- Create: `backend/tests/test_vue_generator.py`

**Reference:** `pfy-front/scaffolding/src/generators/VuePageGenerator.ts` + `MockDataGenerator.ts` (feat/pfy-front-scaffolding 브랜치에서 `git show` 로 참조)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_vue_generator.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_vue_generator.py -v`
Expected: FAIL — `app.llm.vue_generator` module not found

- [ ] **Step 3: Implement vue_generator.py**

Create `backend/app/llm/vue_generator.py` — Python 포팅 of `VuePageGenerator.ts` + `MockDataGenerator.ts`.

핵심 구조:
```python
"""Vue SFC 생성기 — pfy-front scaffolding의 VuePageGenerator.ts Python 포팅."""
from __future__ import annotations
from datetime import datetime, timezone


def generate_vue_page(
    screen_id: str,
    screen_name: str,
    page_type: str,
    fields: list[dict],
    tabs: list[dict] | None = None,
    menu_path: list[str] | None = None,
) -> str:
    """ScaffoldRequest에 해당하는 Vue SFC 문자열을 생성한다."""
    if page_type in ("list-detail", "list"):
        return _generate_list_detail_sfc(screen_id, screen_name, page_type, fields, menu_path)
    elif page_type == "edit":
        return _generate_edit_sfc(screen_id, screen_name, fields)
    elif page_type == "tab-detail":
        return _generate_tab_detail_sfc(screen_id, screen_name, fields, tabs or [], menu_path)
    else:
        return _generate_list_detail_sfc(screen_id, screen_name, page_type, fields, menu_path)
```

`VuePageGenerator.ts`의 모든 헬퍼 함수를 Python으로 1:1 포팅한다:
- `_collect_import_needs(fields)` → ImportNeeds dict
- `_build_imports(needs, page_type)` → import 문자열
- `_render_search_field(field)` → SearchForm 필드 HTML
- `_render_column(field)` → DataTable Column HTML
- `_render_detail_row(field, data_ref)` → 상세 행 HTML
- `_render_form_row(field)` → Edit 폼 행 HTML
- `_generate_mock_assets(fields, row_count=20)` → interface, mock data, searchParams, options 코드
- `_generate_filter_logic(fields)` → computed filteredRows 로직
- `_generate_list_detail_sfc(...)` → list/list-detail Vue SFC
- `_generate_edit_sfc(...)` → edit Vue SFC
- `_generate_tab_detail_sfc(...)` → tab-detail Vue SFC

TypeScript 원본의 문자열 템플릿을 Python f-string으로 변환. 로직은 동일하게 유지한다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_vue_generator.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/vue_generator.py backend/tests/test_vue_generator.py
git commit -m "feat(vue-generator): port VuePageGenerator and MockDataGenerator to Python"
```

---

## Task 3: Mockup 프롬프트 포팅

**Files:**
- Create: `backend/app/llm/mockup_prompts.py`

**Reference:** pfy-front 브랜치의 `ai-generate.ts`, `ai-annotate.ts`, `ai-interview-questions.ts`, `interview-result.ts`, `RequirementPrompt/masterPrompt.md`

- [ ] **Step 1: Create mockup_prompts.py**

```python
# backend/app/llm/mockup_prompts.py
"""pfy-front scaffolding 서버의 프롬프트를 Python으로 포팅."""
from __future__ import annotations

from pathlib import Path

from app.config import settings


def _load_master_prompt() -> str:
    """RequirementPrompt/masterPrompt.md 로딩 (pfy_prompt 디렉토리에서)."""
    path = Path(settings.PROMPT_REFERENCE_DIR) / "masterPrompt.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def ai_generate_prompt(
    page_type: str, title: str, description: str | None = None,
) -> tuple[str, str]:
    """화면 제목/설명 → 필드/컬럼/Mock 데이터 JSON 설계 프롬프트."""
    # pfy-front ai-generate.ts buildPrompt() 포팅
    system = "당신은 엔터프라이즈 UI 설계 전문가입니다. 요청한 JSON 형식으로만 답변합니다."
    desc_line = f"\n화면 설명: {description}" if description and description.strip() else ""

    if page_type == "list":
        user = f"""당신은 한국 엔터프라이즈 UI를 설계하는 시니어 개발자 및 DB 아키텍트입니다.
아래 화면 정보를 보고 목록(List) 화면 설계 정보를 응답하세요.

화면 제목: {title}{desc_line}

반드시 아래 JSON 형식으로만 응답하세요 (코드블록, 설명 없이):
{{
  "domain": "화면의도메인명(영문)",
  "searchFields": [
    {{
      "key": "camelCase영문키",
      "label": "한글레이블",
      "type": "text|number|date|daterange|select|checkbox",
      "optionsText": "select일 때만 포함",
      "operator": "EQ|LIKE|BETWEEN|IN"
    }}
  ],
  "tableColumns": [
    {{
      "key": "camelCase영문키",
      "label": "한글헤더명",
      "dataType": "VARCHAR|NUMBER|DATETIME",
      "dataLength": "길이",
      "align": "left|center|right"
    }}
  ],
  "mockRows": [
    {{ "tableColumns의key1": "현실적인샘플값" }}
  ]
}}

규칙:
- searchFields: 3~5개, 실제 업무에서 자주 쓰이는 조회 조건
- tableColumns: 5~8개 (No 컬럼 제외), 목록에 표시할 주요 정보
- key는 반드시 영문 camelCase, 실제 DB 컬럼명으로 활용 가능하도록 의미 있게 작성
- type이 select인 경우 반드시 optionsText 필드를 포함하고, 값은 "코드1:라벨1, 코드2:라벨2" 형식
- mockRows: 10건, tableColumns의 key와 정확히 일치하는 key로 구성"""
    else:
        user = f"""당신은 한국 엔터프라이즈 UI를 설계하는 시니어 개발자입니다.
아래 화면 정보를 보고 입력/수정(Form) 화면 설계 정보를 응답하세요.

화면 제목: {title}{desc_line}

반드시 아래 JSON 형식으로만 응답하세요 (코드블록, 설명 없이):
{{
  "formFields": [
    {{
      "key": "camelCase영문키",
      "label": "한글레이블",
      "type": "text|number|date|select|textarea|checkbox",
      "required": true,
      "optionsText": "select일 때만 포함",
      "validation": {{
        "min": "최소값/최소길이",
        "max": "최대값/최대길이"
      }},
      "description": "필드에 대한 비즈니스 설명"
    }}
  ]
}}

규칙:
- formFields: 5~10개, 실제 업무에서 입력하는 항목
- key는 반드시 영문 camelCase"""

    return system, user


def annotation_prompt(template_section: str) -> tuple[str, str]:
    """Vue <template> → UI 요소별 주석 JSON 배열 프롬프트."""
    system = """당신은 Vue.js <template>을 분석하여 각 UI 요소에 대한 구조화된 주석 정보를 JSON 배열로 반환하는 분석가입니다.

[출력 형식 (STRICT)]
반드시 아래 JSON 배열만 반환하세요. 다른 텍스트 없이:
[
  {
    "selector": "엘리먼트를 식별할 수 있는 코드 스니펫 (15자 이내)",
    "id": "kebab-case 고유 ID",
    "type": "input | action | display | container",
    "summary": "요소 설명 (20자 이내)",
    "note": "동작 또는 정책 (30자 이내)",
    "model": "v-model 값 또는 null",
    "constraints": "업무 제약사항 (50자 이내) 또는 null"
  }
]

[규칙]
- 주요 UI 요소만 포함 (최대 20개)
- JSON만 출력, Markdown 코드블럭 금지"""
    user = template_section
    return system, user


def interview_prompt(
    title: str,
    annotation_markdown: str | None = None,
    vue_source: str | None = None,
    spec_json: dict | None = None,
) -> tuple[str, str]:
    """주석 테이블 + MockUp → 인터뷰 질문 10개 프롬프트."""
    role_context = """# Role
당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다.
제공된 [MockUp 코드]와 [컴포넌트 주석 테이블]을 분석하여, 설계 확정을 위한 핵심 인터뷰 질문 10개를 생성해 주세요.

# Context
이 인터뷰의 목적은 목업 단계의 가설을 확정하여 Back-End API 설계서와 DB 정의서를 포함한 Spec.md를 도출하기 위함입니다.

# Question Generation Rules
1. 데이터 스펙 확정: 각 필드의 타입, 길이, 필수 여부를 확인하는 질문 포함.
2. 검색 및 정렬 로직: 검색 시 일치 조건(Like vs Equal)과 기본 정렬 순서 확인.
3. 비즈니스 예외 케이스: 데이터가 없거나, 권한이 없거나, 서버 오류 시의 사용자 경험 확인.
4. 연동 및 출력: 엑셀 다운로드 범위, 타 시스템 연동 데이터 등에 대한 질문.
5. 어조: 전문적이면서도 현업이 이해하기 쉬운 비즈니스 용어 사용."""

    output_format = """# Output Format
반드시 아래 JSON 형식으로만 응답하세요:
{
  "questions": [
    {
      "category": "조회조건|데이터정의|사용자행동|권한|예외처리 중 하나",
      "question": "구체적인 질문 (보충 질문 포함)",
      "priority": "높음|보통|낮음",
      "tip": "현재 목업 기반 설계 가설 (1~2문장)"
    }
  ]
}
규칙: questions 배열 길이는 정확히 10"""

    system = "당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다. 지정한 JSON 스키마로만 답하고, questions는 반드시 10개입니다."

    if annotation_markdown and annotation_markdown.strip():
        source_section = ""
        if vue_source and vue_source.strip():
            source_section = f"\n\n--- MockUp 소스 코드 시작 ---\n```vue\n{vue_source}\n```\n--- MockUp 소스 코드 끝 ---"

        user = f"""{role_context}

아래는 "{title}" 화면에 대해 자동 생성된 컴포넌트 주석 테이블입니다.

--- 컴포넌트 주석 테이블 시작 ---
{annotation_markdown}
--- 컴포넌트 주석 테이블 끝 ---{source_section}

{output_format}"""
    else:
        import json
        spec_str = json.dumps(spec_json or {}, indent=2, ensure_ascii=False)
        user = f"""{role_context}

아래는 MockUp Builder에서 정의된 "{title}" 화면 스펙(JSON)입니다.

--- 화면 스펙 시작 ---
{spec_str}
--- 화면 스펙 끝 ---

{output_format}"""

    return system, user


def interview_notes_prompt(
    title: str, questions_answers: list[dict],
) -> tuple[str, str]:
    """인터뷰 질문+답변 → InterviewNote.md 생성 프롬프트."""
    import json
    system = "당신은 IT 비즈니스 분석가입니다. 인터뷰 결과를 구조화된 Markdown 문서로 정리합니다."
    qa_text = json.dumps(questions_answers, indent=2, ensure_ascii=False)
    user = f"""아래 인터뷰 질문과 답변을 바탕으로 "{title}" 화면의 InterviewNote.md를 작성하세요.

## 인터뷰 결과
{qa_text}

## 출력 형식
Markdown 문서로 아래 구조를 따르세요:
# {title} — 인터뷰 결과

## 확정 기능 (Keep)
- 반드시 구현할 기능 목록

## 변경 요구 (Change)
- 기존 설계에서 변경이 필요한 항목

## 추가 요구 (Add)
- 새롭게 추가된 기능/요구사항

## 미결 사항 (TBD)
- 추후 확인이 필요한 항목"""
    return system, user


def extract_structured_data_prompt(raw_text: str) -> tuple[str, str]:
    """인터뷰 전문(raw text) → keep/change/add/tbd 구조화 JSON 프롬프트."""
    system = "당신은 인터뷰 텍스트에서 구조화된 데이터를 추출하는 분석가입니다. JSON만 출력합니다."
    user = f"""아래 인터뷰 전문에서 설계 결정 사항을 추출하여 JSON으로 분류하세요.

--- 인터뷰 전문 ---
{raw_text}
--- 인터뷰 전문 끝 ---

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "keep": ["확정된 기능/요구사항"],
  "change": ["변경이 필요한 항목"],
  "add": ["새로 추가된 기능"],
  "tbd": ["미결 사항"]
}}"""
    return system, user


def merge_annotations_prompt(
    annotation_markdown: str, interview_data: dict,
) -> tuple[str, str]:
    """@id 주석에 인터뷰 결과를 매칭하여 병합하는 프롬프트."""
    import json
    system = "당신은 UI 주석과 인터뷰 결과를 매칭하는 분석가입니다."
    data_str = json.dumps(interview_data, indent=2, ensure_ascii=False)
    user = f"""아래 컴포넌트 주석 테이블의 각 @id 항목에 인터뷰 결과를 매칭하여, 보강된 주석 테이블을 반환하세요.

--- 주석 테이블 ---
{annotation_markdown}
--- 주석 테이블 끝 ---

--- 인터뷰 결과 ---
{data_str}
--- 인터뷰 결과 끝 ---

각 주석 항목에 @interview 필드를 추가하여 관련 인터뷰 결과를 연결하세요. 원본 주석의 다른 필드는 그대로 유지합니다. Markdown 테이블 형식으로 출력하세요."""
    return system, user


def master_spec_prompt(
    title: str,
    annotation_markdown: str,
    interview_note_md: str,
    vue_source: str | None = None,
) -> tuple[str, str]:
    """masterPrompt.md 기반 최종 spec.md 생성 프롬프트."""
    master = _load_master_prompt()
    system = master if master else "You are a senior software architect creating a technical specification (spec.md)."

    source_section = ""
    if vue_source and vue_source.strip():
        source_section = f"\n\n## [2] Mockup 화면\n```vue\n{vue_source}\n```"

    user = f"""# Customer Input (고객 요구사항)

## [1] 인터뷰 회의록
{interview_note_md}
{source_section}

## [3] 컴포넌트 주석 테이블
{annotation_markdown}

화면명: {title}

위 데이터를 기반으로 spec.md를 생성하세요."""
    return system, user
```

- [ ] **Step 2: Verify module imports**

Run: `cd backend && python -c "from app.llm.mockup_prompts import ai_generate_prompt, annotation_prompt, interview_prompt, master_spec_prompt; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/llm/mockup_prompts.py
git commit -m "feat(mockup-prompts): port pfy-front prompts to Python"
```

---

## Task 4: Mockup 파이프라인 클래스

**Files:**
- Create: `backend/app/llm/mockup_pipeline.py`

- [ ] **Step 1: Create mockup_pipeline.py**

```python
# backend/app/llm/mockup_pipeline.py
"""Mockup 기반 6단계 spec 생성 파이프라인."""
from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator

from app.llm.client import llm_client
from app.llm.mockup_prompts import (
    ai_generate_prompt,
    annotation_prompt,
    extract_structured_data_prompt,
    interview_notes_prompt,
    interview_prompt,
    master_spec_prompt,
    merge_annotations_prompt,
)
from app.llm.vue_generator import generate_vue_page


def _extract_json(text: str) -> dict | list:
    """LLM 응답에서 JSON 추출 (코드블록 제거 포함)."""
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()
    return json.loads(cleaned)


class MockupPipeline:
    # ── Step 1: AI Generate ──────────────────────────────────────────────────
    async def ai_generate(
        self, title: str, page_type: str, description: str | None = None,
    ) -> dict:
        """화면 제목 → 필드/컬럼/Mock 설계 JSON."""
        system, user = ai_generate_prompt(page_type, title, description)
        response = await llm_client.complete(system, user, stream=False)
        return _extract_json(response)

    # ── Step 2: Scaffold ─────────────────────────────────────────────────────
    def scaffold(
        self,
        screen_id: str,
        screen_name: str,
        page_type: str,
        fields: list[dict],
        tabs: list[dict] | None = None,
    ) -> str:
        """필드 정의 → Vue SFC 코드 생성 (LLM 불필요)."""
        return generate_vue_page(
            screen_id=screen_id,
            screen_name=screen_name,
            page_type=page_type,
            fields=fields,
            tabs=tabs,
        )

    # ── Step 3: AI Annotate ──────────────────────────────────────────────────
    async def ai_annotate(self, vue_code: str) -> tuple[str, list[dict], str]:
        """Vue 코드 → 주석 삽입된 코드, 주석 목록, 주석 마크다운 테이블."""
        template_section = self._extract_template(vue_code)
        if not template_section:
            raise ValueError("<template> 블록을 찾을 수 없습니다.")

        analysis_target = template_section[:6000] if len(template_section) > 6000 else template_section

        system, user = annotation_prompt(analysis_target)
        response = await llm_client.complete(system, user, stream=False)
        annotations = _extract_json(response)
        if not isinstance(annotations, list):
            raise ValueError("LLM이 주석 배열을 반환하지 않았습니다.")

        annotated_code = self._inject_annotations(vue_code, annotations)
        markdown = self._annotations_to_markdown(annotations)
        return annotated_code, annotations, markdown

    # ── Step 4: AI Interview ─────────────────────────────────────────────────
    async def ai_interview(
        self,
        title: str,
        annotation_markdown: str | None = None,
        vue_source: str | None = None,
        spec_json: dict | None = None,
    ) -> list[dict]:
        """주석 + MockUp → 인터뷰 질문 10개."""
        system, user = interview_prompt(title, annotation_markdown, vue_source, spec_json)
        response = await llm_client.complete(system, user, stream=False)
        result = _extract_json(response)
        questions = result.get("questions", result) if isinstance(result, dict) else result
        if not isinstance(questions, list):
            raise ValueError("questions 배열이 없습니다.")

        valid_priorities = {"높음", "보통", "낮음"}
        normalized = []
        for i, item in enumerate(questions[:10]):
            if isinstance(item, str):
                normalized.append({"no": i + 1, "category": "", "question": item, "priority": "보통", "tip": ""})
            else:
                p = item.get("priority", "보통")
                normalized.append({
                    "no": i + 1,
                    "category": str(item.get("category", "")),
                    "question": str(item.get("question", "")),
                    "priority": p if p in valid_priorities else "보통",
                    "tip": str(item.get("tip", "")),
                })
        return normalized

    # ── Step 5: Interview Result ─────────────────────────────────────────────
    async def interview_result(
        self,
        title: str,
        annotation_markdown: str,
        vue_source: str | None = None,
        questions: list[dict] | None = None,
        answers: list[dict] | None = None,
        raw_interview_text: str | None = None,
    ) -> tuple[str, str]:
        """인터뷰 답변 → InterviewNote.md + spec_markdown 생성.

        Returns:
            (interview_note_md, spec_markdown)
        """
        # Step 5a: Generate InterviewNote.md
        if raw_interview_text and raw_interview_text.strip():
            # raw text 모드: 구조화 데이터 추출 먼저
            sys_ext, usr_ext = extract_structured_data_prompt(raw_interview_text)
            ext_response = await llm_client.complete(sys_ext, usr_ext, stream=False)
            interview_data = _extract_json(ext_response)

            # InterviewNote 생성
            sys_note, usr_note = interview_notes_prompt(title, [{"raw_text": raw_interview_text}])
            interview_note_md = await llm_client.complete(sys_note, usr_note, stream=False)
        else:
            # 질문-답변 모드
            qa_pairs = []
            if questions and answers:
                for q, a in zip(questions, answers):
                    qa_pairs.append({
                        "question": q.get("question", ""),
                        "answer": a.get("answer", ""),
                        "category": q.get("category", ""),
                    })

            sys_note, usr_note = interview_notes_prompt(title, qa_pairs)
            interview_note_md = await llm_client.complete(sys_note, usr_note, stream=False)

            # 구조화 데이터 추출
            sys_ext, usr_ext = extract_structured_data_prompt(interview_note_md)
            ext_response = await llm_client.complete(sys_ext, usr_ext, stream=False)
            interview_data = _extract_json(ext_response)

        # Step 5b: Merge annotations
        sys_merge, usr_merge = merge_annotations_prompt(annotation_markdown, interview_data)
        merged_annotations = await llm_client.complete(sys_merge, usr_merge, stream=False)

        # Step 5c (Step 6): Generate spec.md
        sys_spec, usr_spec = master_spec_prompt(
            title=title,
            annotation_markdown=merged_annotations,
            interview_note_md=interview_note_md,
            vue_source=vue_source,
        )
        spec_markdown = await llm_client.complete(sys_spec, usr_spec, stream=False)
        return interview_note_md, spec_markdown

    # ── Step 6: Generate Spec (streaming) ────────────────────────────────────
    async def generate_spec_streaming(
        self,
        title: str,
        annotation_markdown: str,
        interview_note_md: str,
        vue_source: str | None = None,
    ) -> AsyncIterator[str]:
        """masterPrompt 기반 spec 스트리밍 생성."""
        sys_spec, usr_spec = master_spec_prompt(
            title=title,
            annotation_markdown=annotation_markdown,
            interview_note_md=interview_note_md,
            vue_source=vue_source,
        )
        stream = await llm_client.complete(sys_spec, usr_spec, stream=True)
        async for chunk in stream:
            yield chunk

    # ── Helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_template(source: str) -> str | None:
        start = source.find("<template")
        if start == -1:
            return None
        tag_end = source.find(">", start)
        if tag_end == -1:
            return None
        depth = 1
        pos = tag_end + 1
        while pos < len(source) and depth > 0:
            next_open = source.find("<template", pos)
            next_close = source.find("</template>", pos)
            if next_close == -1:
                return None
            if next_open != -1 and next_open < next_close:
                depth += 1
                pos = next_open + 9
            else:
                depth -= 1
                if depth == 0:
                    return source[start:next_close + len("</template>")]
                pos = next_close + 11
        return None

    @staticmethod
    def _inject_annotations(source: str, annotations: list[dict]) -> str:
        lines = source.split("\n")
        insertions = []
        for ann in annotations:
            sel = (ann.get("selector") or "").strip()
            if not sel:
                continue
            keyword = sel.lstrip("<").split()[0].split(">")[0]
            if not keyword:
                continue
            for idx, line in enumerate(lines):
                if keyword in line:
                    if any(ins["idx"] == idx for ins in insertions):
                        continue
                    indent = " " * (len(line) - len(line.lstrip()))
                    comment = "\n".join([
                        f"{indent}<!--",
                        f"{indent}  @id: {ann.get('id', '')}",
                        f"{indent}  @type: {ann.get('type', '')}",
                        f"{indent}  @summary: {ann.get('summary', '')}",
                        f"{indent}  @note: {ann.get('note', '')}",
                        f"{indent}  @model: {ann.get('model') or 'null'}",
                        f"{indent}  @constraints: {ann.get('constraints') or 'null'}",
                        f"{indent}-->",
                    ])
                    insertions.append({"idx": idx, "comment": comment})
                    break
        insertions.sort(key=lambda x: x["idx"], reverse=True)
        for ins in insertions:
            lines.insert(ins["idx"], ins["comment"])
        return "\n".join(lines)

    @staticmethod
    def _annotations_to_markdown(annotations: list[dict]) -> str:
        rows = ["| id | type | summary | note | model | constraints |",
                "|---|---|---|---|---|---|"]
        for ann in annotations:
            rows.append(
                f"| {ann.get('id', '')} | {ann.get('type', '')} "
                f"| {ann.get('summary', '')} | {ann.get('note', '')} "
                f"| {ann.get('model') or 'null'} | {ann.get('constraints') or 'null'} |"
            )
        return "\n".join(rows)


mockup_pipeline = MockupPipeline()
```

- [ ] **Step 2: Verify module imports**

Run: `cd backend && python -c "from app.llm.mockup_pipeline import mockup_pipeline; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/llm/mockup_pipeline.py
git commit -m "feat(mockup-pipeline): add MockupPipeline with 6-stage orchestration"
```

---

## Task 5: Mockup API 라우터

**Files:**
- Create: `backend/app/routers/mockup.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create mockup.py router**

```python
# backend/app/routers/mockup.py
"""Mockup 파이프라인 API 엔드포인트."""
from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.llm.mockup_pipeline import mockup_pipeline
from app.models import MockupState
from app.session import get_session_id, session_store

router = APIRouter(prefix="/mockup", tags=["mockup"])


# ── Request Models ───────────────────────────────────────────────────────────

class AiGenerateRequest(BaseModel):
    title: str
    page_type: str = "list"
    description: str | None = None


class ScaffoldRequest(BaseModel):
    screen_id: str
    screen_name: str
    page_type: str = "list-detail"
    fields: list[dict]
    tabs: list[dict] | None = None


class InterviewResultRequest(BaseModel):
    answers: list[dict] | None = None
    raw_interview_text: str | None = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_mockup_state(session_id: str) -> MockupState:
    session = session_store.get(session_id)
    if session is None or session.mockup_state is None:
        raise HTTPException(400, "Mockup 파이프라인이 시작되지 않았습니다. ai-generate를 먼저 실행하세요.")
    return session.mockup_state


# ── Step 1: AI Generate ─────────────────────────────────────────────────────

@router.post("/ai-generate")
async def ai_generate(
    body: AiGenerateRequest,
    session_id: str = Depends(get_session_id),
):
    if not body.title.strip():
        raise HTTPException(400, "화면 제목(title)은 필수입니다.")

    session_store.increment_llm_calls(session_id)
    result = await mockup_pipeline.ai_generate(body.title, body.page_type, body.description)

    session = session_store.get_or_create(session_id)
    session.spec_source = "mockup"
    session.mockup_state = MockupState(
        screen_id=re.sub(r"[^A-Za-z0-9_]", "", body.title)[:10].upper() or "SCR001",
        screen_name=body.title,
        page_type=body.page_type,
        fields=result.get("searchFields", []) + result.get("tableColumns", []),
        current_step=1,
    )
    session_store.save(session_id)

    return {"success": True, **result}


# ── Step 2: Scaffold ────────────────────────────────────────────────────────

@router.post("/scaffold")
async def scaffold(
    body: ScaffoldRequest,
    session_id: str = Depends(get_session_id),
):
    if not re.match(r"^[A-Za-z0-9_]+$", body.screen_id):
        raise HTTPException(400, "screenId는 영문·숫자·언더스코어만 허용됩니다.")

    vue_code = mockup_pipeline.scaffold(
        screen_id=body.screen_id,
        screen_name=body.screen_name,
        page_type=body.page_type,
        fields=body.fields,
        tabs=body.tabs,
    )

    session = session_store.get_or_create(session_id)
    if session.mockup_state is None:
        session.mockup_state = MockupState(
            screen_id=body.screen_id,
            screen_name=body.screen_name,
            page_type=body.page_type,
            fields=body.fields,
        )
    session.mockup_state.vue_code = vue_code
    session.mockup_state.screen_id = body.screen_id
    session.mockup_state.screen_name = body.screen_name
    session.mockup_state.page_type = body.page_type
    session.mockup_state.fields = body.fields
    session.mockup_state.current_step = 2
    session_store.save(session_id)

    return {"success": True, "vue_code": vue_code}


# ── Step 3: AI Annotate ─────────────────────────────────────────────────────

@router.post("/ai-annotate")
async def ai_annotate(
    session_id: str = Depends(get_session_id),
):
    ms = _get_mockup_state(session_id)
    if not ms.vue_code:
        raise HTTPException(400, "Vue 코드가 없습니다. scaffold를 먼저 실행하세요.")

    session_store.increment_llm_calls(session_id)
    annotated_code, annotations, markdown = await mockup_pipeline.ai_annotate(ms.vue_code)

    ms.vue_code = annotated_code
    ms.annotations = annotations
    ms.annotation_markdown = markdown
    ms.current_step = 3
    session_store.save(session_id)

    return {"success": True, "annotation_count": len(annotations), "annotation_markdown": markdown}


# ── Step 4: AI Interview ────────────────────────────────────────────────────

@router.post("/ai-interview")
async def ai_interview(
    session_id: str = Depends(get_session_id),
):
    ms = _get_mockup_state(session_id)

    session_store.increment_llm_calls(session_id)
    questions = await mockup_pipeline.ai_interview(
        title=ms.screen_name,
        annotation_markdown=ms.annotation_markdown,
        vue_source=ms.vue_code,
    )

    ms.interview_questions = questions
    ms.current_step = 4
    session_store.save(session_id)

    return {"success": True, "questions": questions}


# ── Step 5+6: Interview Result → Spec ───────────────────────────────────────

@router.post("/interview-result")
async def interview_result(
    body: InterviewResultRequest,
    session_id: str = Depends(get_session_id),
):
    ms = _get_mockup_state(session_id)
    session = session_store.get(session_id)

    if not body.answers and not body.raw_interview_text:
        raise HTTPException(400, "answers 또는 raw_interview_text가 필요합니다.")

    session_store.increment_llm_calls(session_id)
    session_store.increment_llm_calls(session_id)

    if body.raw_interview_text:
        ms.raw_interview_text = body.raw_interview_text
    if body.answers:
        ms.interview_answers = body.answers

    interview_note_md, spec_markdown = await mockup_pipeline.interview_result(
        title=ms.screen_name,
        annotation_markdown=ms.annotation_markdown or "",
        vue_source=ms.vue_code,
        questions=ms.interview_questions,
        answers=body.answers,
        raw_interview_text=body.raw_interview_text,
    )

    ms.interview_note_md = interview_note_md
    ms.current_step = 6
    session.spec_markdown = spec_markdown
    session.spec_version += 1
    session_store.save(session_id)

    return {
        "success": True,
        "interview_note_md": interview_note_md,
        "spec_version": session.spec_version,
    }


# ── Step 6 (alternative): Streaming spec generation ─────────────────────────

@router.post("/generate-spec")
async def generate_spec_streaming(
    session_id: str = Depends(get_session_id),
):
    ms = _get_mockup_state(session_id)
    session = session_store.get(session_id)

    if not ms.interview_note_md:
        raise HTTPException(400, "인터뷰 결과가 없습니다. interview-result를 먼저 실행하세요.")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Generating spec from interview results..."})}

            session_store.increment_llm_calls(session_id)
            full_spec = ""
            async for chunk in mockup_pipeline.generate_spec_streaming(
                title=ms.screen_name,
                annotation_markdown=ms.annotation_markdown or "",
                interview_note_md=ms.interview_note_md,
                vue_source=ms.vue_code,
            ):
                full_spec += chunk
                yield {"event": "message", "data": json.dumps({"type": "chunk", "content": chunk})}

            session.spec_markdown = full_spec
            session.spec_version += 1
            session_store.save(session_id)

            yield {"event": "message", "data": json.dumps({"type": "complete", "spec_version": session.spec_version})}

        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_generator(), ping=10)


# ── Annotate Constraints (optional step) ────────────────────────────────────

@router.post("/annotate-constraints")
async def annotate_constraints(
    session_id: str = Depends(get_session_id),
):
    ms = _get_mockup_state(session_id)
    if not ms.annotation_markdown:
        raise HTTPException(400, "주석 마크다운이 없습니다. ai-annotate를 먼저 실행하세요.")

    session_store.increment_llm_calls(session_id)
    # 제약조건 보강을 위한 추가 LLM 호출
    from app.llm.client import llm_client
    system = "주어진 주석 테이블의 각 항목에 대해 constraints 필드를 보강하세요. Markdown 테이블 형식으로 출력합니다."
    response = await llm_client.complete(system, ms.annotation_markdown, stream=False)
    ms.annotation_markdown = response
    session_store.save(session_id)

    return {"success": True, "annotation_markdown": response}
```

- [ ] **Step 2: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import mockup as mockup_router
```

And add the router:

```python
app.include_router(mockup_router.router, prefix="/api")
```

- [ ] **Step 3: Verify server starts**

Run: `cd backend && python -c "from app.main import app; print('Routes:', [r.path for r in app.routes][:5])"`
Expected: No import errors, routes listed

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/mockup.py backend/app/main.py
git commit -m "feat(mockup-api): add /api/mockup/* endpoints and register router"
```

---

## Task 6: Frontend 타입 및 API 클라이언트 확장

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add Mockup types to types/index.ts**

Append to `frontend/src/types/index.ts`:

```typescript
// --- Mockup Pipeline Types ---

export interface FieldOption {
  label: string
  value: string
  color?: string
}

export interface FieldDef {
  key: string
  label: string
  type: 'text' | 'number' | 'select' | 'radio' | 'badge' | 'date' | 'daterange' | 'textarea' | 'checkbox'
  searchable?: boolean
  listable?: boolean
  detailable?: boolean
  editable?: boolean
  required?: boolean
  options?: FieldOption[]
  width?: string
}

export interface InterviewQuestion {
  no: number
  category: string
  question: string
  priority: '높음' | '보통' | '낮음'
  tip: string
}

export interface MockupState {
  screenId: string
  screenName: string
  pageType: string
  fields: Record<string, unknown>[]
  vueCode: string | null
  annotations: Record<string, unknown>[] | null
  annotationMarkdown: string | null
  interviewQuestions: InterviewQuestion[] | null
  interviewAnswers: { no: number; answer: string }[] | null
  rawInterviewText: string | null
  interviewNoteMd: string | null
  currentStep: number
}

export interface AiGenerateResult {
  success: boolean
  domain?: string
  searchFields?: Record<string, unknown>[]
  tableColumns?: Record<string, unknown>[]
  mockRows?: Record<string, unknown>[]
  formFields?: Record<string, unknown>[]
}

export interface ScaffoldResult {
  success: boolean
  vue_code: string
}

export interface AnnotateResult {
  success: boolean
  annotation_count: number
  annotation_markdown: string
}

export interface InterviewResult {
  success: boolean
  questions: InterviewQuestion[]
}

export interface InterviewResultResponse {
  success: boolean
  interview_note_md: string
  spec_version: number
}
```

- [ ] **Step 2: Add Mockup API functions to client.ts**

Append to `frontend/src/api/client.ts`:

```typescript
// --- Mockup Pipeline API ---

export async function mockupAiGenerate(
  title: string, pageType: string, description?: string,
): Promise<import('../types').AiGenerateResult> {
  const res = await fetch('/api/mockup/ai-generate', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, page_type: pageType, description }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function mockupScaffold(
  screenId: string, screenName: string, pageType: string, fields: Record<string, unknown>[], tabs?: Record<string, unknown>[],
): Promise<import('../types').ScaffoldResult> {
  const res = await fetch('/api/mockup/scaffold', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ screen_id: screenId, screen_name: screenName, page_type: pageType, fields, tabs }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function mockupAiAnnotate(): Promise<import('../types').AnnotateResult> {
  const res = await fetch('/api/mockup/ai-annotate', {
    method: 'POST',
    headers: apiHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function mockupAiInterview(): Promise<import('../types').InterviewResult> {
  const res = await fetch('/api/mockup/ai-interview', {
    method: 'POST',
    headers: apiHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export async function mockupInterviewResult(
  answers?: { no: number; answer: string }[],
  rawInterviewText?: string,
): Promise<import('../types').InterviewResultResponse> {
  const res = await fetch('/api/mockup/interview-result', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers, raw_interview_text: rawInterviewText }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export function mockupGenerateSpec(onEvent: (event: import('../types').SSEEvent) => void): void {
  consumeSSE('/api/mockup/generate-spec', onEvent, {})
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No errors related to new types/API functions

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat(frontend): add Mockup pipeline types and API client functions"
```

---

## Task 7: Zustand 스토어 확장

**Files:**
- Modify: `frontend/src/store/sessionStore.ts`

- [ ] **Step 1: Add mockup state and actions to sessionStore.ts**

Import 추가:

```typescript
import type { ChatMessage, CodeGenState, ValidationResult, MockupState, InterviewQuestion } from '../types'
import {
  // ... existing imports ...
  mockupAiGenerate as apiMockupAiGenerate,
  mockupScaffold as apiMockupScaffold,
  mockupAiAnnotate as apiMockupAiAnnotate,
  mockupAiInterview as apiMockupAiInterview,
  mockupInterviewResult as apiMockupInterviewResult,
  mockupGenerateSpec as apiMockupGenerateSpec,
} from '../api/client'
```

SessionStore interface에 추가:

```typescript
  // --- Mockup Pipeline ---
  specMode: 'text' | 'mockup'
  mockupState: MockupState | null
  mockupLoading: boolean
  mockupError: string | null
  setSpecMode: (mode: 'text' | 'mockup') => void
  mockupAiGenerate: (title: string, pageType: string, description?: string) => Promise<void>
  mockupScaffold: (screenId: string, screenName: string, pageType: string, fields: Record<string, unknown>[]) => Promise<void>
  mockupAiAnnotate: () => Promise<void>
  mockupAiInterview: () => Promise<void>
  mockupSubmitInterviewResult: (answers?: { no: number; answer: string }[], rawText?: string) => Promise<void>
  mockupGenerateSpec: () => void
  mockupGoToStep: (step: number) => void
  resetMockup: () => void
```

초기값 및 구현:

```typescript
  specMode: 'text',
  mockupState: null,
  mockupLoading: false,
  mockupError: null,

  setSpecMode: (mode) => set({ specMode: mode }),

  mockupAiGenerate: async (title, pageType, description) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupAiGenerate(title, pageType, description)
      set({
        mockupState: {
          screenId: title.replace(/[^A-Za-z0-9_]/g, '').slice(0, 10).toUpperCase() || 'SCR001',
          screenName: title,
          pageType,
          fields: [...(result.searchFields || []), ...(result.tableColumns || [])],
          vueCode: null,
          annotations: null,
          annotationMarkdown: null,
          interviewQuestions: null,
          interviewAnswers: null,
          rawInterviewText: null,
          interviewNoteMd: null,
          currentStep: 1,
        },
        mockupLoading: false,
      })
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupScaffold: async (screenId, screenName, pageType, fields) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupScaffold(screenId, screenName, pageType, fields)
      set((state) => ({
        mockupState: state.mockupState ? {
          ...state.mockupState,
          screenId, screenName, pageType, fields,
          vueCode: result.vue_code,
          currentStep: 2,
        } : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupAiAnnotate: async () => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupAiAnnotate()
      set((state) => ({
        mockupState: state.mockupState ? {
          ...state.mockupState,
          annotationMarkdown: result.annotation_markdown,
          currentStep: 3,
        } : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupAiInterview: async () => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupAiInterview()
      set((state) => ({
        mockupState: state.mockupState ? {
          ...state.mockupState,
          interviewQuestions: result.questions,
          currentStep: 4,
        } : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupSubmitInterviewResult: async (answers, rawText) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupInterviewResult(answers, rawText)
      set((state) => ({
        mockupState: state.mockupState ? {
          ...state.mockupState,
          interviewAnswers: answers || null,
          rawInterviewText: rawText || null,
          interviewNoteMd: result.interview_note_md,
          currentStep: 5,
        } : null,
        specVersion: result.spec_version,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupGenerateSpec: () => {
    set({ isGenerating: true, statusMessage: 'Generating spec from interview results...', specMarkdown: null })
    apiMockupGenerateSpec((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? event.message ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
        set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + event.content }))
      } else if (event.type === 'complete') {
        set((state) => ({
          isGenerating: false,
          statusMessage: null,
          specVersion: event.spec_version ?? state.specVersion + 1,
          mockupState: state.mockupState ? { ...state.mockupState, currentStep: 6 } : null,
        }))
      } else if (event.type === 'error') {
        set({ isGenerating: false, statusMessage: event.content ?? event.message ?? 'An error occurred' })
      }
    })
  },

  mockupGoToStep: (step) => set((state) => ({
    mockupState: state.mockupState ? { ...state.mockupState, currentStep: step } : null,
  })),

  resetMockup: () => set({
    mockupState: null,
    mockupLoading: false,
    mockupError: null,
  }),
```

reset 함수에 mockup 상태 초기화 추가:

```typescript
  reset: () => {
    // ... existing reset logic ...
    set({
      // ... existing resets ...
      specMode: 'text',
      mockupState: null,
      mockupLoading: false,
      mockupError: null,
    })
  },
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/store/sessionStore.ts
git commit -m "feat(store): add mockup pipeline state and actions to sessionStore"
```

---

## Task 8: SpecModeSelector 탭 컴포넌트

**Files:**
- Create: `frontend/src/components/SpecModeSelector.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create SpecModeSelector.tsx**

```tsx
// frontend/src/components/SpecModeSelector.tsx
import { useSessionStore } from '../store/sessionStore'
import InputPanel from './InputPanel'
import MockupPipeline from './mockup/MockupPipeline'

export default function SpecModeSelector() {
  const specMode = useSessionStore((s) => s.specMode)
  const setSpecMode = useSessionStore((s) => s.setSpecMode)
  const mockupState = useSessionStore((s) => s.mockupState)
  const isGenerating = useSessionStore((s) => s.isGenerating)

  function handleTabChange(mode: 'text' | 'mockup') {
    if (isGenerating) return
    if (specMode === 'mockup' && mode === 'text' && mockupState && mockupState.currentStep > 1) {
      if (!confirm('진행 중인 Mockup 작업이 초기화됩니다. 계속하시겠습니까?')) return
    }
    setSpecMode(mode)
  }

  return (
    <div className="max-w-[900px] mx-auto">
      {/* Tab selector */}
      <div className="flex justify-center mb-8">
        <div className="inline-flex bg-surface-container rounded-2xl p-1.5 gap-1">
          <button
            onClick={() => handleTabChange('text')}
            disabled={isGenerating}
            className={`px-6 py-3 rounded-xl text-sm font-bold transition-all flex items-center gap-2 ${
              specMode === 'text'
                ? 'bg-primary text-on-primary shadow-md'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            } disabled:opacity-50`}
          >
            <span className="material-symbols-outlined text-[20px]">description</span>
            텍스트 입력
          </button>
          <button
            onClick={() => handleTabChange('mockup')}
            disabled={isGenerating}
            className={`px-6 py-3 rounded-xl text-sm font-bold transition-all flex items-center gap-2 ${
              specMode === 'mockup'
                ? 'bg-primary text-on-primary shadow-md'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            } disabled:opacity-50`}
          >
            <span className="material-symbols-outlined text-[20px]">devices</span>
            Mockup 생성
          </button>
        </div>
      </div>

      {/* Tab content */}
      {specMode === 'text' ? <InputPanel /> : <MockupPipeline />}
    </div>
  )
}
```

- [ ] **Step 2: Update App.tsx**

Replace `InputPanel` import and usage:

```tsx
// Replace: import InputPanel from './components/InputPanel'
import SpecModeSelector from './components/SpecModeSelector'

// In the JSX, replace:
// {!showSpec && !showOverlay ? (
//   <InputPanel />
// Replace with:
// {!showSpec && !showOverlay ? (
//   <SpecModeSelector />
```

- [ ] **Step 3: Create placeholder MockupPipeline.tsx**

```tsx
// frontend/src/components/mockup/MockupPipeline.tsx
export default function MockupPipeline() {
  return (
    <div className="text-center text-on-surface-variant p-12">
      <p>Mockup Pipeline — 구현 중...</p>
    </div>
  )
}
```

- [ ] **Step 4: Verify dev server renders tabs**

Run: `cd frontend && npm run dev`
Open browser → 탭 두 개가 보이고, "텍스트 입력" 탭 선택 시 기존 InputPanel이 동작하는지 확인.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SpecModeSelector.tsx frontend/src/components/mockup/MockupPipeline.tsx frontend/src/App.tsx
git commit -m "feat(ui): add SpecModeSelector tabs and placeholder MockupPipeline"
```

---

## Task 9: StepIndicator 컴포넌트

**Files:**
- Create: `frontend/src/components/mockup/StepIndicator.tsx`

- [ ] **Step 1: Create StepIndicator.tsx**

```tsx
// frontend/src/components/mockup/StepIndicator.tsx
const STEPS = [
  { num: 1, label: '화면설계', icon: 'auto_awesome' },
  { num: 2, label: 'Mockup', icon: 'code' },
  { num: 3, label: '주석', icon: 'comment' },
  { num: 4, label: '인터뷰', icon: 'forum' },
  { num: 5, label: '결과', icon: 'summarize' },
  { num: 6, label: 'Spec', icon: 'description' },
]

interface Props {
  currentStep: number
  onStepClick?: (step: number) => void
}

export default function StepIndicator({ currentStep, onStepClick }: Props) {
  return (
    <div className="flex items-center justify-center gap-1 mb-8">
      {STEPS.map((step, i) => {
        const isActive = step.num === currentStep
        const isCompleted = step.num < currentStep
        const isClickable = isCompleted && onStepClick

        return (
          <div key={step.num} className="flex items-center">
            <button
              onClick={() => isClickable && onStepClick(step.num)}
              disabled={!isClickable}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                isActive
                  ? 'bg-primary text-on-primary shadow-md'
                  : isCompleted
                  ? 'bg-primary-fixed text-on-primary-fixed cursor-pointer hover:bg-primary-fixed-dim'
                  : 'bg-surface-container text-on-surface-variant'
              } disabled:cursor-default`}
            >
              <span className="material-symbols-outlined text-[16px]">
                {isCompleted ? 'check_circle' : step.icon}
              </span>
              <span className="hidden sm:inline">{step.label}</span>
              <span className="sm:hidden">{step.num}</span>
            </button>
            {i < STEPS.length - 1 && (
              <div className={`w-4 h-0.5 mx-0.5 ${
                step.num < currentStep ? 'bg-primary' : 'bg-surface-container-highest'
              }`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/mockup/StepIndicator.tsx
git commit -m "feat(ui): add StepIndicator component for mockup pipeline"
```

---

## Task 10: Step1~6 컴포넌트 구현

**Files:**
- Create: `frontend/src/components/mockup/Step1AiGenerate.tsx`
- Create: `frontend/src/components/mockup/Step2Scaffold.tsx`
- Create: `frontend/src/components/mockup/Step3Annotate.tsx`
- Create: `frontend/src/components/mockup/Step4Interview.tsx`
- Create: `frontend/src/components/mockup/Step5InterviewResult.tsx`
- Create: `frontend/src/components/mockup/Step6SpecGenerate.tsx`
- Modify: `frontend/src/components/mockup/MockupPipeline.tsx`

- [ ] **Step 1: Create Step1AiGenerate.tsx**

```tsx
// frontend/src/components/mockup/Step1AiGenerate.tsx
import { useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

const PAGE_TYPES = [
  { value: 'list', label: '목록 (List)' },
  { value: 'list-detail', label: '목록+상세 (List-Detail)' },
  { value: 'edit', label: '입력/수정 (Edit)' },
  { value: 'tab-detail', label: '탭 상세 (Tab-Detail)' },
]

export default function Step1AiGenerate() {
  const [title, setTitle] = useState('')
  const [pageType, setPageType] = useState('list')
  const [description, setDescription] = useState('')

  const mockupAiGenerate = useSessionStore((s) => s.mockupAiGenerate)
  const mockupGoToStep = useSessionStore((s) => s.mockupGoToStep)
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)

  async function handleGenerate() {
    if (!title.trim()) return
    await mockupAiGenerate(title, pageType, description || undefined)
  }

  const hasResult = mockupState && mockupState.fields.length > 0

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">auto_awesome</span>
          AI 화면 설계
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-on-surface-variant mb-1">화면 제목 *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="예: 신고 관리, 교육 프로그램 목록"
              className="w-full px-4 py-3 rounded-xl border border-outline/20 bg-surface-container-lowest text-on-surface focus:ring-2 focus:ring-primary/30 focus:border-primary"
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-on-surface-variant mb-1">화면 유형</label>
            <div className="grid grid-cols-2 gap-2">
              {PAGE_TYPES.map((pt) => (
                <button
                  key={pt.value}
                  onClick={() => setPageType(pt.value)}
                  className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    pageType === pt.value
                      ? 'bg-primary text-on-primary'
                      : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'
                  }`}
                >
                  {pt.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-on-surface-variant mb-1">화면 설명 (선택)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="화면의 주요 기능이나 업무 요구사항을 간단히 설명하세요..."
              className="w-full px-4 py-3 rounded-xl border border-outline/20 bg-surface-container-lowest text-on-surface focus:ring-2 focus:ring-primary/30 min-h-[80px] resize-y"
              disabled={loading}
            />
          </div>
        </div>
        <button
          onClick={handleGenerate}
          disabled={!title.trim() || loading}
          className="gradient-button text-on-primary w-full px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {loading ? 'AI 설계 중...' : 'AI 설계 시작'}
          {!loading && <span className="material-symbols-outlined">auto_awesome</span>}
        </button>
        {error && <p className="text-error text-sm">{error}</p>}
      </div>

      {hasResult && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-3">
          <h4 className="font-bold text-on-surface">설계 결과</h4>
          <pre className="text-xs text-on-surface-variant bg-surface-container p-4 rounded-lg overflow-x-auto max-h-[300px]">
            {JSON.stringify(mockupState.fields, null, 2)}
          </pre>
          <button
            onClick={() => mockupGoToStep(2)}
            className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold w-full flex items-center justify-center gap-2"
          >
            다음: Mockup 생성
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create Step2Scaffold.tsx**

```tsx
// frontend/src/components/mockup/Step2Scaffold.tsx
import { useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

export default function Step2Scaffold() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const mockupScaffold = useSessionStore((s) => s.mockupScaffold)
  const mockupGoToStep = useSessionStore((s) => s.mockupGoToStep)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)

  const [screenId, setScreenId] = useState(mockupState?.screenId ?? '')

  if (!mockupState) return null

  async function handleScaffold() {
    await mockupScaffold(screenId || mockupState!.screenId, mockupState!.screenName, mockupState!.pageType, mockupState!.fields)
  }

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">code</span>
          Mockup 코드 생성
        </h3>
        <div>
          <label className="block text-sm font-medium text-on-surface-variant mb-1">화면 ID</label>
          <input
            type="text"
            value={screenId}
            onChange={(e) => setScreenId(e.target.value.replace(/[^A-Za-z0-9_]/g, ''))}
            placeholder="MNET010"
            className="w-full px-4 py-3 rounded-xl border border-outline/20 bg-surface-container-lowest text-on-surface"
          />
        </div>
        {!mockupState.vueCode && (
          <button
            onClick={handleScaffold}
            disabled={loading}
            className="gradient-button text-on-primary w-full px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? '생성 중...' : 'Vue 코드 생성'}
          </button>
        )}
        {error && <p className="text-error text-sm">{error}</p>}
      </div>

      {mockupState.vueCode && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-3">
          <h4 className="font-bold text-on-surface">생성된 Vue 코드</h4>
          <pre className="text-xs text-on-surface-variant bg-[#1e1e1e] text-[#d4d4d4] p-4 rounded-lg overflow-x-auto max-h-[400px]">
            {mockupState.vueCode}
          </pre>
          <button
            onClick={() => mockupGoToStep(3)}
            className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold w-full flex items-center justify-center gap-2"
          >
            다음: AI 주석 삽입
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Create Step3Annotate.tsx**

```tsx
// frontend/src/components/mockup/Step3Annotate.tsx
import { useSessionStore } from '../../store/sessionStore'

export default function Step3Annotate() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const mockupAiAnnotate = useSessionStore((s) => s.mockupAiAnnotate)
  const mockupGoToStep = useSessionStore((s) => s.mockupGoToStep)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)

  if (!mockupState) return null

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">comment</span>
          AI 주석 분석
        </h3>
        {!mockupState.annotationMarkdown && (
          <button
            onClick={mockupAiAnnotate}
            disabled={loading}
            className="gradient-button text-on-primary w-full px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? '분석 중...' : 'UI 주석 자동 삽입'}
          </button>
        )}
        {error && <p className="text-error text-sm">{error}</p>}
      </div>

      {mockupState.annotationMarkdown && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-3">
          <h4 className="font-bold text-on-surface">주석 분석 결과</h4>
          <pre className="text-xs text-on-surface-variant bg-surface-container p-4 rounded-lg overflow-x-auto max-h-[300px] whitespace-pre-wrap">
            {mockupState.annotationMarkdown}
          </pre>
          <button
            onClick={() => mockupGoToStep(4)}
            className="bg-primary text-on-primary px-6 py-3 rounded-xl font-bold w-full flex items-center justify-center gap-2"
          >
            다음: 인터뷰 질문 생성
            <span className="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create Step4Interview.tsx**

```tsx
// frontend/src/components/mockup/Step4Interview.tsx
import { useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

const PRIORITY_COLORS: Record<string, string> = {
  '높음': 'bg-error/10 text-error',
  '보통': 'bg-amber-500/10 text-amber-700',
  '낮음': 'bg-primary/10 text-primary',
}

export default function Step4Interview() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const mockupAiInterview = useSessionStore((s) => s.mockupAiInterview)
  const mockupSubmitInterviewResult = useSessionStore((s) => s.mockupSubmitInterviewResult)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)

  const [inputMode, setInputMode] = useState<'questions' | 'raw'>('questions')
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [rawText, setRawText] = useState('')

  if (!mockupState) return null

  const questions = mockupState.interviewQuestions

  function updateAnswer(no: number, value: string) {
    setAnswers((prev) => ({ ...prev, [no]: value }))
  }

  async function handleSubmit() {
    if (inputMode === 'raw') {
      if (!rawText.trim()) return
      await mockupSubmitInterviewResult(undefined, rawText)
    } else {
      if (!questions) return
      const answerList = questions.map((q) => ({
        no: q.no,
        answer: answers[q.no] || '',
      }))
      await mockupSubmitInterviewResult(answerList)
    }
  }

  const allAnswered = questions
    ? questions.every((q) => (answers[q.no] || '').trim())
    : false

  return (
    <div className="space-y-6">
      {/* Generate questions if not yet */}
      {!questions && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
          <h3 className="font-bold font-headline text-on-surface flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-primary">forum</span>
            인터뷰 질문 생성
          </h3>
          <button
            onClick={mockupAiInterview}
            disabled={loading}
            className="gradient-button text-on-primary w-full px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? '질문 생성 중...' : '인터뷰 질문 자동 생성'}
          </button>
          {error && <p className="text-error text-sm mt-2">{error}</p>}
        </div>
      )}

      {/* Questions generated - show input mode selector + questions/raw */}
      {questions && (
        <>
          <div className="flex justify-center">
            <div className="inline-flex bg-surface-container rounded-xl p-1 gap-1">
              <button
                onClick={() => setInputMode('questions')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  inputMode === 'questions' ? 'bg-secondary-container text-on-secondary-container' : 'text-on-surface-variant'
                }`}
              >
                질문별 답변
              </button>
              <button
                onClick={() => setInputMode('raw')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  inputMode === 'raw' ? 'bg-secondary-container text-on-secondary-container' : 'text-on-surface-variant'
                }`}
              >
                인터뷰 전문 붙여넣기
              </button>
            </div>
          </div>

          {inputMode === 'questions' ? (
            <div className="space-y-4">
              {questions.map((q) => (
                <div key={q.no} className="bg-surface-container-lowest rounded-xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-on-surface bg-surface-container px-2 py-0.5 rounded-md">Q{q.no}</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${PRIORITY_COLORS[q.priority] || ''}`}>{q.priority}</span>
                    <span className="text-xs text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-md">{q.category}</span>
                  </div>
                  <p className="text-sm text-on-surface font-medium">{q.question}</p>
                  {q.tip && <p className="text-xs text-on-surface-variant italic">{q.tip}</p>}
                  <textarea
                    value={answers[q.no] || ''}
                    onChange={(e) => updateAnswer(q.no, e.target.value)}
                    placeholder="답변을 입력하세요..."
                    className="w-full px-3 py-2 rounded-lg border border-outline/20 bg-surface-container-lowest text-on-surface text-sm min-h-[60px] resize-y"
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
              <h4 className="font-bold text-on-surface mb-3">인터뷰 전문 붙여넣기</h4>
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="인터뷰 회의록 전체를 붙여넣으세요..."
                className="w-full px-4 py-3 rounded-xl border border-outline/20 bg-surface-container-lowest text-on-surface min-h-[300px] resize-y"
              />
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={loading || (inputMode === 'questions' ? !allAnswered : !rawText.trim())}
            className="gradient-button text-on-primary w-full px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? '처리 중...' : '답변 완료 → Spec 생성'}
            {!loading && <span className="material-symbols-outlined">arrow_forward</span>}
          </button>
          {error && <p className="text-error text-sm">{error}</p>}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Create Step5InterviewResult.tsx**

```tsx
// frontend/src/components/mockup/Step5InterviewResult.tsx
import { useSessionStore } from '../../store/sessionStore'

export default function Step5InterviewResult() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const mockupGenerateSpec = useSessionStore((s) => s.mockupGenerateSpec)
  const loading = useSessionStore((s) => s.mockupLoading)

  if (!mockupState?.interviewNoteMd) return null

  return (
    <div className="space-y-6">
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-3">
        <h3 className="font-bold font-headline text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">summarize</span>
          인터뷰 결과 (InterviewNote)
        </h3>
        <pre className="text-sm text-on-surface-variant bg-surface-container p-4 rounded-lg overflow-x-auto max-h-[400px] whitespace-pre-wrap">
          {mockupState.interviewNoteMd}
        </pre>
      </div>

      <button
        onClick={mockupGenerateSpec}
        disabled={loading}
        className="gradient-button text-on-primary w-full px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 disabled:opacity-50"
      >
        {loading ? 'Spec 생성 중...' : '최종 Spec 생성 (스트리밍)'}
        <span className="material-symbols-outlined">description</span>
      </button>
    </div>
  )
}
```

- [ ] **Step 6: Create Step6SpecGenerate.tsx**

```tsx
// frontend/src/components/mockup/Step6SpecGenerate.tsx
import { useSessionStore } from '../../store/sessionStore'
import StreamingText from '../StreamingText'

export default function Step6SpecGenerate() {
  const specMarkdown = useSessionStore((s) => s.specMarkdown)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)

  if (!isGenerating && !specMarkdown) return null

  return (
    <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-3">
      <h3 className="font-bold font-headline text-on-surface flex items-center gap-2">
        <span className="material-symbols-outlined text-primary">description</span>
        Spec 생성
      </h3>
      {isGenerating && (
        <div className="flex items-center gap-3 text-sm text-secondary">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <StreamingText text={statusMessage ?? 'Generating spec...'} isStreaming />
        </div>
      )}
      {specMarkdown && !isGenerating && (
        <p className="text-sm text-primary font-bold">
          Spec 생성 완료! 왼쪽 패널에서 확인하세요.
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 7: Update MockupPipeline.tsx with all steps**

```tsx
// frontend/src/components/mockup/MockupPipeline.tsx
import { useSessionStore } from '../../store/sessionStore'
import StepIndicator from './StepIndicator'
import Step1AiGenerate from './Step1AiGenerate'
import Step2Scaffold from './Step2Scaffold'
import Step3Annotate from './Step3Annotate'
import Step4Interview from './Step4Interview'
import Step5InterviewResult from './Step5InterviewResult'
import Step6SpecGenerate from './Step6SpecGenerate'

export default function MockupPipeline() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const mockupGoToStep = useSessionStore((s) => s.mockupGoToStep)

  const currentStep = mockupState?.currentStep ?? 1

  function renderStep() {
    switch (currentStep) {
      case 1: return <Step1AiGenerate />
      case 2: return <Step2Scaffold />
      case 3: return <Step3Annotate />
      case 4: return <Step4Interview />
      case 5: return <Step5InterviewResult />
      case 6: return <Step6SpecGenerate />
      default: return <Step1AiGenerate />
    }
  }

  return (
    <div className="max-w-[768px] mx-auto space-y-6">
      <div className="flex flex-col items-center text-center space-y-3 mb-4">
        <h1 className="text-[3.5rem] leading-tight font-extrabold font-headline tracking-tighter text-on-background">
          Mockup
        </h1>
        <p className="text-secondary max-w-md">
          AI가 화면을 설계하고, 인터뷰 질문으로 요구사항을 확정합니다.
        </p>
      </div>

      <StepIndicator
        currentStep={currentStep}
        onStepClick={(step) => mockupGoToStep(step)}
      />

      {renderStep()}
    </div>
  )
}
```

- [ ] **Step 8: Verify dev server renders mockup pipeline**

Run: `cd frontend && npm run dev`
"Mockup 생성" 탭 선택 → 6단계 스텝퍼 + Step1 입력 폼이 렌더링되는지 확인.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/mockup/
git commit -m "feat(ui): implement 6-step mockup pipeline components"
```

---

## Task 11: 통합 테스트 및 기존 기능 회귀 확인

**Files:** None (테스트만)

- [ ] **Step 1: Backend 전체 테스트 실행**

Run: `cd backend && python -m pytest -v`
Expected: 기존 37개 테스트 + 신규 테스트 모두 PASS

- [ ] **Step 2: Frontend 빌드 확인**

Run: `cd frontend && npm run build`
Expected: 빌드 성공, 타입 에러 없음

- [ ] **Step 3: E2E 수동 테스트 — 탭1 (텍스트 입력)**

1. `./start.sh`로 백엔드+프론트엔드 기동
2. 브라우저에서 "텍스트 입력" 탭 선택
3. 텍스트 붙여넣기 → "Generate Spec" → spec 생성 확인
4. ChatPanel 리파인 → CodeGenPanel 코드 생성 확인

Expected: 기존 동작과 동일

- [ ] **Step 4: E2E 수동 테스트 — 탭2 (Mockup 생성)**

1. "Mockup 생성" 탭 선택
2. Step1: 화면 제목 "교육 프로그램 관리" 입력 → AI 설계 시작
3. Step2: Vue 코드 생성 확인
4. Step3: AI 주석 삽입 확인
5. Step4: 인터뷰 질문 10개 생성 확인 → 답변 입력 → 제출
6. Step5: InterviewNote 결과 확인
7. Step6: Spec 생성 → SpecViewer에서 확인
8. ChatPanel → CodeGenPanel 연결 확인

- [ ] **Step 5: Commit all remaining changes**

```bash
git add -A
git commit -m "feat: complete dual spec pipeline integration"
```

---

## Task 12: masterPrompt.md 파일 복사

**Files:**
- Copy: `pfy-front/RequirementPrompt/masterPrompt.md` → `pfy_prompt/masterPrompt.md`

- [ ] **Step 1: Copy masterPrompt.md from pfy-front branch**

```bash
git show feat/pfy-front-scaffolding:pfy-front/RequirementPrompt/masterPrompt.md > pfy_prompt/masterPrompt.md
```

- [ ] **Step 2: Verify file exists**

Run: `ls -la pfy_prompt/masterPrompt.md`
Expected: 파일 존재, 내용 있음

- [ ] **Step 3: Commit**

```bash
git add pfy_prompt/masterPrompt.md
git commit -m "feat: add masterPrompt.md for mockup-based spec generation"
```
