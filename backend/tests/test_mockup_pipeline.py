import json

import pytest
from unittest.mock import AsyncMock, patch

from app.llm.mockup_pipeline import MockupPipeline, mockup_pipeline


@pytest.mark.asyncio
async def test_ai_generate_parses_json():
    payload = {"screen_id": "CpmsT1", "screen_name": "T1", "fields": [], "tabs": None}
    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value=json.dumps(payload))
        out = await mockup_pipeline.ai_generate("제목", "list", None, None)
    assert out["screen_id"] == "CpmsT1"


def test_scaffold_returns_vue():
    vue = mockup_pipeline.scaffold(
        screen_id="CpmsScratch",
        screen_name="Scratch",
        page_type="list",
        fields=[
            {
                "key": "id",
                "label": "ID",
                "type": "text",
                "searchable": False,
                "listable": True,
                "detailable": False,
                "editable": False,
                "required": True,
            }
        ],
        tabs=None,
    )
    assert "<template" in vue


@pytest.mark.asyncio
async def test_interview_result_with_raw_text():
    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(
            side_effect=[
                '{"k":"v"}',
                "## Interview note",
                '{"merged":"x"}',
                "# Final Spec\n{화면코드}.{대컴포넌트명}.{라벨ID}\n{대컴포넌트명}.{라벨ID}\nt('{대컴포넌트명}.{라벨id}')\ncmn_lbl\non conflict",
            ]
        )
        with patch.object(MockupPipeline, "_has_required_label_rules", return_value=True):
            note, spec = await mockup_pipeline.interview_result(
                title="T",
                annotation_markdown="| h |\n|---|",
                vue_source="<template><div>x</div></template>",
                questions=None,
                answers=None,
                raw_interview_text="raw",
                screen_name="S",
                menu_context=None,
            )
    assert "## Interview" in note
    assert "# Final Spec" in spec


@pytest.mark.asyncio
async def test_generate_spec_streaming():
    fake_spec = (
        "# Spec\n"
        "{화면코드}.{대컴포넌트명}.{라벨ID}\n"
        "{대컴포넌트명}.{라벨ID}\n"
        "t('{대컴포넌트명}.{라벨id}')\n"
        "cmn_lbl\n"
        "on conflict\n"
    )

    with patch("app.llm.mockup_pipeline.mockup_client") as m:
        m.complete = AsyncMock(return_value=fake_spec)
        with patch.object(MockupPipeline, "_has_required_label_rules", return_value=True):
            chunks: list[str] = []
            async for chunk in mockup_pipeline.generate_spec_streaming(
                title="b",
                annotation_markdown="ann",
                interview_note_md="n",
            ):
                chunks.append(chunk)
    assert "".join(chunks) == fake_spec
