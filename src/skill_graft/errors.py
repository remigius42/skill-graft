import sys


class SkillGraftError(Exception):
    """A failure the user can act on; the CLI prints its message and exits 1."""


def warn(warnings: list[str]) -> None:
    """Prints each warning to stderr; the command goes on."""
    for warning in warnings:
        print(f"skill-graft: warning: {warning}", file=sys.stderr)
