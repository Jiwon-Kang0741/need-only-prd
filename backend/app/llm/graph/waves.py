"""Fixed wave assignment for file types (deterministic, not LLM-decided).

Wave 1: leaf files derivable directly from contract (no inter-dependency).
Wave 2: files depending on wave-1 DTO/types.
Wave 3: files depending on wave-2 DAO method names.
"""

from __future__ import annotations

MAX_WAVE = 3

_WAVE_MAP: dict[str, int] = {
    # wave 1 — leaf
    "db_init_sql": 1,
    "dto_request": 1,
    "dto_response": 1,
    "vue_types": 1,
    # wave 2 — depend on DTO/types
    "dao": 2,
    "dao_impl": 2,
    "mapper_xml": 2,
    "vue_page": 2,
    # wave 3 — depend on DAO method names
    "service": 3,
    "service_impl": 3,
}


def wave_for_file_type(file_type: str) -> int:
    """Return the fixed wave for a file type. Unknown types run last (see everything)."""
    return _WAVE_MAP.get(file_type, MAX_WAVE)


def files_in_wave(plan: dict, wave: int) -> list[dict]:
    """Return plan file specs assigned to the given wave."""
    return [f for f in plan.get("files", [])
            if wave_for_file_type(f["file_type"]) == wave]
