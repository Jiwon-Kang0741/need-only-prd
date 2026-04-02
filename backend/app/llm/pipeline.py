import json
from collections.abc import AsyncIterator

from app.llm.client import llm_client
from app.llm.prompts import (
    extraction_prompt,
    generation_prompt,
    refinement_prompt,
    summarization_prompt,
    validation_prompt,
)
from app.models import ChatMessage


class SpecPipeline:
    async def extract_requirements(self, raw_text: str) -> dict:
        system, user = extraction_prompt(raw_text)
        response = await llm_client.complete(system, user, stream=False)
        return json.loads(response)

    async def generate_spec(self, requirements: dict, raw_text: str) -> AsyncIterator[str]:
        requirements_json = json.dumps(requirements, indent=2)
        system, user = generation_prompt(requirements_json, raw_text)
        stream = await llm_client.complete(system, user, stream=True)
        async for chunk in stream:
            yield chunk

    async def _build_history_context(self, chat_history: list[ChatMessage]) -> str:
        # A "round" is a pair of user + assistant messages (2 messages per round)
        round_count = len(chat_history) // 2
        if round_count <= 5:
            return "\n".join(f"{msg.role}: {msg.content}" for msg in chat_history)

        # Summarize older messages, keep last 2 rounds (4 messages) in full
        older = chat_history[:-4]
        recent = chat_history[-4:]
        older_str = "\n".join(f"{msg.role}: {msg.content}" for msg in older)
        system, user = summarization_prompt(older_str)
        summary = await llm_client.complete(system, user, stream=False)
        recent_str = "\n".join(f"{msg.role}: {msg.content}" for msg in recent)
        return f"[Summary of earlier conversation]\n{summary}\n\n[Recent messages]\n{recent_str}"

    async def refine_spec(
        self,
        current_spec: str,
        chat_history: list[ChatMessage],
        new_message: str,
    ) -> AsyncIterator[str]:
        history_str = await self._build_history_context(chat_history)
        system, user = refinement_prompt(current_spec, history_str, new_message)
        stream = await llm_client.complete(system, user, stream=True)
        async for chunk in stream:
            yield chunk

    async def validate_coverage(
        self, raw_text: str, spec_markdown: str, requirements: dict
    ) -> dict:
        requirements_json = json.dumps(requirements, indent=2)
        system, user = validation_prompt(raw_text, spec_markdown, requirements_json)
        response = await llm_client.complete(system, user, stream=False)
        return json.loads(response)


spec_pipeline = SpecPipeline()
