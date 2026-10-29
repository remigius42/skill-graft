import contextlib
import sys
from collections.abc import Generator


class SkillGraftError(Exception):
    """A failure the user can act on; the CLI prints its message and exits 1."""


def warn(warnings: list[str]) -> None:
    """Prints each warning to stderr; the command goes on."""
    for warning in warnings:
        print(f"skill-graft: warning: {warning}", file=sys.stderr)


def notice(text: str) -> None:
    """Prints a notice to stderr, beside the warnings; the command goes on."""
    print(f"skill-graft: {text}", file=sys.stderr)


@contextlib.contextmanager
def warnings_last() -> Generator[list[str]]:
    """A list a command adds its warnings to; on exit, also on failure, prints each
    distinct one, in the order first added, after all else but the error line."""
    warnings: list[str] = []
    try:
        yield warnings
    finally:
        sys.stdout.flush()  # into a pipe or file, stdout is buffered; stderr is not
        warn(list(dict.fromkeys(warnings)))
