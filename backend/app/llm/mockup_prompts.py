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
