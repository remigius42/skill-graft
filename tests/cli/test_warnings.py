"""Every command prints its warnings last: after its output, notices and APM's."""

import io
import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from conftest import FakeApm, Upstream, skill, write_config

from skill_graft.cli import main
from skill_graft.pipeline import lock

FOO = "skill-graft: warning: `own/tdd` calls `/foo`"
OVERLAP = "skill-graft: warning: source 'own'"


@contextmanager
def combined(file: Path) -> Iterator[None]:
    """stdout and stderr, Python's and a subprocess's, into `file` as written."""
    sys.stdout.flush()
    sys.stderr.flush()
    saved = os.dup(1), os.dup(2), sys.stdout, sys.stderr
    with open(file, "wb", buffering=0) as raw:
        stream = io.TextIOWrapper(raw, write_through=True)
        os.dup2(raw.fileno(), 1)
        os.dup2(raw.fileno(), 2)
        sys.stdout = sys.stderr = stream
        try:
            yield
        finally:
            sys.stdout, sys.stderr = saved[2], saved[3]
            os.dup2(saved[0], 1)
            os.dup2(saved[1], 2)
            os.close(saved[0])
            os.close(saved[1])
            stream.detach()


def run(tmp_path: Path, *args: str) -> tuple[int, str]:
    """`skill-graft args`'s exit code and everything it and APM printed, in order."""
    file = tmp_path / "output"
    with combined(file):
        code = main(list(args))
    return code, file.read_text()


def in_order(text: str, *parts: str) -> None:
    """Each part appears once, and in this order."""
    for part in parts:
        assert text.count(part) == 1, (part, text)
    positions = [text.index(part) for part in parts]
    assert positions == sorted(positions), text


def calls_foo(home: Path) -> None:
    """`own/tdd` calls `/foo`, which no source has, and mentions `notes` in prose."""
    skill(home / "src" / "tdd", "Run /foo. See `notes`.\n")
    skill(home / "src" / "notes")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')


def overlapping(home: Path, entries: str = "[]") -> None:
    """Source `own` is `~/.agents/skills`, where APM deploys: a config warning."""
    skill(home / ".agents" / "skills" / "chisel")
    write_config(f'entries = {entries}\n[sources.own]\npath = "~/.agents/skills"\n')


def test_resolve(home: Path, tmp_path: Path) -> None:
    calls_foo(home)

    code, text = run(tmp_path, "resolve")

    assert code == 0
    in_order(text, "\nown/tdd\n", "mentioned in prose", "  own/notes, by own/tdd", FOO)


def test_resolve_through_a_pipe(home: Path) -> None:
    """Python buffers stdout into a pipe, not stderr; the order holds even so."""
    calls_foo(home)

    result = subprocess.run(
        [sys.executable, "-m", "skill_graft.cli", "resolve"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    in_order(result.stdout, "\nown/tdd\n", "  own/notes, by own/tdd", FOO)


def test_build(home: Path, tmp_path: Path, fake_apm: FakeApm) -> None:
    calls_foo(home)

    code, text = run(tmp_path, "build")

    assert code == 0
    in_order(text, "fake apm: install", FOO)


def test_update(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    old = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    upstream.commit({"tdd/SKILL.md": "Run /foo.\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{old}"\n'
    )

    code, text = run(tmp_path, "update", "--dry-run")

    assert code == 0
    foo = "skill-graft: warning: `mp/tdd` calls `/foo`"
    in_order(text, "~ mp/tdd", "dry run:", foo)


def test_edit_with_a_notice(home: Path, tmp_path: Path) -> None:
    skill(home / "src" / "tdd", "Run /grilling and /foo.\n")
    skill(home / "src" / "grilling")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    code, text = run(tmp_path, "add", "own/grilling")

    assert code == 0
    in_order(text, "\nown/tdd\n", "was already in the hull, via `own/tdd`", FOO)


def test_config_warning(home: Path, tmp_path: Path) -> None:
    overlapping(home, '["own/chisel"]')

    code, text = run(tmp_path, "resolve")

    assert code == 0
    in_order(text, "own/chisel\n", OVERLAP)


def test_edit_fails_before_resolving(home: Path, tmp_path: Path) -> None:
    overlapping(home)

    code, text = run(tmp_path, "unbind", "own/x")

    assert code == 1
    in_order(text, OVERLAP, "skill-graft: `own/x` is not bound")


def test_failing_command(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls_foo(home)

    def fail(text: str, file: Path | None = None) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    code, text = run(tmp_path, "resolve")

    assert code == 1
    in_order(text, FOO, "skill-graft: disk full\n")
    assert text.endswith("skill-graft: disk full\n")


def test_no_op_edit_prints_only_its_notice(home: Path, tmp_path: Path) -> None:
    overlapping(home, '["own/chisel"]')

    code, text = run(tmp_path, "add", "own/chisel")

    assert code == 0
    package = home / ".apm" / "skill-graft"
    assert text == (
        f"skill-graft: package: {package}\n"
        "skill-graft: `own/chisel` is already an entry\n"
    )
