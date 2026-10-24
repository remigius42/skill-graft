import errno
import json
import os
import subprocess
from importlib import metadata
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


class FakeDistribution(metadata.Distribution):
    """An installed skill-graft, as `importlib.metadata` finds it: its METADATA names
    `version`, or no version for None."""

    def __init__(self, version: str | None, direct_url: str | None = None) -> None:
        self.metadata_text = "Name: skill-graft\n" + (
            f"Version: {version}\n" if version is not None else ""
        )
        self.direct_url = direct_url

    def read_text(self, filename: str) -> str | None:
        if filename == "METADATA":
            return self.metadata_text
        return self.direct_url if filename == "direct_url.json" else None

    def locate_file(self, path: str | os.PathLike[str]) -> Path:
        return Path(path)


def install(
    monkeypatch: pytest.MonkeyPatch, version: str | None, direct_url: str | None = None
) -> None:
    """Fakes the installed distribution, whatever installer ran the suite."""
    monkeypatch.setattr(
        metadata, "distribution", lambda name: FakeDistribution(version, direct_url)
    )


def broken(monkeypatch: pytest.MonkeyPatch, file: str, error: Exception) -> None:
    """Fakes skill-graft 0.2.0 installed, reading whose `file` raises `error`."""

    class Broken(FakeDistribution):
        def read_text(self, filename: str) -> str | None:
            if filename == file:
                raise error
            return super().read_text(filename)

    monkeypatch.setattr(metadata, "distribution", lambda name: Broken("0.2.0"))


def test_version_of_a_release(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0")
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


def test_version_never_reads_the_config(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0")
    project = Path.cwd() / "project"
    (project / ".apm" / "skill-graft").mkdir(parents=True)
    (project / ".apm" / "skill-graft" / "skill-graft.toml").write_text("[not toml\n")
    monkeypatch.chdir(project)
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


def test_help_lists_version(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["--help"], capsys)
    assert code == 0
    assert "--version" in out


COMMIT = "e294a0e5f3c1d2b4a6978877665544332211aabb"
URL = "https://github.com/remigius42/skill-graft"


def vcs(**vcs_info: object) -> str:
    """A git install's direct_url.json, as PEP 610 has it."""
    return json.dumps({"url": URL, "vcs_info": {"vcs": "git", **vcs_info}})


def test_version_of_a_git_install(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=COMMIT))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0 (e294a0e)\n"


def test_version_of_a_git_install_at_a_branch(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=COMMIT, requested_revision="main"))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0 (main @ e294a0e)\n"


@pytest.mark.parametrize("pinned", [COMMIT, "e294a0e", "E294A0E"])
def test_version_of_a_git_install_at_a_commit(
    pinned: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=COMMIT, requested_revision=pinned))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0 (e294a0e)\n"


def test_version_of_another_version_control(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    direct_url = json.dumps(
        {"url": URL, "vcs_info": {"vcs": "hg", "commit_id": COMMIT}}
    )
    install(monkeypatch, "0.2.0", direct_url)
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0\n"


@pytest.mark.parametrize("revision", ["", None, 123])
def test_version_without_a_usable_revision(
    revision: object,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=COMMIT, requested_revision=revision))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0 (e294a0e)\n"


@pytest.mark.parametrize(
    "direct_url",
    [
        "not json",
        "[]",
        json.dumps({"url": "file:///src", "dir_info": {"editable": True}}),
        json.dumps({"url": URL, "vcs_info": "git"}),
        vcs(),
        vcs(commit_id=7),
        vcs(commit_id=""),
    ],
)
def test_version_of_an_unexpected_origin(
    direct_url: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, "0.2.0", direct_url)
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


def test_version_of_a_branch_named_like_the_commit(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=COMMIT, requested_revision="e2"))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0 (e2 @ e294a0e)\n"


@pytest.mark.parametrize("revision", ["main\nfoo", "\x1b[2J", "main‮", "ブランチ"])
def test_version_of_a_revision_not_printable_ascii(
    revision: str,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=COMMIT, requested_revision=revision))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0 (e294a0e)\n"


@pytest.mark.parametrize("commit", ["abc) x", "\x1b[2J" + COMMIT, "e294a0"])
def test_version_of_a_commit_not_a_hash(
    commit: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=commit, requested_revision="main"))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0\n"


def test_version_of_an_undecodable_origin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    broken(
        monkeypatch,
        "direct_url.json",
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
    )
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


@pytest.mark.parametrize("code", [errno.ELOOP, errno.EIO])
def test_version_of_an_unreadable_origin(
    code: int, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    broken(monkeypatch, "direct_url.json", OSError(code, os.strerror(code)))
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


def test_version_of_a_deeply_nested_origin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0", "[" * 100_000 + "]" * 100_000)
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


def test_version_when_not_installed(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(name: str) -> metadata.Distribution:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "distribution", missing)
    assert run(["--version"], capsys) == (0, "skill-graft unknown\n", "")


@pytest.mark.parametrize(
    "error",
    [
        OSError(errno.EIO, os.strerror(errno.EIO)),
        UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
    ],
)
def test_version_of_unreadable_metadata(
    error: Exception,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken(monkeypatch, "METADATA", error)
    assert run(["--version"], capsys) == (0, "skill-graft unknown\n", "")


@pytest.mark.filterwarnings("error::DeprecationWarning")
@pytest.mark.parametrize("version", [None, "0.2.0\n foo", "0.2.0\x1b[2J", "0.2.ü"])
def test_version_of_an_odd_version(
    version: str | None,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, version)
    assert run(["--version"], capsys) == (0, "skill-graft unknown\n", "")


def test_unknown_version_of_a_git_install(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, None, vcs(commit_id=COMMIT, requested_revision="main"))
    assert run(["--version"], capsys)[1] == "skill-graft unknown (main @ e294a0e)\n"


def test_version_of_this_installation() -> None:
    result = subprocess.run(
        ["skill-graft", "--version"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert result.stdout.startswith(f"skill-graft {metadata.version('skill-graft')}")
