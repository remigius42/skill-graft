import subprocess
from pathlib import Path

import pytest

from skill_graft.cli import main

COMMANDS = [
    "init",
    "resolve",
    "build",
    "update",
    "why",
    "tree",
    "add",
    "remove",
    "rename",
    "bind",
    "unbind",
    "help",
]


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    """Runs the CLI; returns its exit code, stdout and stderr, argparse exits included."""
    try:
        code = main(argv)
    except SystemExit as exit:
        code = exit.code if isinstance(exit.code, int) else 1
    out, err = capsys.readouterr()
    return code, out, err


def test_help_lists_commands() -> None:
    result = subprocess.run(
        ["skill-graft", "--help"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "init" in result.stdout
    assert "build" in result.stdout


def test_top_level_help(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["--help"], capsys)
    assert code == 0
    lines = out.splitlines()
    for command in COMMANDS:
        # Each command on a line of its own, with a summary after it.
        assert any(
            line.split()[:1] == [command] and len(line.split()) > 1 for line in lines
        ), command


def test_command_help(capsys: pytest.CaptureFixture[str]) -> None:
    # No ~/.apm/skill-graft/: help never reads the config.
    code, out, _ = run(["update", "--help"], capsys)
    assert code == 0
    assert "branch tip" in out
    assert "--dry-run" in out


def test_help_command_same_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["help", "update"], capsys) == run(["update", "--help"], capsys)
    # Prints tree's help, never runs it: there is no config to resolve.
    code, out, _ = run(["help", "tree"], capsys)
    assert code == 0
    assert "--format" in out
    assert (code, out) == run(["tree", "--help"], capsys)[:2]
    assert run(["help"], capsys) == run(["--help"], capsys)


def test_help_unknown_topic(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["help", "nope"], capsys)
    assert (code, out) == (2, "")
    assert "nope" in err
    assert all(command in err for command in COMMANDS)


def test_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["explain"], capsys)
    assert (code, out) == (2, "")
    assert "explain" in err
    assert all(command in err for command in COMMANDS)


def test_no_command(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run([], capsys)
    assert (code, out) == (2, "")
    assert all(command in err for command in COMMANDS)


def test_help_names_where_the_package_is(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])

    out = " ".join(capsys.readouterr().out.split())
    assert "nearest .apm/skill-graft/ above the working folder" in out
    assert "~/.apm/skill-graft/" in out


def test_bind_help(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["bind", "--help"], capsys)
    assert code == 0
    assert "skill ID" in out and "false" in out


def test_bind_missing_argument(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["bind", "mp/tmp"], capsys)
    assert (code, out) == (2, "")
    assert "target" in err


def test_unbind_help(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["unbind", "--help"], capsys)
    assert code == 0
    assert "resolve by default" in out


def test_unbind_missing_argument(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["unbind"], capsys)
    assert (code, out) == (2, "")
    assert "alias/name" in err


def test_build_help_lists_into(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["build", "--help"], capsys)
    assert code == 0
    assert "[--no-install | --into DIR]" in out


def test_into_with_no_install(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["build", "--into", "d", "--no-install"], capsys)
    assert (code, out) == (2, "")
    assert err.startswith("usage: skill-graft build")
    assert "--into" in err and "--no-install" in err and "package:" not in err


def test_into_without_a_value(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["build", "--into"], capsys)
    assert (code, out) == (2, "")
    assert "--into" in err


def test_into_with_an_empty_value(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = sorted(home.iterdir())
    code, out, err = run(["build", "--into", ""], capsys)
    assert (code, out) == (2, "")
    assert "--into" in err and "package:" not in err
    assert sorted(home.iterdir()) == before
