"""The `config` spec, through `skill-graft build --no-install`."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import build, configure, skill, vendored, write_config

from skill_graft.pipeline import config

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


def test_valid_bind_loads(home: Path) -> None:
    (home / "a").mkdir()
    (home / "b").mkdir()
    write_config(
        '[sources.mp]\npath = "~/a"\n[sources.own]\npath = "~/b"\n'
        '[bind]\n"mp/grilling" = "own/grill"\n"mp/tmp" = false\n'
    )

    assert config.load().binds == {
        config.SkillId("mp", "grilling"): config.SkillId("own", "grill"),
        config.SkillId("mp", "tmp"): None,
    }


@pytest.mark.parametrize(
    ("bind", "expected"),
    [
        ('"mp/grilling" = "nope/grill"', ['bind."mp/grilling"', "'nope'"]),
        ('"nope/grilling" = "own/grill"', ['bind."nope/grilling"', "'nope'"]),
        ('"mp/grilling" = 1', ['bind."mp/grilling"']),
        ('"mp/grilling" = true', ['bind."mp/grilling"']),
        ('"mp/grilling" = "own"', ['bind."mp/grilling"']),
        ('"mp/grilling" = "own/../x"', ['bind."mp/grilling"']),
        ('"grilling" = "own/grill"', ['bind."grilling"']),
        ('"mp/a b" = "own/grill"', ['bind."mp/a b"']),
    ],
)
def test_bad_bind(home: Path, capsys: Capsys, bind: str, expected: list[str]) -> None:
    (home / "a").mkdir()
    (home / "b").mkdir()
    write_config(
        f'[sources.mp]\npath = "~/a"\n[sources.own]\npath = "~/b"\n[bind]\n{bind}\n'
    )

    code, err = build(capsys)

    assert code == 1
    for text in expected:
        assert text in err


def test_valid_rename_loads(home: Path) -> None:
    (home / "a").mkdir()
    write_config(
        '[sources.mp]\npath = "~/a"\n[rename]\n"mp/code-review" = "mp-code-review"\n'
    )

    assert config.load().renames == {
        config.SkillId("mp", "code-review"): "mp-code-review"
    }


@pytest.mark.parametrize(
    ("rename", "expected"),
    [
        ('"mp/tdd" = "a/b"', ['rename."mp/tdd"']),
        ('"mp/tdd" = ""', ['rename."mp/tdd"']),
        ('"mp/tdd" = 1', ['rename."mp/tdd"']),
        ('"nope/tdd" = "tdd2"', ['rename."nope/tdd"', "'nope'"]),
        ('"tdd" = "tdd2"', ['rename."tdd"']),
    ],
)
def test_bad_rename(
    home: Path, capsys: Capsys, rename: str, expected: list[str]
) -> None:
    (home / "a").mkdir()
    write_config(f'[sources.mp]\npath = "~/a"\n[rename]\n{rename}\n')

    code, err = build(capsys)

    assert code == 1
    for text in expected:
        assert text in err


def test_valid_patches_load(home: Path) -> None:
    (home / "a").mkdir()
    folder = home / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True)
    (folder / "tdd.patch").write_bytes(b"--- a/SKILL.md\n")
    write_config(
        '[sources.mp]\npath = "~/a"\n[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )

    assert config.load().patches == {
        config.SkillId("mp", "tdd"): [
            config.PatchFile("patches/tdd.patch", b"--- a/SKILL.md\n")
        ]
    }


BINARY = b"Binary files base/x.png and edited/x.png differ\n"
GIT_BINARY = b"diff --git a/x.png b/x.png\nGIT binary patch\nliteral 1\n"
ONLY_IN = b"Only in edited/refs: new.md\n"


@pytest.mark.parametrize(
    ("patches", "expected"),
    [
        ('"mp/tdd" = "patches/a.patch"', ['patches."mp/tdd"']),
        ('"mp/tdd" = []', ['patches."mp/tdd"']),
        ('"mp/tdd" = [1]', ['patches."mp/tdd"']),
        ('"nope/tdd" = ["patches/a.patch"]', ['patches."nope/tdd"', "'nope'"]),
        (
            '"mp/tdd" = ["patches/gone.patch"]',
            ['patches."mp/tdd"', "patches/gone.patch"],
        ),
        ('"mp/tdd" = ["patches"]', ['patches."mp/tdd"', "patches"]),
        (
            '"mp/tdd" = ["patches/a.patch", "./patches/a.patch"]',
            ['patches."mp/tdd"', "./patches/a.patch", "twice"],
        ),
        (
            '"mp/tdd" = ["patches/binary.patch"]',
            ["patches/binary.patch", "Binary files"],
        ),
        (
            '"mp/tdd" = ["patches/git-binary.patch"]',
            ["patches/git-binary.patch", "binary"],
        ),
        (
            '"mp/tdd" = ["patches/only-in.patch"]',
            ["patches/only-in.patch", "Only in", "-N"],
        ),
    ],
)
def test_bad_patches(
    home: Path, capsys: Capsys, patches: str, expected: list[str]
) -> None:
    (home / "a").mkdir()
    folder = home / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True)
    (folder / "a.patch").write_bytes(b"--- a/SKILL.md\n")
    (folder / "binary.patch").write_bytes(b"--- a/SKILL.md\n" + BINARY)
    (folder / "git-binary.patch").write_bytes(GIT_BINARY)
    (folder / "only-in.patch").write_bytes(ONLY_IN)
    write_config(f'[sources.mp]\npath = "~/a"\n[patches]\n{patches}\n')

    code, err = build(capsys)

    assert code == 1
    for text in expected:
        assert text in err


def test_shared_patch_loads(home: Path) -> None:
    (home / "a").mkdir()
    folder = home / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True)
    (folder / "common.patch").write_bytes(b"--- a/SKILL.md\n")
    write_config(
        '[sources.mp]\npath = "~/a"\n[patches]\n'
        '"mp/tdd" = ["patches/common.patch"]\n"mp/notes" = ["patches/common.patch"]\n'
    )

    assert len(config.load().patches) == 2


def test_patches_not_a_table(capsys: Capsys) -> None:
    write_config('patches = "x"\n')

    code, err = build(capsys)

    assert code == 1 and "'patches'" in err


def test_valid_reserved_list_loads() -> None:
    write_config('reserved = ["review"]\n')

    assert config.load().reserved == ["review"]


@pytest.mark.parametrize("value", ['"review"', '["a/b"]', "[1]", '[""]'])
def test_reserved_not_a_list_of_names(capsys: Capsys, value: str) -> None:
    write_config(f"reserved = {value}\n")

    code, err = build(capsys)

    assert code == 1 and "'reserved'" in err


def test_rename_not_a_table(capsys: Capsys) -> None:
    write_config('rename = "x"\n')

    code, err = build(capsys)

    assert code == 1 and "'rename'" in err


def test_bind_not_a_table(capsys: Capsys) -> None:
    write_config('bind = "x"\n')

    code, err = build(capsys)

    assert code == 1 and "'bind'" in err


def test_valid_prefix_loads(home: Path) -> None:
    (home / "a").mkdir()
    write_config(
        '[sources.mp]\ngit = "/srv/mp"\nprefix = "mp-"\n'
        '[sources.own]\npath = "~/a"\nprefix = "own."\n'
        '[sources.x]\ngit = "/srv/x"\n'
    )

    assert config.load().prefixes == {"mp": "mp-", "own": "own."}


@pytest.mark.parametrize("prefix", ['""', '"-x"', '"a/"', "1"])
def test_prefix_not_a_name(home: Path, capsys: Capsys, prefix: str) -> None:
    (home / "a").mkdir()
    write_config(f'[sources.mp]\npath = "~/a"\nprefix = {prefix}\n')

    code, err = build(capsys)

    assert code == 1 and "'sources.mp.prefix'" in err


def test_prefix_without_a_kind(capsys: Capsys) -> None:
    write_config('[sources.mp]\nprefix = "mp-"\n')

    code, err = build(capsys)

    assert code == 1 and "'sources.mp' needs 'path' or 'git'" in err
