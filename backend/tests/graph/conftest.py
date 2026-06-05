"""Shared fixtures for graph integration tests (real gpt-5.5 LLM).

Per project decision, node/graph tests call the REAL gpt-5.5 client. Tests that
need the LLM are marked @pytest.mark.llm and skipped when keys are absent.
"""

import pytest

from app.config import settings


def _llm_available() -> bool:
    return bool(settings.GPT55_AZURE_OPENAI_API_KEY and settings.GPT55_AZURE_OPENAI_ENDPOINT)


@pytest.fixture(autouse=True)
def _skip_llm_when_unavailable(request):
    """Auto-skip any test marked `llm` when gpt-5.5 credentials are missing."""
    if request.node.get_closest_marker("llm") and not _llm_available():
        pytest.skip("gpt-5.5 credentials not configured (GPT55_AZURE_OPENAI_*)")


@pytest.fixture
def guide_stub(monkeypatch):
    """Replace guide loading with a small constant so the generator prompt stays
    small and fast (the guide content itself is exercised in test_guides.py).

    Patches the `guides` module directly — the contract-first nodes (gen_nodes)
    call `guides.load_guide_for_file_type(...)` at generation time."""
    import app.llm.graph.guides as guides_mod
    monkeypatch.setattr(guides_mod, "load_guide_for_file_type",
                        lambda ft: "Follow CPMS conventions. Use String for IDs.")
    return None
