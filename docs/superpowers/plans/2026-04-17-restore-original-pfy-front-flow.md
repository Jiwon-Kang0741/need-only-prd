# 원본 pfy-front 플로우 복원 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 현재 6단계 Mockup 파이프라인을 원본 pfy-front의 4단계 플로우(Brief→Mockup→Interview→Spec)로 완전 대체하고, Mockup 생성 LLM은 원본 사내 AOAI 게이트웨이(gpt-5.2)를 전용 클라이언트로 호출한다.

**Architecture:** 백엔드에 신규 `MockupLLMClient`(httpx 기반)를 추가하여 `/api/mockup/*` 엔드포인트 5개를 재정의. 프론트엔드는 4개의 Step 컴포넌트로 교체. LLM이 Vue SFC를 생성하므로 `vue_generator.py`는 삭제.

**Tech Stack:** FastAPI, httpx, Python 3.11+, React 19, TypeScript, Zustand, Vite

**Design Doc:** `docs/superpowers/specs/2026-04-17-restore-original-pfy-front-flow-design.md`

---

## File Structure

### Backend (신규/수정)
- `backend/app/config.py` — MOCKUP_AOAI_* 환경변수 추가
- `backend/app/llm/mockup_client.py` (신규) — 원본 사내 게이트웨이 호환 클라이언트
- `backend/app/llm/mockup_prompts.py` (완전 대체) — brief/mockupPrompt/InterviewParser/master 프롬프트
- `backend/app/llm/mockup_pipeline.py` (완전 대체) — 4단계 오케스트레이션
- `backend/app/routers/mockup.py` (완전 대체) — 5개 엔드포인트
- `backend/app/models.py` — MockupState 재정의, FieldOption/FieldDef/TabDef 제거
- `backend/tests/test_mockup_client.py` (신규)
- `backend/tests/test_mockup_models.py` (재작성)
- `backend/tests/test_mockup_pipeline.py` (신규)
- `backend/tests/test_mockup_router.py` (신규)

### Backend (삭제)
- `backend/app/llm/vue_generator.py`
- `backend/tests/test_vue_generator.py`

### 원본 리소스 복사 → `pfy_prompt/`
- `brief.md`
- `mockupPrompt.md`
- `InterviewParser.md`
- `componentCatalog.md` (일회성 스크립트로 생성)

### Frontend (신규)
- `frontend/src/components/mockup/Step1Brief.tsx`
- `frontend/src/components/mockup/Step2Mockup.tsx`
- `frontend/src/components/mockup/Step3Interview.tsx`
- `frontend/src/components/mockup/Step4SpecGenerate.tsx`

### Frontend (수정)
- `frontend/src/types/index.ts` — Mockup 타입 재정의
- `frontend/src/api/client.ts` — Mockup API 함수 재정의
- `frontend/src/store/sessionStore.ts` — Mockup 액션 재정의
- `frontend/src/components/mockup/MockupPipeline.tsx` — 4단계
- `frontend/src/components/mockup/StepIndicator.tsx` — 4단계 라벨

### Frontend (삭제)
- `frontend/src/components/mockup/Step1AiGenerate.tsx`
- `frontend/src/components/mockup/Step2Scaffold.tsx`
- `frontend/src/components/mockup/Step3Annotate.tsx`
- `frontend/src/components/mockup/Step4Interview.tsx`
- `frontend/src/components/mockup/Step5InterviewResult.tsx`
- `frontend/src/components/mockup/Step6SpecGenerate.tsx`

### 기타
- `.env.example` — MOCKUP_AOAI_* 추가
- `backend/scripts/build_component_catalog.py` (신규, 일회성)

---

## Task 1: Config 확장 + env.example

**Files:**
- Modify: `backend/app/config.py`
- Modify: `.env.example`

- [ ] **Step 1: config.py에 MOCKUP_AOAI_* 필드 추가**

Open `backend/app/config.py`. Find the `Settings` class. Add these fields after the existing `CODEX_AZURE_OPENAI_*` fields:

```python
    # --- Mockup Pipeline 전용 (원본 pfy-front 사내 게이트웨이 호환) ---
    MOCKUP_AOAI_ENDPOINT: str = ""
    MOCKUP_AOAI_API_KEY: str = ""
    MOCKUP_AOAI_DEPLOYMENT: str = "gpt-5.2"
    MOCKUP_AOAI_MAX_TOKENS: int = 8000
```

- [ ] **Step 2: .env.example에 관련 변수 추가**

Open `.env.example`. Append at the end:

```env

# --- Mockup Pipeline 전용 (원본 pfy-front 사내 AOAI 게이트웨이) ---
# 설정하지 않으면 Mockup 탭 사용 시 에러 메시지가 표시됩니다.
MOCKUP_AOAI_ENDPOINT=https://ito-ax.apps.dev.honecloud.co.kr/api/hub/v1/models/gpt-5.2/invoke
MOCKUP_AOAI_API_KEY=your-mockup-api-key
MOCKUP_AOAI_DEPLOYMENT=gpt-5.2
MOCKUP_AOAI_MAX_TOKENS=8000
```

- [ ] **Step 3: 검증**

Run: `cd backend && source .venv/bin/activate && python -c "from app.config import settings; print(settings.MOCKUP_AOAI_DEPLOYMENT)"`
Expected: `gpt-5.2`

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py .env.example
git commit -m "feat(config): add MOCKUP_AOAI_* settings for original pfy-front gateway"
```

---

## Task 2: MockupLLMClient 신규

**Files:**
- Create: `backend/app/llm/mockup_client.py`
- Create: `backend/tests/test_mockup_client.py`

- [ ] **Step 1: 테스트 작성 (구조만 검증, 실제 네트워크 호출 없음)**

Create `backend/tests/test_mockup_client.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from app.llm.mockup_client import MockupLLMClient


def test_client_reads_config():
    client = MockupLLMClient()
    # settings에서 읽은 값이 반영되는지만 확인
    assert hasattr(client, "_endpoint")
    assert hasattr(client, "_api_key")
    assert hasattr(client, "_model")


@pytest.mark.asyncio
async def test_complete_non_streaming_raises_without_config():
    client = MockupLLMClient()
    client._endpoint = ""
    client._api_key = ""
    with pytest.raises(RuntimeError, match="MOCKUP_AOAI"):
        await client.complete("sys", "usr", stream=False)


@pytest.mark.asyncio
async def test_complete_non_streaming_returns_content():
    client = MockupLLMClient()
    client._endpoint = "http://fake"
    client._api_key = "fake"
    client._model = "gpt-5.2"

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json = lambda: {
        "choices": [{"message": {"content": "hello world"}}]
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__aenter__.return_value
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await client.complete("sys", "usr", stream=False)

    assert result == "hello world"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_client.py -v`
Expected: FAIL — `app.llm.mockup_client` module not found

- [ ] **Step 3: MockupLLMClient 구현**

Create `backend/app/llm/mockup_client.py`:

```python
"""원본 pfy-front scaffolding/src/utils/llmClient.ts의 Python 포팅.

사내 AOAI 게이트웨이(X-Api-Key 헤더, OpenAI chat 포맷)를 호출한다.
기존 AzureOpenAI SDK와 다른 인증/엔드포인트 구조라 전용 클라이언트로 분리.
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings


class MockupLLMClient:
    def __init__(self) -> None:
        self._endpoint = settings.MOCKUP_AOAI_ENDPOINT
        self._api_key = settings.MOCKUP_AOAI_API_KEY
        self._model = settings.MOCKUP_AOAI_DEPLOYMENT

    async def complete(
        self,
        system: str,
        user: str,
        stream: bool = False,
        max_tokens: int | None = None,
        temperature: float = 0.35,
    ) -> str | AsyncIterator[str]:
        if not self._endpoint or not self._api_key:
            raise RuntimeError(
                "MOCKUP_AOAI_ENDPOINT / MOCKUP_AOAI_API_KEY 가 .env에 설정되지 않았습니다."
            )

        max_tok = max_tokens if max_tokens is not None else settings.MOCKUP_AOAI_MAX_TOKENS
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tok,
            "stream": stream,
        }
        headers = {"Content-Type": "application/json", "X-Api-Key": self._api_key}

        if not stream:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=30.0), verify=False
            ) as c:
                r = await c.post(self._endpoint, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
                return data["choices"][0]["message"]["content"]

        async def _stream() -> AsyncIterator[str]:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(None, connect=30.0), verify=False
            ) as c:
                async with c.stream("POST", self._endpoint, json=body, headers=headers) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[6:].strip()
                        if payload == "[DONE]":
                            break
                        try:
                            obj = json.loads(payload)
                            delta = obj.get("choices", [{}])[0].get("delta", {}).get("content")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

        return _stream()


mockup_client = MockupLLMClient()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_client.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/mockup_client.py backend/tests/test_mockup_client.py
git commit -m "feat(mockup-client): add MockupLLMClient for original pfy-front AOAI gateway"
```

---

## Task 3: 원본 프롬프트 파일 복사

**Files:**
- Create: `pfy_prompt/brief.md`
- Create: `pfy_prompt/mockupPrompt.md`
- Create: `pfy_prompt/InterviewParser.md`

원본 파일은 `/Users/g1_kang/Downloads/pfy-front/RequirementPrompt/`에 있음.

- [ ] **Step 1: 복사**

Run:
```bash
cp /Users/g1_kang/Downloads/pfy-front/RequirementPrompt/brief.md pfy_prompt/brief.md
cp /Users/g1_kang/Downloads/pfy-front/RequirementPrompt/mockupPrompt.md pfy_prompt/mockupPrompt.md
cp /Users/g1_kang/Downloads/pfy-front/RequirementPrompt/InterviewParser.md pfy_prompt/InterviewParser.md
```

- [ ] **Step 2: 파일 존재 확인**

Run:
```bash
ls -la pfy_prompt/brief.md pfy_prompt/mockupPrompt.md pfy_prompt/InterviewParser.md
```
Expected: 세 파일 모두 존재, 크기 > 0

- [ ] **Step 3: Commit**

```bash
git add pfy_prompt/brief.md pfy_prompt/mockupPrompt.md pfy_prompt/InterviewParser.md
git commit -m "feat(prompts): copy original pfy-front RequirementPrompt files"
```

---

## Task 4: componentCatalog.md 생성 스크립트

**Files:**
- Create: `backend/scripts/build_component_catalog.py`
- Create: `pfy_prompt/componentCatalog.md` (스크립트 산출물)

- [ ] **Step 1: 스크립트 작성**

Create `backend/scripts/build_component_catalog.py`:

```python
"""원본 pfy-front의 템플릿/공통 컴포넌트 메타를 componentCatalog.md로 생성.

사용:
  python backend/scripts/build_component_catalog.py

출력: pfy_prompt/componentCatalog.md
"""
from __future__ import annotations

import re
from pathlib import Path

PFY_FRONT_ROOT = Path("/Users/g1_kang/Downloads/pfy-front/src")
OUTPUT = Path(__file__).parent.parent.parent / "pfy_prompt" / "componentCatalog.md"

TEMPLATE_DIRS = [
    "templates/TypeA_StandardSearch",
    "templates/TypeB_InputDetail",
    "templates/TypeC_TreeGrid",
    "templates/TypeD_MasterDetail",
]

COMMON_COMPONENT_DIRS = [
    "components/common/searchForm",
    "components/common/dataTable2",
    "components/common/treeTable",
    "components/common/button",
    "components/common/select",
    "components/common/inputText",
    "components/common/inputNumber",
    "components/common/datePicker",
    "components/common/textarea",
    "components/common/contentHeader",
    "components/common/paginator",
    "components/common/splitter",
    "components/common/radioButton",
    "components/common/toggleSwitch",
]


def extract_template_section(vue_source: str) -> str:
    m = re.search(r"<template[^>]*>(.*?)</template>", vue_source, re.DOTALL)
    return m.group(1).strip() if m else ""


def extract_props(vue_source: str) -> list[str]:
    """defineProps<{...}>()에서 prop 이름 추출."""
    m = re.search(r"defineProps<\{([^}]*)\}>", vue_source, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    return re.findall(r"^\s*(\w+)[\?:]", body, re.MULTILINE)


def main() -> None:
    lines: list[str] = [
        "# Component Catalog",
        "",
        "원본 pfy-front의 템플릿 및 공통 컴포넌트 시그니처. ",
        "Mockup 생성 LLM은 여기 등록된 컴포넌트만 사용해야 한다.",
        "",
        "## 페이지 템플릿 (TypeA~D)",
        "",
        "각 생성 페이지는 반드시 아래 4개 중 하나를 상속(사용)해야 한다:",
        "",
    ]

    for rel in TEMPLATE_DIRS:
        full = PFY_FRONT_ROOT / rel / "index.vue"
        if not full.exists():
            lines.append(f"- `@/{rel}` — **파일 없음**")
            continue
        src = full.read_text(encoding="utf-8")
        template = extract_template_section(src)
        props = extract_props(src)
        preview = "\n".join(template.splitlines()[:40])
        lines.append(f"### `@/{rel}`")
        lines.append("")
        if props:
            lines.append(f"**Props**: {', '.join(props)}")
            lines.append("")
        lines.append("**Template 구조 (상위 40줄)**:")
        lines.append("```vue")
        lines.append(preview)
        lines.append("```")
        lines.append("")

    lines.append("## 공통 컴포넌트")
    lines.append("")
    lines.append("생성 페이지는 아래 공통 컴포넌트만 import하여 사용한다:")
    lines.append("")

    for rel in COMMON_COMPONENT_DIRS:
        full = PFY_FRONT_ROOT / rel
        if not full.exists():
            continue
        index = full / "index.ts"
        if index.exists():
            exports_raw = index.read_text(encoding="utf-8")
            exports = re.findall(r"export\s+\{([^}]+)\}", exports_raw)
            names = []
            for e in exports:
                names.extend(n.strip() for n in e.split(","))
            lines.append(f"- `@/{rel}` → `{{ {', '.join(names)} }}`")
        else:
            vues = list(full.glob("*.vue"))
            names = [v.stem for v in vues]
            lines.append(f"- `@/{rel}` → `{', '.join(names)}.vue`")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 스크립트 실행**

Run:
```bash
cd /Users/g1_kang/projects/need-only-prd
python backend/scripts/build_component_catalog.py
```
Expected: `Written: ...pfy_prompt/componentCatalog.md`

- [ ] **Step 3: 결과 확인**

Run: `head -50 pfy_prompt/componentCatalog.md`
Expected: Markdown 헤더 + TypeA~D 섹션 + 공통 컴포넌트 목록 표시

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/build_component_catalog.py pfy_prompt/componentCatalog.md
git commit -m "feat(prompts): generate componentCatalog.md from original pfy-front sources"
```

---

## Task 5: MockupState 모델 재정의

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_mockup_models.py` (전체 재작성)

- [ ] **Step 1: 테스트 재작성**

Replace the contents of `backend/tests/test_mockup_models.py`:

```python
from datetime import datetime, timezone

from app.models import MockupState, SessionState


def test_mockup_state_minimal():
    s = MockupState(project_id="ETHICS_REPORT", project_name="윤리경영")
    assert s.project_id == "ETHICS_REPORT"
    assert s.project_name == "윤리경영"
    assert s.brief_md is None
    assert s.mockup_vue is None
    assert s.raw_interview_text is None
    assert s.interview_notes_md is None
    assert s.current_step == 1


def test_mockup_state_full():
    s = MockupState(
        project_id="EDU_PROG",
        project_name="교육",
        brief_md="# Brief",
        mockup_vue="<template>...</template>",
        raw_interview_text="text...",
        interview_notes_md="## Keep...",
        current_step=4,
    )
    assert s.current_step == 4
    assert s.brief_md == "# Brief"


def test_mockup_state_ignores_legacy_fields():
    """기존 디스크 세션에 screen_id, fields 등 구 필드가 있어도 ValidationError 없이 무시."""
    s = MockupState(
        project_id="X",
        project_name="X",
        screen_id="SHOULD_IGNORE",       # legacy
        fields=[{"a": 1}],                # legacy
        annotations=None,                  # legacy
    )
    assert s.project_id == "X"
    assert not hasattr(s, "screen_id") or s.model_extra is not None


def test_session_state_with_new_mockup():
    session = SessionState(
        session_id="t1",
        created_at=datetime.now(timezone.utc),
        spec_source="mockup",
        mockup_state=MockupState(project_id="P1", project_name="N1"),
    )
    assert session.spec_source == "mockup"
    assert session.mockup_state.project_id == "P1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_models.py -v`
Expected: FAIL — new field names not in model

- [ ] **Step 3: models.py 업데이트**

Open `backend/app/models.py`. Delete the existing `FieldOption`, `FieldDef`, `TabDef`, `MockupState` class definitions. Replace with:

```python
class MockupState(BaseModel):
    project_id: str
    project_name: str
    brief_md: str | None = None
    mockup_vue: str | None = None
    raw_interview_text: str | None = None
    interview_notes_md: str | None = None
    current_step: int = 1

    model_config = {"extra": "ignore"}
```

Remove the `from pydantic import ConfigDict` import if it was only used elsewhere (else keep). `SessionState` class already has `spec_source: Literal["text", "mockup"] | None = None` and `mockup_state: MockupState | None = None` fields — leave those.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/tests/test_mockup_models.py
git commit -m "feat(models): redefine MockupState for 4-step flow (brief/mockup/interview/spec)"
```

---

## Task 6: mockup_prompts.py 재작성

**Files:**
- Replace: `backend/app/llm/mockup_prompts.py`

- [ ] **Step 1: 파일 완전 재작성**

Replace the entire contents of `backend/app/llm/mockup_prompts.py`:

```python
"""Mockup 파이프라인 프롬프트 (원본 pfy-front RequirementPrompt 포팅).

각 함수는 (system, user) 튜플을 반환한다. 시스템 프롬프트는 pfy_prompt/ 디렉토리의
원본 Markdown을 로드하여 사용한다.
"""
from __future__ import annotations

from pathlib import Path

from app.config import settings

_PROMPT_DIR = Path(settings.PROMPT_REFERENCE_DIR)

_cache: dict[str, str] = {}


def _load(filename: str) -> str:
    if filename in _cache:
        return _cache[filename]
    p = _PROMPT_DIR / filename
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    _cache[filename] = text
    return text


def brief_template() -> str:
    """Step1 textarea 프리필용 brief.md 원본 내용 반환 (LLM 호출 없음)."""
    return _load("brief.md")


def mockup_generation_prompt(brief_md: str) -> tuple[str, str]:
    """brief.md + mockupPrompt.md + componentCatalog.md → Vue SFC 생성 프롬프트."""
    mockup_system = _load("mockupPrompt.md")
    catalog = _load("componentCatalog.md")
    system = (
        f"{mockup_system}\n\n"
        f"--- ALLOWED COMPONENT CATALOG ---\n{catalog}\n"
        "--- END CATALOG ---\n\n"
        "중요: 위 catalog에 등록된 템플릿/컴포넌트만 사용하고, "
        "반드시 하나의 .vue 파일에 모든 화면을 v-if 로 전환하는 구조로 생성하세요. "
        "설명 없이 Vue SFC 코드만 출력합니다."
    )
    user = f"--- Brief ---\n{brief_md}\n--- End Brief ---"
    return system, user


def interview_parser_prompt(mockup_vue: str, raw_interview_text: str) -> tuple[str, str]:
    """Mockup + 인터뷰 원문 → interviewNotes.md (Keep/Change/Add/Out/TBD)."""
    system = _load("InterviewParser.md")
    user = (
        f"--- Mockup.vue ---\n{mockup_vue}\n"
        f"--- End Mockup ---\n\n"
        f"--- 인터뷰 원문 ---\n{raw_interview_text}\n"
        f"--- End 인터뷰 ---"
    )
    return system, user


def master_spec_prompt(
    brief_md: str,
    mockup_vue: str,
    interview_notes_md: str,
) -> tuple[str, str]:
    """masterPrompt.md 기반 최종 spec.md 생성. brief/mockup/interview 모두 전달."""
    system = _load("masterPrompt.md")
    user = (
        f"# Customer Input\n\n"
        f"## [1] brief.md\n{brief_md}\n\n"
        f"## [2] Mockup.vue\n```vue\n{mockup_vue}\n```\n\n"
        f"## [3] interviewNotes.md\n{interview_notes_md}"
    )
    return system, user
```

- [ ] **Step 2: Import 검증**

Run:
```bash
cd backend && source .venv/bin/activate && python -c "
from app.llm.mockup_prompts import (
    brief_template, mockup_generation_prompt,
    interview_parser_prompt, master_spec_prompt,
)
print('OK')
print(f'brief.md length: {len(brief_template())}')
"
```
Expected: `OK` + brief.md 길이 출력 (>0)

- [ ] **Step 3: Commit**

```bash
git add backend/app/llm/mockup_prompts.py
git commit -m "feat(mockup-prompts): rewrite for brief/mockup/interview/spec 4-step flow"
```

---

## Task 7: mockup_pipeline.py 재작성

**Files:**
- Replace: `backend/app/llm/mockup_pipeline.py`
- Create: `backend/tests/test_mockup_pipeline.py`

- [ ] **Step 1: 테스트 작성**

Create `backend/tests/test_mockup_pipeline.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.llm.mockup_pipeline import mockup_pipeline


@pytest.mark.asyncio
async def test_generate_mockup_streaming_yields_chunks():
    async def fake_stream():
        yield "<template>"
        yield "</template>"

    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value=fake_stream())
        result = []
        async for chunk in mockup_pipeline.generate_mockup_streaming("# brief"):
            result.append(chunk)
        assert "".join(result) == "<template></template>"


@pytest.mark.asyncio
async def test_generate_mockup_streaming_fallback_when_not_async_iter():
    """게이트웨이가 스트리밍 미지원 → 전체 문자열 반환 시 줄 단위 에뮬레이션."""
    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value="line1\nline2\n")
        result = []
        async for chunk in mockup_pipeline.generate_mockup_streaming("# brief"):
            result.append(chunk)
        assert "".join(result) == "line1\nline2\n"


@pytest.mark.asyncio
async def test_parse_interview_returns_string():
    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value="## Keep\n- ...")
        out = await mockup_pipeline.parse_interview("<vue>", "raw text")
        assert out.startswith("## Keep")


@pytest.mark.asyncio
async def test_generate_spec_streaming():
    async def fake_stream():
        yield "# Spec\n"
        yield "## 1. "

    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value=fake_stream())
        result = []
        async for chunk in mockup_pipeline.generate_spec_streaming("b", "v", "n"):
            result.append(chunk)
        assert "".join(result) == "# Spec\n## 1. "
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_pipeline.py -v`
Expected: FAIL — current pipeline doesn't match signatures

- [ ] **Step 3: mockup_pipeline.py 재작성**

Replace the entire contents of `backend/app/llm/mockup_pipeline.py`:

```python
"""Mockup 기반 4단계 spec 생성 파이프라인.

원본 pfy-front 플로우:
  brief.md → Mockup.vue → interviewNotes.md → spec.md

모든 LLM 호출은 mockup_client(gpt-5.2, 원본 사내 게이트웨이)를 사용한다.
기존 llm_client(gpt-5.4)는 코드 생성 / 텍스트 spec 파이프라인 전용.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm.mockup_client import mockup_client
from app.llm.mockup_prompts import (
    interview_parser_prompt,
    master_spec_prompt,
    mockup_generation_prompt,
)


class MockupPipeline:
    async def generate_mockup_streaming(self, brief_md: str) -> AsyncIterator[str]:
        system, user = mockup_generation_prompt(brief_md)
        result = await mockup_client.complete(system, user, stream=True)
        async for chunk in _as_async_iter(result):
            yield chunk

    async def parse_interview(self, mockup_vue: str, raw_interview_text: str) -> str:
        system, user = interview_parser_prompt(mockup_vue, raw_interview_text)
        response = await mockup_client.complete(system, user, stream=False)
        return str(response)

    async def generate_spec_streaming(
        self,
        brief_md: str,
        mockup_vue: str,
        interview_notes_md: str,
    ) -> AsyncIterator[str]:
        system, user = master_spec_prompt(brief_md, mockup_vue, interview_notes_md)
        result = await mockup_client.complete(system, user, stream=True)
        async for chunk in _as_async_iter(result):
            yield chunk


async def _as_async_iter(result) -> AsyncIterator[str]:
    """게이트웨이가 stream 미지원 시 전체 응답 문자열 → 줄 단위 yield로 에뮬레이션."""
    if hasattr(result, "__aiter__"):
        async for chunk in result:
            yield chunk
    else:
        text = str(result)
        # 청크 단위로 쪼개서 UX 향상 (줄 단위)
        for line in text.splitlines(keepends=True):
            yield line


mockup_pipeline = MockupPipeline()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_pipeline.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/llm/mockup_pipeline.py backend/tests/test_mockup_pipeline.py
git commit -m "feat(mockup-pipeline): rewrite for 4-step flow using MockupLLMClient"
```

---

## Task 8: mockup.py 라우터 재작성

**Files:**
- Replace: `backend/app/routers/mockup.py`
- Create: `backend/tests/test_mockup_router.py`

- [ ] **Step 1: 테스트 작성**

Create `backend/tests/test_mockup_router.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
HEADERS = {"X-Session-ID": "mockup-router-test-1"}


def test_brief_creates_state():
    r = client.post(
        "/api/mockup/brief",
        json={"project_id": "TEST_PRJ", "project_name": "테스트", "brief_md": "# Brief"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["project_id"] == "TEST_PRJ"

    s = client.get("/api/session", headers=HEADERS).json()
    assert s["mockup_state"]["project_id"] == "TEST_PRJ"
    assert s["mockup_state"]["current_step"] == 1


def test_brief_rejects_invalid_project_id():
    r = client.post(
        "/api/mockup/brief",
        json={"project_id": "invalid-id!", "project_name": "X", "brief_md": "x"},
        headers={"X-Session-ID": "mockup-router-test-2"},
    )
    assert r.status_code == 400


def test_reset_clears_state():
    client.post(
        "/api/mockup/brief",
        json={"project_id": "R1", "project_name": "R", "brief_md": "x"},
        headers={"X-Session-ID": "mockup-router-test-3"},
    )
    r = client.post("/api/mockup/reset", headers={"X-Session-ID": "mockup-router-test-3"})
    assert r.status_code == 200
    s = client.get("/api/session", headers={"X-Session-ID": "mockup-router-test-3"}).json()
    assert s["mockup_state"] is None


@pytest.mark.asyncio
async def test_parse_interview_requires_mockup():
    """Step 3는 mockup_vue가 이미 생성되어 있어야 함."""
    headers = {"X-Session-ID": "mockup-router-test-4"}
    client.post(
        "/api/mockup/brief",
        json={"project_id": "P4", "project_name": "X", "brief_md": "x"},
        headers=headers,
    )
    r = client.post(
        "/api/mockup/parse-interview",
        json={"raw_interview_text": "test"},
        headers=headers,
    )
    assert r.status_code == 400  # mockup_vue 없음
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_router.py -v`
Expected: FAIL — old endpoints exist, new `/brief` doesn't

- [ ] **Step 3: mockup.py 라우터 완전 재작성**

Replace the entire contents of `backend/app/routers/mockup.py`:

```python
"""Mockup pipeline router (원본 pfy-front 4단계 플로우)."""
from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.llm.mockup_pipeline import mockup_pipeline
from app.models import MockupState
from app.session import get_session_id, session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mockup", tags=["mockup"])

_PFY_FRONT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "pfy-front"
_PFY_PAGES_GENERATED = _PFY_FRONT_ROOT / "src" / "pages" / "generated"
_PFY_STATIC_ROUTES = _PFY_FRONT_ROOT / "src" / "router" / "staticRoutes.ts"

_PROJECT_ID_RE = re.compile(r"^[A-Z0-9_]+$")


# ── Request models ───────────────────────────────────────────────────────────

class BriefRequest(BaseModel):
    project_id: str
    project_name: str
    brief_md: str


class ParseInterviewRequest(BaseModel):
    raw_interview_text: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _require_mockup_state(session_id: str) -> MockupState:
    s = session_store.get(session_id)
    if s is None or s.mockup_state is None:
        raise HTTPException(400, "No mockup state. Call /api/mockup/brief first.")
    return s.mockup_state


def _write_vue_to_pfy_front(project_id: str, vue_code: str, project_name: str) -> str | None:
    try:
        pid = project_id.lower()
        page_dir = _PFY_PAGES_GENERATED / pid
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.vue").write_text(vue_code, encoding="utf-8")
        meta = {
            "screenId": project_id.upper(),
            "screenName": project_name,
            "pageType": "project-mockup",
            "routePath": f"/{project_id.upper()}",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        (page_dir / "scaffold-meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        route_path = f"/{project_id.upper()}"
        route_name = project_id.upper()
        if _PFY_STATIC_ROUTES.exists():
            content = _PFY_STATIC_ROUTES.read_text(encoding="utf-8")
            if f"name: '{route_name}'" not in content:
                entry = (
                    f"    {{\n"
                    f"      path: '{route_path}',\n"
                    f"      name: '{route_name}',\n"
                    f"      meta: {{ menuId: '{route_name}', generated: true }},\n"
                    f"      component: () => import('@/pages/generated/{pid}/index.vue'),\n"
                    f"    }},\n"
                )
                marker = "path: '/:pathMatch(.*)*'"
                idx = content.find(marker)
                if idx != -1:
                    brace_idx = content.rfind("{", 0, idx)
                    if brace_idx != -1:
                        line_start = content.rfind("\n", 0, brace_idx) + 1
                        content = content[:line_start] + entry + content[line_start:]
                        _PFY_STATIC_ROUTES.write_text(content, encoding="utf-8")
        return route_path
    except Exception as e:
        logger.warning("[mockup] Failed to write pfy-front: %s", e)
        return None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/brief")
async def brief(body: BriefRequest, session_id: str = Depends(get_session_id)):
    if not _PROJECT_ID_RE.match(body.project_id):
        raise HTTPException(400, "project_id는 영문 대문자, 숫자, 언더스코어만 허용됩니다.")
    session = session_store.get_or_create(session_id)
    session.mockup_state = MockupState(
        project_id=body.project_id,
        project_name=body.project_name,
        brief_md=body.brief_md,
        current_step=1,
    )
    session.spec_source = "mockup"
    session_store.save(session_id)
    return {"project_id": body.project_id, "project_name": body.project_name, "current_step": 1}


@router.post("/generate-mockup")
async def generate_mockup(session_id: str = Depends(get_session_id)):
    ms = _require_mockup_state(session_id)
    if not ms.brief_md:
        raise HTTPException(400, "brief_md가 없습니다.")

    async def event_gen() -> AsyncGenerator[dict, None]:
        try:
            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Generating Mockup.vue..."})}
            session_store.increment_llm_calls(session_id)
            full = ""
            async for chunk in mockup_pipeline.generate_mockup_streaming(ms.brief_md):
                full += chunk
                yield {"event": "message", "data": json.dumps({"type": "chunk", "content": chunk})}

            # 코드블록 제거 (LLM이 ```vue ... ```로 감쌀 수 있음)
            cleaned = re.sub(r"^```(?:vue)?\s*", "", full.strip())
            cleaned = re.sub(r"```\s*$", "", cleaned).strip()

            ms.mockup_vue = cleaned
            ms.current_step = 2
            session_store.save(session_id)

            route_path = _write_vue_to_pfy_front(ms.project_id, cleaned, ms.project_name)

            yield {"event": "message", "data": json.dumps({"type": "complete", "route_path": route_path})}
        except HTTPException as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": e.detail})}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_gen(), ping=10)


@router.post("/parse-interview")
async def parse_interview(body: ParseInterviewRequest, session_id: str = Depends(get_session_id)):
    ms = _require_mockup_state(session_id)
    if not ms.mockup_vue:
        raise HTTPException(400, "mockup_vue가 없습니다. /generate-mockup을 먼저 호출하세요.")

    session_store.increment_llm_calls(session_id)
    interview_notes = await mockup_pipeline.parse_interview(ms.mockup_vue, body.raw_interview_text)
    ms.raw_interview_text = body.raw_interview_text
    ms.interview_notes_md = interview_notes
    ms.current_step = 3
    session_store.save(session_id)
    return {"interview_notes_md": interview_notes, "current_step": 3}


@router.post("/generate-spec")
async def generate_spec(session_id: str = Depends(get_session_id)):
    ms = _require_mockup_state(session_id)
    session = session_store.get(session_id)
    if not ms.brief_md or not ms.mockup_vue or not ms.interview_notes_md:
        raise HTTPException(400, "brief / mockup / interview 중 누락된 것이 있습니다.")

    async def event_gen() -> AsyncGenerator[dict, None]:
        try:
            yield {"event": "message", "data": json.dumps({"type": "status", "content": "Generating spec.md..."})}
            session_store.increment_llm_calls(session_id)
            full = ""
            async for chunk in mockup_pipeline.generate_spec_streaming(
                ms.brief_md, ms.mockup_vue, ms.interview_notes_md,
            ):
                full += chunk
                yield {"event": "message", "data": json.dumps({"type": "chunk", "content": chunk})}

            session.spec_markdown = full
            session.spec_version += 1
            ms.current_step = 4
            session_store.save(session_id)

            yield {"event": "message", "data": json.dumps({"type": "complete", "spec_version": session.spec_version})}
        except HTTPException as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": e.detail})}
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

    return EventSourceResponse(event_gen(), ping=10)


@router.post("/reset")
async def reset(session_id: str = Depends(get_session_id)):
    s = session_store.get(session_id)
    if s:
        s.mockup_state = None
        s.spec_source = None
        session_store.save(session_id)
    return {"reset": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && python -m pytest tests/test_mockup_router.py -v`
Expected: 4 tests PASS

- [ ] **Step 5: Verify no regressions**

Run: `cd backend && source .venv/bin/activate && python -m pytest -v 2>&1 | tail -5`
Expected: All tests PASS (except possibly test_vue_generator.py which we'll delete next)

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/mockup.py backend/tests/test_mockup_router.py
git commit -m "feat(mockup-api): replace endpoints with 4-step brief/mockup/interview/spec flow"
```

---

## Task 9: vue_generator 삭제

**Files:**
- Delete: `backend/app/llm/vue_generator.py`
- Delete: `backend/tests/test_vue_generator.py`

- [ ] **Step 1: 파일 삭제**

Run:
```bash
rm backend/app/llm/vue_generator.py
rm backend/tests/test_vue_generator.py
```

- [ ] **Step 2: 참조 남아있는지 확인**

Run:
```bash
cd /Users/g1_kang/projects/need-only-prd && grep -rn "vue_generator" backend/ 2>/dev/null
```
Expected: 출력 없음 (모든 import 제거됨)

- [ ] **Step 3: 테스트 재실행**

Run: `cd backend && source .venv/bin/activate && python -m pytest -v 2>&1 | tail -5`
Expected: 전체 테스트 PASS

- [ ] **Step 4: Commit**

```bash
git add -u backend/app/llm/vue_generator.py backend/tests/test_vue_generator.py
git commit -m "chore(vue-generator): remove (replaced by LLM Vue generation)"
```

---

## Task 10: Frontend 타입 재정의

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: 기존 Mockup 관련 타입 제거 + 신규 타입 추가**

Open `frontend/src/types/index.ts`. Find and **delete** these declarations (they start with `// --- Mockup Pipeline Types ---` comment):

- `SCREEN_ID_INVALID_CHARS`
- `FieldOption`
- `FieldDef`
- `InterviewQuestion`
- `MockupState` (old version with screenId, fields, annotations...)
- `AiGenerateResult`
- `ScaffoldResult`
- `AnnotateResult`
- `InterviewResult`
- `InterviewResultResponse`

Replace with:

```typescript
// --- Mockup Pipeline Types (원본 pfy-front 4단계 플로우) ---

/** project_id는 영문 대문자, 숫자, 언더스코어만 허용 */
export const PROJECT_ID_INVALID_CHARS = /[^A-Z0-9_]/g

export interface MockupState {
  projectId: string
  projectName: string
  briefMd: string | null
  mockupVue: string | null
  rawInterviewText: string | null
  interviewNotesMd: string | null
  currentStep: number
}

export interface BriefRequest {
  project_id: string
  project_name: string
  brief_md: string
}

export interface BriefResponse {
  project_id: string
  project_name: string
  current_step: number
}

export interface ParseInterviewResponse {
  interview_notes_md: string
  current_step: number
}
```

- [ ] **Step 2: TypeScript 컴파일 확인**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 여러 에러 (기존 참조가 깨짐) — Task 11, 12에서 해결됨. 이번 Step에서는 일단 넘어감.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(types): redefine Mockup types for 4-step flow (project_id/brief/mockup/interview/spec)"
```

---

## Task 11: API 클라이언트 재정의

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 기존 Mockup API 함수 제거 + 신규 함수 추가**

Open `frontend/src/api/client.ts`. **Delete** these functions:
- `mockupAiGenerate`
- `mockupScaffold`
- `mockupAiAnnotate`
- `mockupAiInterview`
- `mockupInterviewResult`
- `mockupGenerateSpec` (old SSE function)

Replace the "--- Mockup Pipeline API ---" section with:

```typescript
// --- Mockup Pipeline API (원본 pfy-front 4단계 플로우) ---

export async function mockupBrief(
  projectId: string,
  projectName: string,
  briefMd: string,
): Promise<import('../types').BriefResponse> {
  const res = await fetch('/api/mockup/brief', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: projectId,
      project_name: projectName,
      brief_md: briefMd,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export function mockupGenerateMockup(
  onEvent: (event: import('../types').SSEEvent) => void,
): void {
  consumeSSE('/api/mockup/generate-mockup', onEvent, {})
}

export async function mockupParseInterview(
  rawInterviewText: string,
): Promise<import('../types').ParseInterviewResponse> {
  const res = await fetch('/api/mockup/parse-interview', {
    method: 'POST',
    headers: { ...apiHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_interview_text: rawInterviewText }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail ?? `Request failed: ${res.status}`)
  }
  return res.json()
}

export function mockupGenerateSpec(
  onEvent: (event: import('../types').SSEEvent) => void,
): void {
  consumeSSE('/api/mockup/generate-spec', onEvent, {})
}

export async function mockupReset(): Promise<void> {
  await fetch('/api/mockup/reset', { method: 'POST', headers: apiHeaders() })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat(api): redefine Mockup API client for brief/mockup/interview/spec endpoints"
```

---

## Task 12: Zustand 스토어 재정의

**Files:**
- Modify: `frontend/src/store/sessionStore.ts`

- [ ] **Step 1: import 수정**

Open `frontend/src/store/sessionStore.ts`. Find the imports block and:

Replace:
```typescript
import { SCREEN_ID_INVALID_CHARS } from '../types'
```
with: (delete this line entirely — no longer used)

Replace:
```typescript
  mockupAiGenerate as apiMockupAiGenerate,
  mockupScaffold as apiMockupScaffold,
  mockupAiAnnotate as apiMockupAiAnnotate,
  mockupAiInterview as apiMockupAiInterview,
  mockupInterviewResult as apiMockupInterviewResult,
  mockupGenerateSpec as apiMockupGenerateSpec,
```
with:
```typescript
  mockupBrief as apiMockupBrief,
  mockupGenerateMockup as apiMockupGenerateMockup,
  mockupParseInterview as apiMockupParseInterview,
  mockupGenerateSpec as apiMockupGenerateSpec,
  mockupReset as apiMockupReset,
```

- [ ] **Step 2: SessionStore interface의 Mockup 부분 교체**

Find and **delete** the existing Mockup interface block:
```typescript
  setSpecMode: (mode: 'text' | 'mockup') => void
  mockupAiGenerate: ...
  mockupScaffold: ...
  mockupAiAnnotate: ...
  mockupAiInterview: ...
  mockupSubmitInterviewResult: ...
  mockupGenerateSpec: ...
  mockupGoToStep: ...
  resetMockup: ...
```

Replace with:
```typescript
  // --- Mockup Pipeline (원본 pfy-front 4단계) ---
  specMode: 'text' | 'mockup'
  mockupState: MockupState | null
  mockupLoading: boolean
  mockupError: string | null
  setSpecMode: (mode: 'text' | 'mockup') => void
  mockupSetBrief: (projectId: string, projectName: string, briefMd: string) => Promise<void>
  mockupGenerateMockup: () => void
  mockupParseInterview: (rawText: string) => Promise<void>
  mockupGenerateSpec: () => void
  mockupGoToStep: (step: number) => void
  resetMockup: () => Promise<void>
```

- [ ] **Step 3: 구현부 교체**

Find and **delete** the existing implementations (`mockupAiGenerate: async`, `mockupScaffold: async`, ..., through `resetMockup: () => set({...})`).

Replace with:

```typescript
  specMode: 'text',
  mockupState: null,
  mockupLoading: false,
  mockupError: null,

  setSpecMode: (mode) => set({ specMode: mode }),

  mockupSetBrief: async (projectId, projectName, briefMd) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      await apiMockupBrief(projectId, projectName, briefMd)
      set({
        mockupState: {
          projectId, projectName, briefMd,
          mockupVue: null, rawInterviewText: null, interviewNotesMd: null,
          currentStep: 2,   // Step2로 바로 이동 (Brief 완료)
        },
        mockupLoading: false,
      })
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupGenerateMockup: () => {
    set({ mockupLoading: true, mockupError: null, statusMessage: 'Generating Mockup.vue...' })
    let acc = ''
    apiMockupGenerateMockup((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
        acc += event.content
        set((state) => ({
          mockupState: state.mockupState
            ? { ...state.mockupState, mockupVue: acc }
            : null,
        }))
      } else if (event.type === 'complete') {
        set((state) => ({
          mockupState: state.mockupState ? { ...state.mockupState, currentStep: 3 } : null,
          mockupLoading: false,
          statusMessage: null,
        }))
      } else if (event.type === 'error') {
        set({
          mockupError: event.content ?? event.message ?? 'Mockup 생성 실패',
          mockupLoading: false,
          statusMessage: null,
        })
      }
    })
  },

  mockupParseInterview: async (rawText) => {
    set({ mockupLoading: true, mockupError: null })
    try {
      const result = await apiMockupParseInterview(rawText)
      set((state) => ({
        mockupState: state.mockupState
          ? {
              ...state.mockupState,
              rawInterviewText: rawText,
              interviewNotesMd: result.interview_notes_md,
              currentStep: 4,   // Step4로 이동
            }
          : null,
        mockupLoading: false,
      }))
    } catch (e) {
      set({ mockupError: e instanceof Error ? e.message : String(e), mockupLoading: false })
    }
  },

  mockupGenerateSpec: () => {
    set({
      isGenerating: true,
      statusMessage: 'Generating spec.md...',
      specMarkdown: null,
    })
    apiMockupGenerateSpec((event) => {
      if (event.type === 'status') {
        set({ statusMessage: event.content ?? null })
      } else if ((event.type === 'chunk' || event.type === 'text') && event.content) {
        set((state) => ({ specMarkdown: (state.specMarkdown ?? '') + event.content }))
      } else if (event.type === 'complete') {
        set((state) => ({
          isGenerating: false,
          statusMessage: null,
          specVersion: event.spec_version ?? state.specVersion + 1,
        }))
      } else if (event.type === 'error') {
        set({
          isGenerating: false,
          statusMessage: event.content ?? 'Spec 생성 실패',
        })
      }
    })
  },

  mockupGoToStep: (step) =>
    set((state) => ({
      mockupState: state.mockupState
        ? { ...state.mockupState, currentStep: step }
        : null,
    })),

  resetMockup: async () => {
    try {
      await apiMockupReset()
    } catch { /* ignore network errors on reset */ }
    set({ mockupState: null, mockupLoading: false, mockupError: null })
  },
```

- [ ] **Step 4: reset 함수에서 mockup 상태 초기화 포함 확인**

Find the existing `reset: () => {` block. Make sure it also resets mockup fields. Replace the `set({` block inside `reset` with:

```typescript
    set({
      rawInput: null,
      specMarkdown: null,
      specVersion: 0,
      chatMessages: [],
      validationResult: null,
      isGenerating: false,
      isValidating: false,
      statusMessage: null,
      showCompare: false,
      codeGen: { ...initialCodeGen },
      _codegenAbort: null,
      specMode: 'text',
      mockupState: null,
      mockupLoading: false,
      mockupError: null,
    })
```

- [ ] **Step 5: 컴파일 확인 (일부 에러는 Task 13~16에서 해결)**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: mockup Step 컴포넌트 에러가 남아있을 수 있음 (다음 태스크들에서 해결)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/store/sessionStore.ts
git commit -m "feat(store): redefine mockup actions for brief/mockup/interview/spec flow"
```

---

## Task 13: StepIndicator 4단계로 수정

**Files:**
- Modify: `frontend/src/components/mockup/StepIndicator.tsx`

- [ ] **Step 1: 4단계 라벨로 교체**

Replace the entire contents of `frontend/src/components/mockup/StepIndicator.tsx`:

```tsx
interface Props {
  currentStep: number
  onStepClick?: (step: number) => void
}

const STEPS = [
  { num: 1, label: 'Brief', desc: '프로젝트 정보' },
  { num: 2, label: 'Mockup', desc: 'Vue 생성 & 미리보기' },
  { num: 3, label: '인터뷰', desc: '원천 → InterviewNote' },
  { num: 4, label: 'Spec', desc: '최종 spec.md' },
]

export default function StepIndicator({ currentStep, onStepClick }: Props) {
  return (
    <div className="flex items-center gap-2 justify-center flex-wrap mb-6">
      {STEPS.map((s, idx) => {
        const isActive = s.num === currentStep
        const isDone = s.num < currentStep
        const clickable = isDone && !!onStepClick

        return (
          <div key={s.num} className="flex items-center">
            <button
              type="button"
              onClick={() => clickable && onStepClick?.(s.num)}
              disabled={!clickable && !isActive}
              className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
                isActive
                  ? 'bg-primary text-on-primary shadow-md'
                  : isDone
                  ? 'bg-primary-fixed text-on-primary-fixed cursor-pointer hover:brightness-95'
                  : 'bg-surface-container text-on-surface-variant'
              }`}
            >
              <span className={`inline-flex w-6 h-6 items-center justify-center rounded-full text-xs font-bold ${
                isActive ? 'bg-on-primary/20' : isDone ? 'bg-on-primary-fixed/20' : 'bg-outline-variant/50'
              }`}>
                {isDone ? '✓' : s.num}
              </span>
              <span className="text-sm font-bold font-headline">{s.label}</span>
            </button>
            {idx < STEPS.length - 1 && (
              <div className={`w-6 h-[2px] ${isDone ? 'bg-primary-fixed' : 'bg-surface-container'}`} />
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
git commit -m "feat(ui): update StepIndicator for 4 steps (Brief/Mockup/Interview/Spec)"
```

---

## Task 14: Step1Brief 컴포넌트 신규

**Files:**
- Create: `frontend/src/components/mockup/Step1Brief.tsx`

- [ ] **Step 1: 구현**

Create `frontend/src/components/mockup/Step1Brief.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'
import { PROJECT_ID_INVALID_CHARS } from '../../types'

const DEFAULT_BRIEF_TEMPLATE = `# 프로젝트 개요
- 프로젝트명:
- 목적:
- 대상 사용자:

# 사용자 역할
- ADMIN:
- USER:

# 핵심 기능
1.
2.
3.

# 예상 화면 목록
- 화면1
- 화면2

# 기술 제약
- Spring Boot 3.x, Java 21, JPA, Querydsl
`

export default function Step1Brief() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const setBrief = useSessionStore((s) => s.mockupSetBrief)

  const [projectId, setProjectId] = useState(mockupState?.projectId ?? '')
  const [projectName, setProjectName] = useState(mockupState?.projectName ?? '')
  const [briefMd, setBriefMd] = useState(mockupState?.briefMd ?? DEFAULT_BRIEF_TEMPLATE)

  useEffect(() => {
    if (mockupState) {
      setProjectId(mockupState.projectId)
      setProjectName(mockupState.projectName)
      setBriefMd(mockupState.briefMd ?? DEFAULT_BRIEF_TEMPLATE)
    }
  }, [mockupState])

  const canSubmit =
    projectId.trim().length > 0 &&
    projectName.trim().length > 0 &&
    briefMd.trim().length > 0 &&
    !loading

  async function handleSubmit() {
    if (!canSubmit) return
    await setBrief(projectId, projectName, briefMd)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">① Brief 작성</h2>
        <p className="text-sm text-on-surface-variant">
          프로젝트 전체 정보를 5분 안에 채워주세요. 이 정보를 바탕으로 Mockup이 생성됩니다.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-bold text-on-surface mb-1 block">Project ID *</label>
          <input
            type="text"
            value={projectId}
            onChange={(e) =>
              setProjectId(e.target.value.toUpperCase().replace(PROJECT_ID_INVALID_CHARS, ''))
            }
            placeholder="예: ETHICS_REPORT"
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={loading}
          />
          <p className="text-xs text-on-surface-variant mt-1">영문 대문자, 숫자, 언더스코어만 허용</p>
        </div>
        <div>
          <label className="text-sm font-bold text-on-surface mb-1 block">프로젝트명 *</label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="예: 윤리경영시스템"
            className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={loading}
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-bold text-on-surface mb-1 block">brief.md *</label>
        <textarea
          value={briefMd}
          onChange={(e) => setBriefMd(e.target.value)}
          rows={20}
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={loading}
        />
      </div>

      {error && (
        <div className="bg-error-container text-on-error-container px-4 py-2 rounded-lg text-sm">{error}</div>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold font-headline shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? '저장 중...' : '다음: Mockup 생성 →'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/mockup/Step1Brief.tsx
git commit -m "feat(ui): add Step1Brief for project info and brief.md input"
```

---

## Task 15: Step2Mockup 컴포넌트 신규

**Files:**
- Create: `frontend/src/components/mockup/Step2Mockup.tsx`

- [ ] **Step 1: 구현**

Create `frontend/src/components/mockup/Step2Mockup.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'
import { useSessionStore } from '../../store/sessionStore'

const PFY_FRONT_DEV_URL = 'http://localhost:8081'
const VIEWPORT_WIDTH = 1440
const VIEWPORT_HEIGHT = 900

export default function Step2Mockup() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const generateMockup = useSessionStore((s) => s.mockupGenerateMockup)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const [showCode, setShowCode] = useState(false)
  const previewContainerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  useEffect(() => {
    const el = previewContainerRef.current
    if (!el) return
    const update = () => {
      const containerWidth = el.clientWidth
      setScale(containerWidth / VIEWPORT_WIDTH)
    }
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [mockupState?.mockupVue])

  const previewUrl = mockupState?.projectId
    ? `${PFY_FRONT_DEV_URL}/${mockupState.projectId}`
    : null

  const hasMockup = !!mockupState?.mockupVue
  const isGenerating = loading && !hasMockup

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">② Mockup 생성</h2>
        <p className="text-sm text-on-surface-variant">
          brief.md를 바탕으로 LLM이 Vue Mockup을 생성합니다. 화면 여러 개가 v-if로 포함되며,
          iframe에서 실제 렌더링을 볼 수 있습니다.
        </p>
      </div>

      {!hasMockup && !isGenerating && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={generateMockup}
            disabled={loading}
            className="gradient-button text-on-primary px-8 py-4 rounded-xl font-bold font-headline text-lg shadow-lg disabled:opacity-50 flex items-center gap-3"
          >
            <span className="material-symbols-outlined">auto_awesome</span>
            Mockup 생성 시작
          </button>
        </div>
      )}

      {isGenerating && (
        <div className="bg-surface-container-low rounded-xl p-6 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <div>
            <p className="text-sm font-bold text-on-surface">{statusMessage ?? '생성 중...'}</p>
            <p className="text-xs text-on-surface-variant mt-0.5">
              현재 코드 길이: {mockupState?.mockupVue?.length ?? 0} 자
            </p>
          </div>
        </div>
      )}

      {hasMockup && previewUrl && (
        <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-surface-container">
            <h3 className="font-bold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-tertiary">preview</span>
              Mockup 미리보기
            </h3>
            <div className="flex items-center gap-2">
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                새 탭
              </a>
              <button
                onClick={() => setShowCode(!showCode)}
                className="text-xs text-on-surface-variant hover:text-on-surface flex items-center gap-1 px-2 py-1 rounded-md hover:bg-surface-container"
              >
                <span className="material-symbols-outlined text-[16px]">
                  {showCode ? 'visibility_off' : 'code'}
                </span>
                {showCode ? '코드 숨기기' : '코드 보기'}
              </button>
            </div>
          </div>
          <div
            ref={previewContainerRef}
            className="relative overflow-hidden bg-white"
            style={{ height: `${VIEWPORT_HEIGHT * scale}px` }}
          >
            <iframe
              src={previewUrl}
              className="border-0 bg-white"
              style={{
                width: `${VIEWPORT_WIDTH}px`,
                height: `${VIEWPORT_HEIGHT}px`,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
              }}
              title="Mockup Preview"
            />
            <div className="absolute bottom-2 right-2 bg-surface-container/80 backdrop-blur-sm text-on-surface-variant text-xs px-2 py-1 rounded-md pointer-events-none">
              {previewUrl} · {Math.round(scale * 100)}%
            </div>
          </div>
        </div>
      )}

      {showCode && hasMockup && (
        <div className="bg-surface-container-lowest rounded-xl p-4 shadow-sm">
          <pre className="bg-inverse-surface text-inverse-on-surface rounded-lg p-4 text-xs overflow-auto max-h-[400px] leading-relaxed">
            {mockupState?.mockupVue}
          </pre>
        </div>
      )}

      {error && (
        <div className="bg-error-container text-on-error-container px-4 py-2 rounded-lg text-sm">{error}</div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => goToStep(1)}
          className="text-on-surface-variant hover:text-on-surface px-4 py-2 rounded-lg hover:bg-surface-container"
        >
          ← 이전
        </button>
        {hasMockup && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={generateMockup}
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high disabled:opacity-50"
            >
              재생성
            </button>
            <button
              type="button"
              onClick={() => goToStep(3)}
              className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold flex items-center gap-2"
            >
              다음: 인터뷰 →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/mockup/Step2Mockup.tsx
git commit -m "feat(ui): add Step2Mockup with LLM-generated Vue streaming and iframe preview"
```

---

## Task 16: Step3Interview 컴포넌트 신규

**Files:**
- Create: `frontend/src/components/mockup/Step3Interview.tsx`

- [ ] **Step 1: 구현**

Create `frontend/src/components/mockup/Step3Interview.tsx`:

```tsx
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useSessionStore } from '../../store/sessionStore'

export default function Step3Interview() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const loading = useSessionStore((s) => s.mockupLoading)
  const error = useSessionStore((s) => s.mockupError)
  const parseInterview = useSessionStore((s) => s.mockupParseInterview)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const [rawText, setRawText] = useState(mockupState?.rawInterviewText ?? '')

  const canSubmit = rawText.trim().length > 0 && !loading
  const hasNotes = !!mockupState?.interviewNotesMd

  async function handleSubmit() {
    if (!canSubmit) return
    await parseInterview(rawText)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">③ 인터뷰</h2>
        <p className="text-sm text-on-surface-variant">
          고객과 Mockup을 보며 진행한 인터뷰 원문(녹취 풀이 / 회의록)을 붙여넣으세요.
          LLM이 Keep / Change / Add / Out / TBD 5개 섹션으로 정리합니다.
        </p>
      </div>

      <div>
        <label className="text-sm font-bold text-on-surface mb-1 block">인터뷰 원문 *</label>
        <textarea
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          rows={15}
          placeholder="녹취를 풀어 정리한 텍스트 또는 회의록 원문을 붙여넣으세요..."
          className="w-full px-3 py-2 rounded-lg border border-outline-variant bg-surface-container-lowest text-on-surface font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={loading}
        />
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold flex items-center gap-2 disabled:opacity-50"
        >
          {loading ? 'InterviewNote 생성 중...' : 'InterviewNote 생성'}
        </button>
        {hasNotes && (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-surface-container text-on-surface hover:bg-surface-container-high disabled:opacity-50"
          >
            재생성
          </button>
        )}
      </div>

      {error && (
        <div className="bg-error-container text-on-error-container px-4 py-2 rounded-lg text-sm">{error}</div>
      )}

      {hasNotes && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm">
          <h3 className="font-bold text-on-surface mb-3">InterviewNote.md</h3>
          <div className="prose prose-sm max-w-none text-on-surface">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {mockupState?.interviewNotesMd ?? ''}
            </ReactMarkdown>
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => goToStep(2)}
          className="text-on-surface-variant hover:text-on-surface px-4 py-2 rounded-lg hover:bg-surface-container"
        >
          ← 이전
        </button>
        {hasNotes && (
          <button
            type="button"
            onClick={() => goToStep(4)}
            className="gradient-button text-on-primary px-6 py-3 rounded-xl font-bold flex items-center gap-2"
          >
            다음: Spec 생성 →
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/mockup/Step3Interview.tsx
git commit -m "feat(ui): add Step3Interview for raw transcript → InterviewNote parsing"
```

---

## Task 17: Step4SpecGenerate 컴포넌트 신규

**Files:**
- Create: `frontend/src/components/mockup/Step4SpecGenerate.tsx`

- [ ] **Step 1: 구현**

Create `frontend/src/components/mockup/Step4SpecGenerate.tsx`:

```tsx
import { useSessionStore } from '../../store/sessionStore'

export default function Step4SpecGenerate() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const isGenerating = useSessionStore((s) => s.isGenerating)
  const statusMessage = useSessionStore((s) => s.statusMessage)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)
  const generateSpec = useSessionStore((s) => s.mockupGenerateSpec)

  const briefOk = !!mockupState?.briefMd
  const mockupOk = !!mockupState?.mockupVue
  const notesOk = !!mockupState?.interviewNotesMd
  const canGenerate = briefOk && mockupOk && notesOk && !isGenerating

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold font-headline text-on-surface mb-1">④ Spec 생성</h2>
        <p className="text-sm text-on-surface-variant">
          Brief + Mockup + InterviewNote를 통합하여 최종 spec.md를 생성합니다.
        </p>
      </div>

      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm space-y-2">
        <h3 className="font-bold text-on-surface mb-2">입력 요약</h3>
        <div className="flex items-center gap-2 text-sm">
          <span className={`material-symbols-outlined ${briefOk ? 'text-green-600' : 'text-error'}`}>
            {briefOk ? 'check_circle' : 'cancel'}
          </span>
          <span>Brief: {briefOk ? `${mockupState?.briefMd?.length ?? 0}자` : '없음'}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className={`material-symbols-outlined ${mockupOk ? 'text-green-600' : 'text-error'}`}>
            {mockupOk ? 'check_circle' : 'cancel'}
          </span>
          <span>Mockup.vue: {mockupOk ? `${mockupState?.mockupVue?.length ?? 0}자` : '없음'}</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className={`material-symbols-outlined ${notesOk ? 'text-green-600' : 'text-error'}`}>
            {notesOk ? 'check_circle' : 'cancel'}
          </span>
          <span>InterviewNote: {notesOk ? '생성 완료' : '없음'}</span>
        </div>
      </div>

      {isGenerating && (
        <div className="bg-surface-container-low rounded-xl p-6 flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-bold text-on-surface">{statusMessage ?? '생성 중...'}</p>
        </div>
      )}

      <div className="flex justify-between">
        <button
          type="button"
          onClick={() => goToStep(3)}
          className="text-on-surface-variant hover:text-on-surface px-4 py-2 rounded-lg hover:bg-surface-container"
        >
          ← 이전
        </button>
        <button
          type="button"
          onClick={generateSpec}
          disabled={!canGenerate}
          className="gradient-button text-on-primary px-8 py-3 rounded-xl font-bold font-headline shadow-lg disabled:opacity-50 flex items-center gap-2"
        >
          <span className="material-symbols-outlined">article</span>
          {isGenerating ? 'Spec.md 생성 중...' : 'Spec.md 생성'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/mockup/Step4SpecGenerate.tsx
git commit -m "feat(ui): add Step4SpecGenerate for final spec.md streaming"
```

---

## Task 18: MockupPipeline 컨테이너 수정

**Files:**
- Modify: `frontend/src/components/mockup/MockupPipeline.tsx`

- [ ] **Step 1: 4개 Step을 사용하도록 교체**

Replace the entire contents of `frontend/src/components/mockup/MockupPipeline.tsx`:

```tsx
import { useSessionStore } from '../../store/sessionStore'
import Step1Brief from './Step1Brief'
import Step2Mockup from './Step2Mockup'
import Step3Interview from './Step3Interview'
import Step4SpecGenerate from './Step4SpecGenerate'
import StepIndicator from './StepIndicator'

export default function MockupPipeline() {
  const mockupState = useSessionStore((s) => s.mockupState)
  const resetMockup = useSessionStore((s) => s.resetMockup)
  const goToStep = useSessionStore((s) => s.mockupGoToStep)

  const currentStep = mockupState?.currentStep ?? 1

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold font-headline text-on-surface">Mockup 파이프라인</h1>
        {mockupState && (
          <button
            type="button"
            onClick={() => {
              if (confirm('진행 중인 Mockup 작업이 모두 초기화됩니다. 계속하시겠습니까?')) {
                resetMockup()
              }
            }}
            className="text-sm text-on-surface-variant hover:text-error px-3 py-1 rounded-lg hover:bg-error-container/30"
          >
            처음부터 다시
          </button>
        )}
      </div>

      <StepIndicator currentStep={currentStep} onStepClick={goToStep} />

      {currentStep === 1 && <Step1Brief />}
      {currentStep === 2 && <Step2Mockup />}
      {currentStep === 3 && <Step3Interview />}
      {currentStep === 4 && <Step4SpecGenerate />}
    </div>
  )
}
```

- [ ] **Step 2: TypeScript 컴파일 및 빌드 확인**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 기존 Step*AiGenerate.tsx 파일 미참조 에러만 남음 (Task 19에서 해결)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/mockup/MockupPipeline.tsx
git commit -m "feat(ui): switch MockupPipeline to 4-step flow"
```

---

## Task 19: 구 Step 컴포넌트 삭제

**Files:**
- Delete: `frontend/src/components/mockup/Step1AiGenerate.tsx`
- Delete: `frontend/src/components/mockup/Step2Scaffold.tsx`
- Delete: `frontend/src/components/mockup/Step3Annotate.tsx`
- Delete: `frontend/src/components/mockup/Step4Interview.tsx`
- Delete: `frontend/src/components/mockup/Step5InterviewResult.tsx`
- Delete: `frontend/src/components/mockup/Step6SpecGenerate.tsx`

- [ ] **Step 1: 파일 삭제**

Run:
```bash
rm frontend/src/components/mockup/Step1AiGenerate.tsx
rm frontend/src/components/mockup/Step2Scaffold.tsx
rm frontend/src/components/mockup/Step3Annotate.tsx
rm frontend/src/components/mockup/Step4Interview.tsx
rm frontend/src/components/mockup/Step5InterviewResult.tsx
rm frontend/src/components/mockup/Step6SpecGenerate.tsx
```

- [ ] **Step 2: 참조 남아있는지 확인**

Run:
```bash
cd /Users/g1_kang/projects/need-only-prd && grep -rn "Step1AiGenerate\|Step2Scaffold\|Step3Annotate\|Step4Interview\|Step5InterviewResult\|Step6SpecGenerate" frontend/src/ 2>/dev/null
```
Expected: 출력 없음

- [ ] **Step 3: TypeScript 컴파일 확인**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: 에러 없음

- [ ] **Step 4: 프로덕션 빌드 확인**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: 빌드 성공

- [ ] **Step 5: Commit**

```bash
git add -u frontend/src/components/mockup/
git commit -m "chore(ui): remove old 6-step mockup components"
```

---

## Task 20: 최종 통합 테스트

**Files:** 테스트만 (코드 변경 없음)

- [ ] **Step 1: 백엔드 전체 테스트**

Run: `cd backend && source .venv/bin/activate && python -m pytest -v 2>&1 | tail -10`
Expected: 모든 테스트 PASS (기존 text 파이프라인 + 신규 mockup 파이프라인)

- [ ] **Step 2: 프론트엔드 빌드**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: `built in ...s` 성공 메시지

- [ ] **Step 3: E2E 수동 검증 준비**

`./stop.sh && ./start.sh` 실행. 브라우저 `http://localhost:5173` 접속.

**시나리오 A (텍스트 탭 회귀)**:
1. "텍스트 입력" 탭 선택
2. 텍스트 붙여넣기 → "Generate Spec" → SpecViewer 정상 표시
3. ChatPanel, CodeGen 동작 확인

**시나리오 B (Mockup 탭 완주)**:
1. "Mockup 생성" 탭 선택
2. Step1: project_id(ETHICS_REPORT) + project_name(윤리경영) + brief.md 작성 → 다음
3. Step2: "Mockup 생성 시작" → 스트리밍 → iframe에 실제 렌더링된 화면 확인 → v-if 전환 버튼 동작 → 다음
4. Step3: 인터뷰 원문 붙여넣기 → "InterviewNote 생성" → Keep/Change/Add/Out/TBD 표시 → 다음
5. Step4: 입력 요약 확인 → "Spec.md 생성" → SpecViewer로 자동 전환 → Spec 표시
6. CodeGen 파이프라인 동작 확인

**시나리오 C (에러 처리)**:
- `.env`에 `MOCKUP_AOAI_*` 없는 상태에서 Step2 실행 → 에러 메시지("MOCKUP_AOAI_ENDPOINT...")

- [ ] **Step 4: 최종 커밋 (통합)**

모든 파일이 이미 커밋된 상태라면 별도 커밋 불필요. 혹시 누락된 파일이 있다면:

```bash
git status
git add <누락 파일>
git commit -m "chore: final integration cleanup"
```

---

## 최종 Verification Checklist

- [ ] Backend `pytest -v` — 기존 + 신규 모든 테스트 통과
- [ ] Frontend `npm run build` — 에러 없이 빌드 성공
- [ ] `./start.sh` 실행 후 3개 서버(:8001/:5173/:8081) 정상 기동
- [ ] 텍스트 탭 회귀 OK (기존 플로우)
- [ ] Mockup 탭 4단계 완주 OK
- [ ] iframe 안에서 v-if 기반 화면 전환 동작
- [ ] InterviewNote가 Keep/Change/Add/Out/TBD 구조로 렌더링
- [ ] 최종 spec.md가 SpecViewer에 스트리밍되고, 이어서 CodeGenPanel로 연결됨
- [ ] 사내 게이트웨이 미설정 시 명확한 에러 메시지
- [ ] 구 Step*.tsx 파일, vue_generator.py, vue_generator 테스트 모두 삭제됨
