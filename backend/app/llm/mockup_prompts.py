"""
mockup_prompts.py — Python port of pfy-front scaffolding server prompts.

Each function returns tuple[str, str] → (system_prompt, user_prompt),
matching the same pattern as prompts.py.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# 1. ai_generate_prompt
#    Port of: pfy-front/scaffolding/src/routes/ai-generate.ts  buildPrompt()
# ─────────────────────────────────────────────────────────────────────────────

def ai_generate_prompt(
    page_type: str,
    title: str,
    description: str | None = None,
) -> tuple[str, str]:
    """
    Build prompts for mockup UI structure generation.

    Args:
        page_type:   "list" or "form"
        title:       screen title (화면 제목)
        description: optional screen description

    Returns:
        (system_prompt, user_prompt)
    """
    system = "당신은 엔터프라이즈 UI 설계 전문가입니다. 요청한 JSON 형식으로만 답변합니다."

    desc_line = f"\n화면 설명: {description.strip()}" if description and description.strip() else ""

    if page_type in ("list", "list-detail", "tab-detail"):
        user = (
            f"당신은 한국 엔터프라이즈 UI를 설계하는 시니어 개발자 및 DB 아키텍트입니다.\n"
            f"아래 화면 정보를 보고 목록(List) 화면 설계 정보를 응답하세요.\n\n"
            f"화면 제목: {title}{desc_line}\n\n"
            f"반드시 아래 JSON 형식으로만 응답하세요 (코드블록, 설명 없이):\n"
            f"{{\n"
            f'  "domain": "화면의도메인명(영문)",\n'
            f'  "searchFields": [\n'
            f'    {{\n'
            f'      "key": "camelCase영문키",\n'
            f'      "label": "한글레이블",\n'
            f'      "type": "text|number|date|daterange|select|checkbox",\n'
            f'      "optionsText": "select일 때만 포함",\n'
            f'      "operator": "EQ|LIKE|BETWEEN|IN"\n'
            f'    }}\n'
            f'  ],\n'
            f'  "tableColumns": [\n'
            f'    {{\n'
            f'      "key": "camelCase영문키",\n'
            f'      "label": "한글헤더명",\n'
            f'      "dataType": "VARCHAR|NUMBER|DATETIME",\n'
            f'      "dataLength": "길이",\n'
            f'      "align": "left|center|right"\n'
            f'    }}\n'
            f'  ],\n'
            f'  "mockRows": [\n'
            f'    {{ "tableColumns의key1": "현실적인샘플값", "tableColumns의key2": "현실적인샘플값" }}\n'
            f'  ]\n'
            f'}}\n\n'
            f"규칙:\n"
            f"- searchFields: 3~5개, 실제 업무에서 자주 쓰이는 조회 조건\n"
            f"- tableColumns: 5~8개 (No 컬럼 제외), 목록에 표시할 주요 정보\n"
            f"- key는 반드시 영문 camelCase (한글·공백·특수문자 금지), 실제 DB 컬럼명으로 활용 가능하도록 의미 있게 작성\n"
            f"- operator: text는 주로 LIKE, number/date 단일값은 EQ, 범위는 BETWEEN, select/checkbox는 IN 또는 EQ\n"
            f"- type 중 daterange는 날짜 범위 조회, checkbox는 Y/N 조회에 사용\n"
            f"- type이 select인 경우 반드시 optionsText 필드를 포함하고, 값은 \"코드1:라벨1, 코드2:라벨2\" 형식으로 작성 (예: \"Y:사용, N:미사용\")\n"
            f"- type이 select가 아닌 경우 optionsText 필드는 생략\n"
            f"- dataType: 데이터의 성격에 맞는 표준 SQL 타입을 지정 (VARCHAR, NUMBER, DATETIME 등)\n"
            f"- dataLength: VARCHAR는 길이(예: \"100\"), NUMBER는 정밀도(예: \"10,2\"), DATETIME은 생략 가능\n"
            f"- align: 텍스트·코드는 left, 숫자·금액은 right, 날짜·상태는 center\n"
            f"- mockRows: 10건, tableColumns의 key와 정확히 일치하는 key로 구성, 한국어 실제 업무 데이터처럼 현실적으로 작성\n"
            f"- 날짜 값은 \"2025-01-15\" 형식, 숫자는 숫자형 문자열, select는 optionsText에 있는 코드값 사용"
        )
    else:
        # form
        user = (
            f"당신은 한국 엔터프라이즈 UI를 설계하는 시니어 개발자입니다.\n"
            f"아래 화면 정보를 보고 입력/수정(Form) 화면 설계 정보를 응답하세요.\n\n"
            f"화면 제목: {title}{desc_line}\n\n"
            f"반드시 아래 JSON 형식으로만 응답하세요 (코드블록, 설명 없이):\n"
            f"{{\n"
            f'  "formFields": [\n'
            f'    {{\n'
            f'      "key": "camelCase영문키",\n'
            f'      "label": "한글레이블",\n'
            f'      "type": "text|number|date|select|textarea|checkbox",\n'
            f'      "required": true,\n'
            f'      "optionsText": "select일 때만 포함",\n'
            f'      "validation": {{\n'
            f'        "min": "최소값/최소길이",\n'
            f'        "max": "최대값/최대길이",\n'
            f'        "pattern": "정규표현식(필요시)"\n'
            f'      }},\n'
            f'      "description": "필드에 대한 비즈니스 설명(Spec 기재용)"\n'
            f'    }}\n'
            f'  ]\n'
            f'}}\n\n'
            f"규칙:\n"
            f"- formFields: 5~10개, 실제 업무에서 입력하는 항목\n"
            f"- key는 반드시 영문 camelCase (한글·공백·특수문자 금지), API Request Body의 Key로 직접 사용됨\n"
            f"- required: 필수 입력 여부 (true/false)\n"
            f"- textarea는 긴 텍스트(내용, 메모 등), checkbox는 Y/N 값에 사용\n"
            f"- type이 select인 경우 반드시 optionsText 필드를 포함하고, 값은 \"코드1:라벨1, 코드2:라벨2\" 형식으로 작성 (예: \"1:남성, 2:여성\" 또는 \"ACTIVE:활성, INACTIVE:비활성\")\n"
            f"- type이 select가 아닌 경우 optionsText 필드는 생략\n"
            f"- validation: 실제 업무 규칙을 고려하여 현실적인 숫자나 길이를 제안 (불필요한 항목은 생략 가능)\n"
            f"- description: 이 필드가 비즈니스 로직상 어떤 의미를 갖는지 간략히 서술"
        )

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# 2. annotation_prompt
#    Port of: pfy-front/scaffolding/src/routes/ai-annotate.ts
#             ANNOTATION_SYSTEM_PROMPT + template section as user content
# ─────────────────────────────────────────────────────────────────────────────

def annotation_prompt(template_section: str) -> tuple[str, str]:
    """
    Build prompts for annotating a Vue <template> section.

    Args:
        template_section: the extracted <template>...</template> block

    Returns:
        (system_prompt, user_prompt)
    """
    system = (
        "당신은 Vue.js <template>을 분석하여 각 UI 요소에 대한 구조화된 주석 정보를 JSON 배열로 반환하는 분석가입니다.\n\n"
        "[출력 형식 (STRICT)]\n"
        "반드시 아래 JSON 배열만 반환하세요. 다른 텍스트 없이:\n"
        "[\n"
        "  {\n"
        '    "selector": "엘리먼트를 식별할 수 있는 코드 스니펫 (태그+주요속성, 15자 이내)",\n'
        '    "id": "kebab-case 고유 ID",\n'
        '    "type": "input | action | display | container",\n'
        '    "summary": "요소 설명 (20자 이내)",\n'
        '    "note": "동작 또는 정책 (30자 이내)",\n'
        '    "model": "v-model 값 또는 null",\n'
        '    "constraints": "이 요소의 업무 제약사항 (50자 이내) 또는 null"\n'
        "  }\n"
        "]\n\n"
        "[규칙]\n"
        '- selector는 해당 요소를 특정할 수 있는 짧은 코드 스니펫 (예: "<button @click=\\"onSearch\\"", "<input v-model=\\"search.name\\"")\n'
        "- 주요 UI 요소(버튼, 인풋, 셀렉트, 테이블, 주요 div)만 포함 (최대 20개)\n"
        "- constraints는 코드에서 파악 가능한 유효성 검사/허용 범위/필수 여부 등 제약사항. 파악 불가 시 null\n"
        "- JSON만 출력, Markdown 코드블럭 금지"
    )

    user = template_section

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# 3. interview_prompt
#    Port of: pfy-front/scaffolding/src/routes/ai-interview-questions.ts
#             buildPromptFromAnnotation() / buildPromptFromSpec()
# ─────────────────────────────────────────────────────────────────────────────

_INTERVIEW_ROLE_CONTEXT = """\
# Role
당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다.
제공된 [MockUp 코드]와 [컴포넌트 주석 테이블]을 분석하여, 설계 확정을 위한 핵심 인터뷰 질문 10개를 생성해 주세요.

# Context
이 인터뷰의 목적은 목업 단계의 가설을 확정하여 Back-End API 설계서와 DB 정의서를 포함한 Spec.md를 도출하기 위함입니다.
따라서 질문은 매우 구체적이고 기술적 의사결정을 포함해야 합니다.

# Question Generation Rules
1. 데이터 스펙 확정: 각 필드의 타입, 길이, 필수 여부를 확인하는 질문 포함.
2. 검색 및 정렬 로직: 검색 시 일치 조건(Like vs Equal)과 기본 정렬 순서 확인.
3. 비즈니스 예외 케이스: 데이터가 없거나, 권한이 없거나, 서버 오류 시의 사용자 경험 확인.
4. 연동 및 출력: 엑셀 다운로드 범위, 타 시스템 연동 데이터 등에 대한 질문.
5. 어조: 전문적이면서도 현업이 이해하기 쉬운 비즈니스 용어 사용.\
"""

_QUESTION_OUTPUT_FORMAT = """\
# Output Format
반드시 아래 JSON 형식으로만 응답하세요 (코드블록·설명 문장 없이 순수 JSON만):
{
  "questions": [
    {
      "category": "조회조건|데이터정의|사용자행동|권한|예외처리 중 하나",
      "question": "인터뷰 시 그대로 읽을 수 있는 구체적인 질문 (보충 질문 포함)",
      "priority": "높음|보통|낮음 중 하나",
      "tip": "현재 목업은 ~로 설계되어 있습니다. 이대로 진행해도 될까요? 형태의 설계 가설 (1~2문장)"
    }
  ]
}

규칙:
- questions 배열 길이는 정확히 10
- category는 조회조건 / 데이터정의 / 사용자행동 / 권한 / 예외처리 중 하나
- question은 예/아니오만으로 끝나는 질문은 반드시 보충 질문을 포함
- priority는 반드시 "높음" | "보통" | "낮음" 중 하나 (업무 영향도·구현 의존성 기준)
- tip은 목업 현황을 근거로 한 설계 가설 문장\
"""


def interview_prompt(
    title: str,
    annotation_markdown: str | None = None,
    vue_source: str | None = None,
    spec_json: dict | None = None,
) -> tuple[str, str]:
    """
    Build prompts for generating 10 interview questions about a mockup screen.

    Priority: uses annotation_markdown if provided; falls back to spec_json.

    Args:
        title:               screen title
        annotation_markdown: component annotation table markdown (preferred)
        vue_source:          Vue SFC source code (optional supplement)
        spec_json:           screen spec dict (fallback when no annotation_markdown)

    Returns:
        (system_prompt, user_prompt)
    """
    system = (
        "당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다. "
        "지정한 JSON 스키마로만 답하고, questions는 반드시 10개입니다."
    )

    source_section = ""
    if vue_source and vue_source.strip():
        source_section = (
            f"\n\n--- MockUp 소스 코드 시작 ---\n```vue\n{vue_source}\n```\n--- MockUp 소스 코드 끝 ---"
        )

    if annotation_markdown and annotation_markdown.strip():
        user = (
            f"{_INTERVIEW_ROLE_CONTEXT}\n\n"
            f'아래는 "{title}" 화면에 대해 자동 생성된 컴포넌트 주석 테이블입니다.\n'
            f"이 주석에 명시된 기능·로직·업무 규칙·예외 처리 내용을 검토하여, 아직 정의되지 않았거나 모호해 보이는 지점을 찾아 "
            f"고객/현업에게 물어볼 인터뷰 질문을 정확히 10개 작성해 주세요.\n\n"
            f"--- 컴포넌트 주석 테이블 시작 ---\n"
            f"{annotation_markdown}\n"
            f"--- 컴포넌트 주석 테이블 끝 ---"
            f"{source_section}\n\n"
            f"{_QUESTION_OUTPUT_FORMAT}"
        )
    else:
        spec = spec_json or {}
        spec_text = json.dumps(spec, ensure_ascii=False, indent=2)
        user = (
            f"{_INTERVIEW_ROLE_CONTEXT}\n\n"
            f'아래는 MockUp Builder에서 정의된 "{title}" 화면 스펙(JSON)입니다.\n'
            f"이 화면만 보고 아직 정의되지 않았거나 모호해 보이는 지점을 찾아, "
            f"고객/현업에게 물어볼 인터뷰 질문을 정확히 10개 작성해 주세요.\n\n"
            f"--- 화면 스펙 시작 ---\n"
            f"{spec_text}\n"
            f"--- 화면 스펙 끝 ---"
            f"{source_section}\n\n"
            f"{_QUESTION_OUTPUT_FORMAT}"
        )

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# 4. interview_notes_prompt
#    Port of: pfy-front/scaffolding/src/routes/interview-result.ts
#             generateInterviewNotes() prompt
# ─────────────────────────────────────────────────────────────────────────────

def interview_notes_prompt(
    title: str,
    questions_answers: list[dict],
    *,
    screen_name: str = "",
    custom_qas: list[dict] | None = None,
    raw_interview_text: str | None = None,
    interview_notes_template: str = "",
) -> tuple[str, str]:
    """
    Build prompts to generate InterviewNote.md from Q&A results.

    Args:
        title:                   screen title
        questions_answers:       list of {no, category, question, priority, tip, answer}
        screen_name:             screen code name (for ID generation)
        custom_qas:              list of {question, answer} for ad-hoc questions
        raw_interview_text:      raw interview transcript (alternative to Q&A)
        interview_notes_template: contents of InterviewNote.md template file

    Returns:
        (system_prompt, user_prompt)
    """
    system = (
        "당신은 InterviewNote 템플릿을 정확히 채우는 BA 전문가입니다. "
        "템플릿 구조를 절대 변경하지 마세요. 섹션 순서와 마크다운 포맷을 100% 유지하세요."
    )

    from datetime import date as _date

    today = _date.today().isoformat()
    screen_id = f"SCR_{screen_name.upper()}_001" if screen_name else f"SCR_{title[:10].upper()}_001"

    if raw_interview_text and raw_interview_text.strip():
        qa_label = "인터뷰 전문(Raw Text)"
        qa_text = raw_interview_text.strip()
    else:
        qa_label = "인터뷰 Q&A 데이터"
        qa_lines = []
        for q in questions_answers:
            no       = q.get("no", "")
            category = q.get("category", "")
            priority = q.get("priority", "")
            question = q.get("question", "")
            tip      = q.get("tip") or "없음"
            answer   = q.get("answer", "")
            qa_lines.append(
                f"Q{no} [{category}/{priority}]: {question}\n"
                f"  설계가설: {tip}\n"
                f"  답변: {answer}"
            )
        qa_text = "\n\n".join(qa_lines)

    custom_text = ""
    if custom_qas:
        lines = []
        for i, qa in enumerate(custom_qas):
            q_text = qa.get("question") or "(질문 없음)"
            a_text = qa.get("answer") or "(미작성)"
            lines.append(f"추가{i + 1}: {q_text}\n  답변: {a_text}")
        custom_text = "\n\n[현장 추가 질문]\n" + "\n\n".join(lines)

    user = (
        f"당신은 엔터프라이즈 시스템 전문 IT 비즈니스 분석가(BA)입니다.\n\n"
        f"아래 [{qa_label}]를 분석하여, 주어진 [InterviewNote 템플릿]을 정확히 채워주세요.\n\n"
        f"규칙 (TEMPLATE LOCK — 절대 준수):\n"
        f"- 템플릿 섹션 구조·순서·마크다운 포맷을 절대 변경하지 마세요.\n"
        f"- 각 답변을 분류 기준(Keep/Change/Add/Out of Scope/TBD)에 따라 정확히 배치하세요.\n"
        f"- 모든 항목에 고유한 @id를 부여하세요 (KEEP-001, CHG-001, ADD-001, OUT-001, TBD-001 형식).\n"
        f"- DataSpec에는 해당 화면의 필드별 기술 명세를 포함하세요.\n"
        f"- BusinessRules에는 정렬/페이징/권한/유효성 규칙을 포함하세요.\n"
        f"- API Specification에는 인터뷰 결과로 도출되는 API 엔드포인트 목록을 작성하세요:\n"
        f"  - @id는 API-001 형식, method는 GET/POST/PUT/PATCH/DELETE 중 하나.\n"
        f"  - requestParams는 \"파라미터명(타입, operator)\" 형식으로 나열.\n"
        f"  - responseFields는 \"필드명(타입)\" 형식으로 나열.\n"
        f"  - relatedIds는 관련된 Keep/Change/Add/TBD @id를 쉼표로 나열.\n"
        f"  - 화면 유형에 따라 필요한 모든 API를 빠짐없이 도출하세요 (목록조회, 상세조회, 등록, 수정, 삭제, 코드조회 등).\n"
        f"- 빈 섹션에는 해당 없음 행을 채우세요.\n"
        f"- 자유 서술 최소화, 반드시 구조화된 값을 사용하세요.\n\n"
        f"[화면 정보]\n"
        f"- 화면명: {title}\n"
        f"- 화면 ID: {screen_id}\n"
        f"- 인터뷰 일자: {today}\n\n"
        f"[{qa_label}]\n{qa_text}{custom_text}\n\n"
        f"[InterviewNote 템플릿]\n{interview_notes_template}\n\n"
        f"위 템플릿 구조를 100% 유지하면서, 인터뷰 데이터를 바탕으로 모든 섹션을 채워 완성된 InterviewNote.md를 출력하세요."
    )

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# 5. extract_structured_data_prompt
#    Port of: pfy-front/scaffolding/src/routes/interview-result.ts
#             extractStructuredDataFromRawText() prompt
# ─────────────────────────────────────────────────────────────────────────────

def extract_structured_data_prompt(
    raw_text: str,
    title: str = "",
) -> tuple[str, str]:
    """
    Build prompts to extract keep/change/add/tbd from raw interview transcript.

    Args:
        raw_text: raw interview transcript
        title:    screen title (for context)

    Returns:
        (system_prompt, user_prompt)
    """
    system = (
        "인터뷰 내용을 Keep/Change/Add/TBD로 분류하는 BA 전문가입니다. "
        "JSON 객체만 반환하고 마크다운 코드블럭을 사용하지 마세요."
    )

    title_line = f"[화면 정보] 화면명: {title}\n\n" if title else ""

    user = (
        f"아래 [인터뷰 전문]을 분석하여, 각 답변을 Keep/Change/Add/TBD 카테고리로 분류하고 JSON으로만 반환하세요.\n\n"
        f"{title_line}"
        f"[분류 기준]\n"
        f"- Keep   : 현행 설계/정책을 그대로 유지하거나 확정된 내용\n"
        f"- Change : 현행 대비 수정/변경이 필요하다고 확인된 내용\n"
        f"- Add    : 신규로 추가해야 할 기능/규칙/요구사항\n"
        f"- TBD    : 미결정 또는 추가 확인이 필요한 내용\n\n"
        f"[출력 형식 — 다른 텍스트 없이 JSON 객체만]\n"
        f"{{\n"
        f'  "keep":   [{{"id":"KEEP-001","name":"요약명(30자 이내)","detail":"상세 내용"}}],\n'
        f'  "change": [{{"id":"CHG-001","name":"요약명","asIs":"변경 전","toBe":"변경 후","rule":"관련 규칙"}}],\n'
        f'  "add":    [{{"id":"ADD-001","name":"요약명","detail":"상세 내용"}}],\n'
        f'  "tbd":    [{{"id":"TBD-001","name":"요약명","reason":"미결 사유"}}]\n'
        f"}}\n\n"
        f"[인터뷰 전문]\n{raw_text}"
    )

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# 6. merge_annotations_prompt
#    Port of: pfy-front/scaffolding/src/routes/interview-result.ts
#             matchAndMergeIntoAnnotations() LLM call
# ─────────────────────────────────────────────────────────────────────────────

def merge_annotations_prompt(
    annotation_markdown: str,
    interview_data: dict,
) -> tuple[str, str]:
    """
    Build prompts to merge interview results into Vue component annotations.

    Takes the annotation list (as markdown or @id summary lines) and structured
    interview data (keep/change/add/tbd) and produces a JSON object mapping
    @id → updated constraints string.

    Args:
        annotation_markdown: string listing "@id: summary / note" entries,
                             or a full markdown annotation table
        interview_data:      dict with keys keep, change, add, tbd (each a list)

    Returns:
        (system_prompt, user_prompt)
    """
    system = (
        "UI 요소 주석에 업무 제약사항을 채우는 BA 전문가입니다. "
        "JSON 객체만 반환하고 마크다운 코드블럭을 사용하지 마세요."
    )

    # Build interview context string from structured data
    lines: list[str] = []

    keep   = interview_data.get("keep", [])
    change = interview_data.get("change", [])
    add    = interview_data.get("add", [])
    tbd    = interview_data.get("tbd", [])

    if keep:
        lines.append("[KEEP — 유지/확정 사항]")
        for k in keep:
            lines.append(f"  {k.get('id','')} ({k.get('name','')}): {k.get('detail','')}")
    if change:
        lines.append("[CHANGE — 변경 사항]")
        for c in change:
            lines.append(
                f"  {c.get('id','')} ({c.get('name','')}): "
                f"{c.get('asIs','')} → {c.get('toBe','')} (규칙: {c.get('rule','')})"
            )
    if add:
        lines.append("[ADD — 신규 추가 사항]")
        for a in add:
            lines.append(f"  {a.get('id','')} ({a.get('name','')}): {a.get('detail','')}")
    if tbd:
        lines.append("[TBD — 미결 사항]")
        for t in tbd:
            lines.append(f"  {t.get('id','')} ({t.get('name','')}): 미결 사유: {t.get('reason','')}")

    interview_context = "\n".join(lines)
    title = interview_data.get("title", "")

    user = (
        f"당신은 엔터프라이즈 시스템 BA 전문가입니다.\n\n"
        f"아래 [인터뷰 결과]를 분석하여, [UI 요소 목록]의 각 @id에 적용되는 업무 제약사항(constraints)을 도출해 주세요.\n\n"
        f"[화면 정보] 화면명: {title}\n\n"
        f"[인터뷰 결과]\n{interview_context}\n\n"
        f"[UI 요소 목록 (@id: \"summary / note\")]\n{annotation_markdown}\n\n"
        f"[출력 규칙]\n"
        f"- 각 @id에 직접 적용되는 인터뷰 기반 제약사항만 작성 (예: 필수 입력, 검색 방식, 허용 범위, 권한 조건 등)\n"
        f"- 해당하는 인터뷰 ID(KEEP-001 등)를 괄호 안에 병기\n"
        f"- 제약사항이 없는 @id는 null\n"
        f"- 한 줄 요약, 100자 이내\n"
        f"- 다른 텍스트 없이 아래 JSON 객체만 반환:\n\n"
        f'{{\n  "@id-값": "제약사항 문구 [KEEP-001, CHG-001]",\n  "@id-값2": null\n}}'
    )

    return system, user


# ─────────────────────────────────────────────────────────────────────────────
# 7. master_spec_prompt
#    Port of: pfy-front/RequirementPrompt/masterPrompt.md as system prompt
#    Loads masterPrompt.md from settings.PROMPT_REFERENCE_DIR
# ─────────────────────────────────────────────────────────────────────────────

_MASTER_PROMPT_CACHE: str | None = None


def _load_master_prompt() -> str:
    global _MASTER_PROMPT_CACHE
    if _MASTER_PROMPT_CACHE is not None:
        return _MASTER_PROMPT_CACHE

    path = Path(settings.PROMPT_REFERENCE_DIR) / "masterPrompt.md"
    if path.exists():
        _MASTER_PROMPT_CACHE = path.read_text(encoding="utf-8")
    else:
        _MASTER_PROMPT_CACHE = ""

    return _MASTER_PROMPT_CACHE


def master_spec_prompt(
    title: str,
    annotation_markdown: str,
    interview_note_md: str,
    vue_source: str | None = None,
) -> tuple[str, str]:
    """
    Build prompts to generate the final spec.md from mockup + interview data.

    Uses masterPrompt.md as system prompt (loaded from PROMPT_REFERENCE_DIR).

    Args:
        title:               screen title
        annotation_markdown: component annotation table markdown
        interview_note_md:   InterviewNote.md content
        vue_source:          Vue SFC source (optional, for deeper analysis)

    Returns:
        (system_prompt, user_prompt)
    """
    system = _load_master_prompt()

    vue_section = ""
    if vue_source and vue_source.strip():
        vue_section = (
            f"\n\n## [2] Mockup 화면 (Mockup.vue 핵심 구조)\n\n"
            f"```vue\n{vue_source}\n```"
        )

    annotation_section = ""
    if annotation_markdown and annotation_markdown.strip():
        annotation_section = (
            f"\n\n## [3] 컴포넌트 주석 테이블 (Annotation)\n\n"
            f"{annotation_markdown}"
        )

    user = (
        f"# 화면 정보\n\n"
        f"- 화면명: {title}\n\n"
        f"## [1] 인터뷰 회의록 (InterviewNote.md)\n\n"
        f"{interview_note_md}"
        f"{vue_section}"
        f"{annotation_section}\n\n"
        f"위 데이터를 바탕으로 spec.md를 생성해 주세요."
    )

    return system, user
