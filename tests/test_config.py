"""The `config` spec, through `skill-graft build --no-install`."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import build, configure, skill, vendored, write_config

Capsys: TypeAlias = pytest.CaptureFixture[str]


def test_home_relative_path(home: Path, capsys: Capsys) -> None:
    skill(home / "skills" / "chisel")
    configure(["own/chisel"], own="~/skills")

    assert build(capsys) == (0, "")
    assert vendored() == {"chisel"}


def test_relative_path_is_taken_from_the_config_folder(
    home: Path, capsys: Capsys
) -> None:
    skill(home / "mine" / "chisel")
    configure(["own/chisel"], own="../../mine")

    assert build(capsys) == (0, "")
    assert vendored() == {"chisel"}


def test_empty_config_builds_nothing(capsys: Capsys) -> None:
    write_config("")

    assert build(capsys) == (0, "")
    assert vendored() == set()


def test_not_initialized(capsys: Capsys) -> None:
    code, err = build(capsys)

    assert code == 1
    assert "skill-graft.toml" in err and "skill-graft init" in err


@pytest.mark.parametrize(
    ("toml", "expected"),
    [
        ('[sources.own]\npath = "~/nowhere"\n', ["'own'", "~/nowhere"]),
        ('entries = ["mp/tdd"]\n', ["mp/tdd", "'mp'"]),
        ('entries = ["tdd"]\n', ["'tdd'"]),
        ('entries = ["/tdd"]\n', ["'/tdd'"]),
        ('entries = ["mp/"]\n', ["'mp/'"]),
        ('entries = ["mp/a/b"]\n', ["'mp/a/b'"]),
        ('[sources.mp]\ngit = "https://x/s.git"\n', ["sources.mp.git", "unsupported"]),
        ('[rename]\n"mp/a" = "b"\n', ["'rename'", "unsupported"]),
        ("entries = [\n", ["skill-graft.toml"]),
        ('entries = "own/chisel"\n', ["'entries'", "list"]),
        ("entries = [1]\n", ["'entries'", "list of strings"]),
        ('sources = "x"\n', ["'sources'"]),
        ("sources = {own = 1}\n", ["'sources.own'"]),
        ("[sources.own]\n", ["'sources.own.path'", "missing"]),
        ("[sources.own]\npath = 1\n", ["'sources.own.path'"]),
        ('[sources."a/b"]\npath = "~/src"\n', ["alias 'a/b'"]),
        ('[sources.".."]\npath = "~/src"\n', ["alias '..'"]),
        ('[sources."-x"]\npath = "~/src"\n', ["alias '-x'"]),
        ('[sources.""]\npath = "~/src"\n', ["alias ''"]),
        (
            'entries = ["own/chisel", "own/chisel"]\n[sources.own]\npath = "~/src"\n',
            ["'own/chisel'", "repeated"],
        ),
        ('[sources.own]\npath = "."\n', ["source 'own'", "skill-graft"]),
        ('[sources.own]\npath = ".apm/skills"\n', ["source 'own'", "skill-graft"]),
        ('[sources.own]\npath = "~/.apm"\n', ["source 'own'", "skill-graft"]),
        ('[sources.own]\npath = "~"\n', ["source 'own'", "skill-graft"]),
    ],
)
def test_config_error_writes_nothing(
    home: Path, capsys: Capsys, toml: str, expected: list[str]
) -> None:
    skill(home / "src" / "chisel")
    configure(["own/chisel"], own="~/src")
    build(capsys)
    write_config(toml)

    code, err = build(capsys)

    assert code == 1
    for text in expected:
        assert text in err
    assert vendored() == {"chisel"}


@pytest.mark.parametrize(
    ("path", "deploy"),
    [
        ("~/.agents/skills", ".agents/skills"),
        ("~/.claude", ".claude/skills"),
        ("~/.config/opencode/skills/x", ".config/opencode/skills"),
    ],
)
def test_source_overlapping_a_deploy_folder_warns(
    home: Path, capsys: Capsys, path: str, deploy: str
) -> None:
    skill(Path(path.replace("~", str(home))) / "chisel")
    configure(["own/chisel"], own=path)

    code, err = build(capsys)

    assert code == 0
    assert err.count("warning:") == 1
    assert "'own'" in err and str(home / deploy) in err
    assert vendored() == {"chisel"}
