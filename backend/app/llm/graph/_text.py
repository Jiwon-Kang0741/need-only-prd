"""Shared text helpers for the code-generation graph."""

from __future__ import annotations


def strip_fences(text: str) -> str:
    """Remove a leading/trailing markdown code fence from an LLM reply."""
    text = text.strip()
    if text.startswith("```"):
        nl = text.index("\n") if "\n" in text else 3
        text = text[nl + 1:]
    if text.rstrip().endswith("```"):
        text = text.rstrip()[:-3].rstrip()
    return text
