"""Mockup 기반 6단계 spec 생성 파이프라인."""
from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator

from app.llm.mockup_client import mockup_client
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
    # Step 1: AI Generate
    async def ai_generate(self, title: str, page_type: str, description: str | None = None) -> dict:
        """화면 제목 → 필드/컬럼/Mock 설계 JSON."""
        system, user = ai_generate_prompt(page_type, title, description)
        response = await mockup_client.complete(system, user, stream=False)
        return _extract_json(response)

    # Step 2: Scaffold (no LLM)
    def scaffold(self, screen_id: str, screen_name: str, page_type: str, fields: list[dict], tabs: list[dict] | None = None) -> str:
        return generate_vue_page(screen_id=screen_id, screen_name=screen_name, page_type=page_type, fields=fields, tabs=tabs)

    # Step 3: AI Annotate
    async def ai_annotate(self, vue_code: str) -> tuple[str, list[dict], str]:
        """Vue 코드 → (annotated_code, annotations, annotation_markdown)."""
        template_section = self._extract_template(vue_code)
        if not template_section:
            raise ValueError("<template> 블록을 찾을 수 없습니다.")
        analysis_target = template_section[:6000] if len(template_section) > 6000 else template_section
        system, user = annotation_prompt(analysis_target)
        response = await mockup_client.complete(system, user, stream=False)
        annotations = _extract_json(response)
        if not isinstance(annotations, list):
            raise ValueError("LLM이 주석 배열을 반환하지 않았습니다.")
        annotated_code = self._inject_annotations(vue_code, annotations)
        markdown = self._annotations_to_markdown(annotations)
        return annotated_code, annotations, markdown

    # Step 4: AI Interview
    async def ai_interview(self, title: str, annotation_markdown: str | None = None, vue_source: str | None = None, spec_json: dict | None = None) -> list[dict]:
        """주석 + MockUp → 인터뷰 질문 10개."""
        system, user = interview_prompt(title, annotation_markdown, vue_source, spec_json)
        response = await mockup_client.complete(system, user, stream=False)
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

    # Step 5: Interview Result
    async def interview_result(self, title: str, annotation_markdown: str, vue_source: str | None = None, questions: list[dict] | None = None, answers: list[dict] | None = None, raw_interview_text: str | None = None, screen_name: str = "") -> tuple[str, str]:
        """인터뷰 답변 → (interview_note_md, spec_markdown)."""
        if raw_interview_text and raw_interview_text.strip():
            sys_ext, usr_ext = extract_structured_data_prompt(raw_interview_text)
            ext_response = await mockup_client.complete(sys_ext, usr_ext, stream=False)
            interview_data = _extract_json(ext_response)
            sys_note, usr_note = interview_notes_prompt(title, [{"raw_text": raw_interview_text}], screen_name=screen_name)
            interview_note_md = await mockup_client.complete(sys_note, usr_note, stream=False)
        else:
            qa_pairs = []
            if questions and answers:
                for q, a in zip(questions, answers):
                    qa_pairs.append({"question": q.get("question", ""), "answer": a.get("answer", ""), "category": q.get("category", "")})
            sys_note, usr_note = interview_notes_prompt(title, qa_pairs, screen_name=screen_name)
            interview_note_md = await mockup_client.complete(sys_note, usr_note, stream=False)
            sys_ext, usr_ext = extract_structured_data_prompt(interview_note_md)
            ext_response = await mockup_client.complete(sys_ext, usr_ext, stream=False)
            interview_data = _extract_json(ext_response)

        sys_merge, usr_merge = merge_annotations_prompt(annotation_markdown, interview_data)
        merged_annotations = await mockup_client.complete(sys_merge, usr_merge, stream=False)

        sys_spec, usr_spec = master_spec_prompt(title=title, annotation_markdown=merged_annotations, interview_note_md=interview_note_md, vue_source=vue_source)
        spec_markdown = await mockup_client.complete(sys_spec, usr_spec, stream=False)
        return interview_note_md, spec_markdown

    # Step 6: Streaming spec generation
    async def generate_spec_streaming(self, title: str, annotation_markdown: str, interview_note_md: str | None = None, vue_source: str | None = None) -> AsyncIterator[str]:
        import asyncio as _asyncio
        sys_spec, usr_spec = master_spec_prompt(title=title, annotation_markdown=annotation_markdown, interview_note_md=interview_note_md, vue_source=vue_source)
        content = await mockup_client.complete(sys_spec, usr_spec, stream=False)
        if not content:
            return
        chunk_size = 200
        for i in range(0, len(content), chunk_size):
            yield content[i : i + chunk_size]
            await _asyncio.sleep(0)

    # Helpers
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
