import errno
import io
import json
import os
import subprocess
import sys
import sysconfig
from importlib import metadata
from pathlib import Path

import pytest
from conftest import FakeApm, write_config

from skill_graft import cli
from skill_graft.cli import main

COMMANDS = [
    "init",
    "resolve",
    "deploy",
    "update",
    "why",
    "tree",
    "add",
    "remove",
    "rename",
    "bind",
    "unbind",
    "vet",
    "help",
]


def run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    """Runs the CLI; returns its exit code, stdout and stderr, argparse exits
    included."""
    try:
        code = main(argv)
    except SystemExit as exit:
        code = exit.code if isinstance(exit.code, int) else 1
    out, err = capsys.readouterr()
    return code, out, err


def run_installed(*args: str) -> subprocess.CompletedProcess[str]:
    """Runs the `skill-graft` script installed for the interpreter running the suite,
    whatever `PATH` holds."""
    script = Path(sysconfig.get_path("scripts")) / "skill-graft"
    return subprocess.run([script, *args], capture_output=True, text=True, check=False)


def test_help_lists_commands() -> None:
    result = run_installed("--help")
    assert result.returncode == 0
    assert "init" in result.stdout
    assert "deploy" in result.stdout


def test_top_level_help(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["--help"], capsys)
    assert code == 0
    lines = out.splitlines()
    for command in COMMANDS:
        # Each command on a line of its own, with a summary after it.
        assert any(
            line.split()[:1] == [command] and len(line.split()) > 1 for line in lines
        ), command


def test_help_wrapped_at_the_terminal_width(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The description and each argument's help, after the usage, which argparse wraps
    itself: at the terminal's width less 2."""
    monkeypatch.setenv("COLUMNS", "50")
    for command in COMMANDS:
        code, out, _ = run([command, "--help"], capsys)
        assert code == 0
        _, after_usage = out.split("\n\n", 1)
        assert max(len(line) for line in after_usage.splitlines()) <= 48, command


def test_command_help(capsys: pytest.CaptureFixture[str]) -> None:
    # No ~/.apm/skill-graft/: help never reads the config.
    code, out, _ = run(["update", "--help"], capsys)
    assert code == 0
    assert "branch tip" in out
    assert "--dry-run" in out
    assert "--expect hull-digest" in out and "DIGEST" not in out
    code, out, _ = run(["deploy", "--help"], capsys)
    assert code == 0 and "what skill-graft.lock records" in " ".join(out.split())
    code, out, _ = run(["resolve", "--help"], capsys)
    assert code == 0 and "vendor" in out


def test_help_command_same_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["help", "update"], capsys) == run(["update", "--help"], capsys)
    # Prints tree's help, never runs it: there is no config to resolve.
    code, out, _ = run(["help", "tree"], capsys)
    assert code == 0
    assert "--format" in out
    assert (code, out) == run(["tree", "--help"], capsys)[:2]
    assert run(["help"], capsys) == run(["--help"], capsys)


def flat(text: str) -> str:
    return " ".join(text.split())


def test_every_help_text_shown(capsys: pytest.CaptureFixture[str]) -> None:
    for key, text in cli._TEXT.items():
        # `<command>` is its summary, in the top level's help; `<command>: description`
        # and `<command> <argument>` are in the command's own.
        command = key.split(":")[0].split(" ")[0]
        own = " " in key and command != "skill-graft"

        code, out, _ = run([command, "--help"] if own else ["--help"], capsys)

        assert code == 0
        if not (" " in key and ":" not in key):
            assert flat(text) in flat(out), key
            continue
        # An argument's: among the arguments, below the description, once for each
        # argument whose help holds it (`<source alias>/<name>` is in two of bind's).
        sections = [out.find(h) for h in ("arguments:", "options:") if h in out]
        arguments = flat(out[min(sections) :])
        holding = [
            other
            for other, its in cli._TEXT.items()
            if other.startswith(f"{command} ") and flat(text) in flat(its)
        ]
        assert arguments.count(flat(text)) >= len(holding), key


def test_command_option_never_abbreviated(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(["update", "--dry"], capsys)

    assert code == 2 and "--dry" in err


@pytest.mark.parametrize(("value", "code"), [("text", 0), ("mermaid", 0), ("nope", 2)])
def test_tree_format_choices(
    capsys: pytest.CaptureFixture[str], value: str, code: int
) -> None:
    assert run(["tree", "--format", value, "--help"], capsys)[0] == code


def test_usage_error_lists_each_command_on_a_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, _, err = run(["nope"], capsys)

    lines = err.split("commands:\n")[1].splitlines()
    assert sorted(line.split()[0] for line in lines) == sorted(COMMANDS)


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


def test_old_command(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = sorted(home.iterdir())
    code, out, err = run(["build"], capsys)
    assert (code, out) == (2, "")
    assert "'build'" in err
    assert all(command in err for command in COMMANDS)
    assert sorted(home.iterdir()) == before


def test_old_install_option(
    fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out, err = run(["deploy", "--no-install"], capsys)
    assert (code, out) == (2, "")
    assert "--no-install" in err and "package:" not in err
    assert fake_apm.calls == []


def test_old_diff_option(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["update", "--dry-run", "--diff", "review.diff"], capsys)
    assert (code, out) == (2, "")
    assert "--diff" in err and "package:" not in err
    assert not (home / "review.diff").exists()


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


def test_vet_help(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["vet", "--help"], capsys)
    flat = " ".join(out.split())
    assert code == 0
    assert "patches and renames applied" in flat
    assert "never the text it matched" in flat
    assert "a flag is not a fault" in flat
    assert "<source alias>/<name>" in flat
    assert "[--into DIR]" in out
    assert "DIR/<alias>/<name>/" in flat and "empty folder" in flat


def test_unbind_missing_argument(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["unbind"], capsys)
    assert (code, out) == (2, "")
    assert "alias/name" in err


def test_deploy_help_lists_into(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(["deploy", "--help"], capsys)
    assert code == 0
    assert "[--no-apm-install | --into DIR]" in out


def test_into_with_no_apm_install(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["deploy", "--into", "d", "--no-apm-install"], capsys)
    assert (code, out) == (2, "")
    assert err.startswith("usage: skill-graft deploy")
    assert "--into" in err and "--no-apm-install" in err and "package:" not in err


def test_into_without_a_value(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, err = run(["deploy", "--into"], capsys)
    assert (code, out) == (2, "")
    assert "--into" in err


@pytest.mark.parametrize("command", ["deploy", "vet"])
def test_into_with_an_empty_value(
    home: Path, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    before = sorted(home.iterdir())
    code, out, err = run([command, "--into", ""], capsys)
    assert (code, out) == (2, "")
    assert "--into" in err and "package:" not in err
    assert sorted(home.iterdir()) == before


def test_prefix_of_an_option(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = sorted(home.iterdir())
    code, out, err = run(["update", "--dry"], capsys)
    assert (code, out) == (2, "")
    assert "--dry" in err and "package:" not in err
    assert sorted(home.iterdir()) == before


def test_option_in_full(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = write_config("entries = []\n")
    package = sorted(config.parent.iterdir())

    code, out, _ = run(["update", "--dry-run"], capsys)

    assert code == 0
    assert "dry run:" in out
    assert sorted(config.parent.iterdir()) == package


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


def test_version_of_a_git_install_at_an_upper_case_commit(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, "0.2.0", vcs(commit_id=COMMIT.upper()))
    assert run(["--version"], capsys)[1] == "skill-graft 0.2.0 (E294A0E)\n"


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


@pytest.mark.parametrize(
    "revision",
    [
        "main\nfoo",
        "\x1b[2J",
        "main\u202e",
        "\u30d6\u30e9\u30f3\u30c1",
        "main @ abc1234",
    ],
)
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


def test_version_of_an_unreadable_origin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    broken(monkeypatch, "direct_url.json", OSError(errno.EIO, os.strerror(errno.EIO)))
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


def test_version_of_an_origin_in_a_symlink_loop(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    dist_info = tmp_path / "skill_graft-0.2.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text("Name: skill-graft\nVersion: 0.2.0\n")
    (dist_info / "direct_url.json").symlink_to("direct_url.json")
    monkeypatch.setattr(
        metadata, "distribution", lambda name: metadata.PathDistribution(dist_info)
    )
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


def test_version_of_unreadable_metadata(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    broken(monkeypatch, "METADATA", OSError(errno.EIO, os.strerror(errno.EIO)))
    assert run(["--version"], capsys) == (0, "skill-graft unknown\n", "")


def test_version_of_metadata_not_utf8(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    dist_info = tmp_path / "skill_graft-0.2.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_bytes(b"Name: skill-graft\nVersion: 0.2.0\xff\n")
    monkeypatch.setattr(
        metadata, "distribution", lambda name: metadata.PathDistribution(dist_info)
    )
    assert run(["--version"], capsys) == (0, "skill-graft unknown\n", "")


@pytest.mark.filterwarnings("error::DeprecationWarning")
@pytest.mark.parametrize(
    "version",
    [None, "0.2.0\n foo", "0.2.0\x1b[2J", "0.2.\u00fc", "0.2.0 (main @ abc1234)"],
)
def test_version_of_an_odd_version(
    version: str | None,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(monkeypatch, version)
    assert run(["--version"], capsys) == (0, "skill-graft unknown\n", "")


def test_version_padded_with_whitespace(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, " 0.2.0 ")
    assert run(["--version"], capsys) == (0, "skill-graft 0.2.0\n", "")


def test_unknown_version_of_a_git_install(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    install(monkeypatch, None, vcs(commit_id=COMMIT, requested_revision="main"))
    assert run(["--version"], capsys)[1] == "skill-graft unknown (main @ e294a0e)\n"


def test_version_of_this_installation() -> None:
    result = run_installed("--version")
    assert result.returncode == 0
    assert result.stdout.split()[:2] == ["skill-graft", metadata.version("skill-graft")]


WINDOWS = "skill-graft: native Windows is unsupported: run skill-graft in WSL\n"

# Stands in for native Windows: no command module may load, as one may import a
# POSIX-only module, and `fcntl` is missing. `win32` comes after the import: set
# before, the standard library's own modules take their Windows branches and fail.
ON_WINDOWS = """
import sys
sys.modules["skill_graft.commands"] = None
sys.modules["fcntl"] = None
from skill_graft.cli import main
sys.platform = "win32"
sys.exit(main(sys.argv[1:]))
"""


def on_windows(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", ON_WINDOWS, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_native_windows_refused() -> None:
    result = on_windows("resolve")
    assert (result.returncode, result.stdout, result.stderr) == (1, "", WINDOWS)


def test_native_windows_refused_in_process(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """As above, in this process, which loads mutmut's mutants: a subprocess loads
    the checkout."""
    monkeypatch.setattr(sys, "platform", "win32")
    assert run(["resolve"], capsys) == (1, "", WINDOWS)


@pytest.mark.parametrize("args", [["help"], ["--help"], ["--version"]])
def test_native_windows_refuses_help_and_version(args: list[str]) -> None:
    result = on_windows(*args)
    assert (result.returncode, result.stdout, result.stderr) == (1, "", WINDOWS)


@pytest.mark.parametrize("args", [[], ["explain"], ["--bogus"]])
def test_native_windows_refuses_usage_errors(args: list[str]) -> None:
    result = on_windows(*args)
    assert (result.returncode, result.stdout, result.stderr) == (1, "", WINDOWS)


class FlushFails(io.StringIO):
    """A stdout whose reader has closed it, its buffer large enough for what is
    printed: each write succeeds, the flush fails."""

    def flush(self) -> None:
        raise BrokenPipeError(32, "Broken pipe")


BROKEN_PIPE = "skill-graft: [Errno 32] Broken pipe\n"


@pytest.mark.usefixtures("discards")
def test_failed_flush_fails_a_command(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdout", FlushFails())
    assert main(["help"]) == 1
    assert capsys.readouterr().err == BROKEN_PIPE


@pytest.mark.usefixtures("discards")
def test_failed_flush_fails_an_argparse_exit(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--help` exits through `SystemExit(0)`; its code is checked as is, as `run`
    would read a `None` as 1."""
    monkeypatch.setattr(sys, "stdout", FlushFails())
    with pytest.raises(SystemExit) as exit:
        main(["--help"])
    assert exit.value.code == 1
    assert capsys.readouterr().err == BROKEN_PIPE


@pytest.mark.usefixtures("discards")
def test_failed_flush_keeps_a_usage_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stdout", FlushFails())
    code, _, err = run(["explain"], capsys)
    assert code == 2
    assert "invalid choice: 'explain'" in err
    assert "Broken pipe" not in err
