"""Vets one skill as deployed: the lines worth reading before trusting it, as flags.

Patterns, never a verdict: a flag is no fault, and no flag is no pass.
"""

from dataclasses import dataclass

from skill_graft.pipeline.deployed import View

# Each category's risk IDs: the OWASP Top 10 for LLM Applications 2025 (LLM) and
# for Agentic Applications 2026 (ASI).
OWASP = {
    "read": ("LLM02",),
    "write": ("ASI02",),
    "send": ("LLM02", "ASI02"),
    "run": ("ASI05",),
    "privilege": ("ASI03",),
    "persistence": ("ASI06",),
    "permission": ("ASI02",),
    "unreviewable": ("LLM03",),
}


@dataclass(frozen=True)
class Flag:
    """A pattern found at a line of a file; line 0 is the file as a whole."""

    file: str
    line: int
    pattern: str  # `<category>.<what>`

    @property
    def category(self) -> str:
        return self.pattern.split(".", 1)[0]


def scan(view: View) -> list[Flag]:
    """Each flag of the skill whose deployed files `view` holds."""
    return []
