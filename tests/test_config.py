"""The `config` spec, through `skill-graft build --no-install`."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import build, configure, skill, vendored, write_config

from skill_graft import config

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


def test_config_not_utf8(capsys: Capsys) -> None:
    write_config("").write_bytes(b'entries = ["\xff"]\n')

    code, err = build(capsys)

    assert code == 1 and "skill-graft.toml" in err


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
        (
            '[sources.mp]\ngit = "/srv/s"\ntag = "v1"\n',
            ["sources.mp.tag", "unsupported"],
        ),
        ('[sources.mp]\npath = "~/src"\ngit = "/srv/s"\n', ["'sources.mp'", "both"]),
        (
            '[sources.own]\npath = "~/src"\nref = "a"\n',
            ["sources.own.ref", "unsupported"],
        ),
        ('[sources.mp]\ngit = "../skills"\n', ["'sources.mp.git'"]),
        ('[sources.mp]\ngit = "~/skills"\n', ["'sources.mp.git'"]),
        ('[sources.mp]\ngit = "--upload-pack=touch x"\n', ["'sources.mp.git'"]),
        ('[sources.mp]\ngit = "ext::sh -c touch% x"\n', ["'sources.mp.git'"]),
        ('[sources.mp]\ngit = "foo://x"\n', ["'sources.mp.git'"]),
        ("[sources.mp]\ngit = 1\n", ["'sources.mp.git'"]),
        ('[sources.mp]\ngit = "/srv/s"\nref = "abc1234"\n', ["'sources.mp.ref'", "40"]),
        ('[sources.mp]\ngit = "/srv/s"\nref = 1\n', ["'sources.mp.ref'"]),
        (
            '[sources.mp]\ngit = "/srv/s"\nbranch = "refs/heads/main"\n',
            ["'sources.mp.branch'"],
        ),
        ('[sources.mp]\ngit = "/srv/s"\nbranch = ""\n', ["'sources.mp.branch'"]),
        ('[sources.mp]\ngit = "/srv/s"\nbranch = "-x"\n', ["'sources.mp.branch'"]),
        ('[rename]\n"mp/a" = "b"\n', ["'rename'", "unsupported"]),
        ("entries = [\n", ["skill-graft.toml"]),
        ('entries = "own/chisel"\n', ["'entries'", "list"]),
        ("entries = [1]\n", ["'entries'", "list of strings"]),
        ('sources = "x"\n', ["'sources'"]),
        ("sources = {own = 1}\n", ["'sources.own'"]),
        ("[sources.own]\n", ["'sources.own'", "'path' or 'git'"]),
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


SHA1 = "a" * 40
SHA256 = "b" * 64


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/s.git",
        "http://example.com/s.git",
        "ssh://git@example.com/s.git",
        "git://example.com/s.git",
        "file:///srv/s",
        "git@example.com:me/s.git",
        "example.com:me/s.git",
        "/srv/skills",
    ],
)
def test_git_source_forms_load(url: str) -> None:
    write_config(f'[sources.mp]\ngit = "{url}"\n')

    assert config.load().sources == {"mp": config.GitSource(url, None, None)}


def test_git_source_with_branch_and_ref_loads() -> None:
    write_config(
        f'[sources.a]\ngit = "/srv/a"\nbranch = "dev"\nref = "{SHA1}"\n'
        f'[sources.b]\ngit = "/srv/b"\nref = "{SHA256}"\n'
    )

    assert config.load().sources == {
        "a": config.GitSource("/srv/a", "dev", SHA1),
        "b": config.GitSource("/srv/b", None, SHA256),
    }


def test_uppercase_ref_is_rejected(capsys: Capsys) -> None:
    write_config(f'[sources.mp]\ngit = "/srv/s"\nref = "{SHA1.upper()}"\n')

    code, err = build(capsys)

    assert code == 1 and "'sources.mp.ref'" in err
