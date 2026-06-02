"""Graph execution constants."""

# Reviewer ReAct loop: hard-cap backstop (convergence is primary exit).
REVIEWER_HARD_CAP = 6

# Per-file static_check gate: regenerate at most this many times.
GATE_MAX_REGEN = 1

# Max tool calls the reviewer may issue in a single ReAct turn batch.
REVIEWER_MAX_TOOLS_PER_TURN = 8
