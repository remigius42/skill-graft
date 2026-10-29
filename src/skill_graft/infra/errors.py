import contextlib
import os
import sys
from collections.abc import Generator
from typing import TextIO


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
    except BaseException:
        with contextlib.suppress(OSError):  # the block's own error wins
            flush_stdout()
        warn(list(dict.fromkeys(warnings)))
        raise
    else:
        try:
            flush_stdout()
        finally:
            warn(list(dict.fromkeys(warnings)))


def flush_stdout() -> None:
    """Flushes stdout, buffered into a pipe or file, unlike stderr. When that fails,
    the reader having closed it or on any other OSError, discards the rest, so
    Python's flush at exit prints nothing, and raises the error."""
    if sys.stdout is None:  # started with it closed; print writes nowhere
        return
    if sys.stdout.closed:  # closed in the process: nothing left to flush
        return
    try:
        sys.stdout.flush()
    except OSError:
        # Without a file descriptor or os.devnull, the shutdown flush may still
        # complain; the error raised stays the flush's.
        with contextlib.suppress(OSError, ValueError):
            _discard(sys.stdout)
        raise


def _discard(stdout: TextIO) -> None:
    """Points `stdout`'s file descriptor at `os.devnull`."""
    descriptor = stdout.fileno()
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, descriptor)
    finally:
        os.close(devnull)
