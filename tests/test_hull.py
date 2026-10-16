"""The `hull` spec, through `skill-graft build --no-install`."""

import os
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import build, configure, skill, vendored

from skill_graft.cli import main

Capsys: TypeAlias = pytest.CaptureFixture[str]


def test_reference_pulls_in_a_skill(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "Run /grilling first.\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "grilling"}


def two_sources(home: Path, tdd: str, **extra: str) -> None:
    """Entry `mp/tdd` holding `tdd`, sources `mp` and `own`, plus `extra` ones."""
    skill(home / "mp" / "tdd", tdd)
    (home / "own").mkdir(exist_ok=True)
    for alias in extra:
        (home / alias).mkdir(exist_ok=True)
    configure(["mp/tdd"], mp="~/mp", own="~/own", **extra)


def test_own_source_wins(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling", "mp\n")
    skill(home / "own" / "grilling", "own\n")
    two_sources(home, "/grilling\n")

    assert build(capsys) == (0, "")
    assert (vendored_dir(home) / "grilling" / "SKILL.md").read_text() == "mp\n"


def test_one_other_source(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "notes")
    two_sources(home, "/notes\n")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "notes"}


def test_several_other_sources(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "notes")
    skill(home / "x" / "notes")
    two_sources(home, "/notes\n", x="~/x")

    code, err = build(capsys)

    assert code == 1
    for text in ["mp/tdd", "/notes", "own/notes", "x/notes", '"mp/notes"', "[bind]"]:
        assert text in err
    assert vendored() == set()


def test_no_such_skill(home: Path, capsys: Capsys) -> None:
    two_sources(home, "/foo and again /foo\n")

    code, err = build(capsys)

    assert code == 0 and vendored() == {"tdd"}
    warning = "`mp/tdd` calls `/foo`: no declared source has a skill `foo`"
    assert err.count(warning) == 1
    assert '"mp/foo" = false' in err


def test_skill_tool_form_named(home: Path, capsys: Capsys) -> None:
    two_sources(home, "Skill(foo)\n")

    _, err = build(capsys)

    assert "`mp/tdd` calls `Skill(foo)`" in err


def test_different_case(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "grilling")
    two_sources(home, "/Grilling\n")

    code, err = build(capsys)

    assert code == 0 and vendored() == {"tdd"}
    assert "no declared source has a skill `Grilling`" in err


def test_invalid_name_does_not_count(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling", '---\nname: "Grilling Tool"\n---\n')
    skill(home / "own" / "grilling", "own\n")
    two_sources(home, "/grilling\n")

    assert build(capsys) == (0, "")
    assert (vendored_dir(home) / "grilling" / "SKILL.md").read_text() == "own\n"


def test_two_hops(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling", "Then Skill(notes).\n")
    skill(home / "own" / "notes")
    two_sources(home, "/grilling\n")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "grilling", "notes"}


def test_cycle(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "a", "/b\n")
    skill(home / "mp" / "b", "/a\n")
    configure(["mp/a"], mp="~/mp")

    assert build(capsys) == (0, "")
    assert vendored() == {"a", "b"}


def test_self_reference(home: Path, capsys: Capsys) -> None:
    two_sources(home, "Run /tdd again.\n")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_ambiguous_target(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "a" / "grilling")
    skill(home / "mp" / "b" / "grilling")
    two_sources(home, "/grilling\n")

    code, err = build(capsys)

    assert code == 1
    assert "'mp/tdd' calls /grilling" in err
    assert str(home / "mp" / "a" / "grilling") in err
    assert str(home / "mp" / "b" / "grilling") in err


def test_clash_through_a_reference(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    skill(home / "own" / "grilling")
    configure(["mp/tdd", "own/grilling"], mp="~/mp", own="~/own")

    code, err = build(capsys)

    assert code == 1
    assert "mp/grilling" in err and "own/grilling" in err
    assert vendored() == set()


def test_not_utf8_warns(home: Path, capsys: Capsys) -> None:
    two_sources(home, "/grilling\n")
    (home / "mp" / "tdd" / "notes.md").write_bytes(b"\xff")

    code, err = build(capsys)

    assert code == 0 and "notes.md" in err and "UTF-8" in err


def test_symlink_to_a_device(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    (home / "mp" / "grilling" / "x.md").symlink_to("/dev/zero")
    two_sources(home, "/grilling\n")

    code, err = build(capsys)

    assert code == 1 and "x.md" in err and "outside" in err


@pytest.mark.parametrize("command", ["resolve", "build"])
def test_fifo_is_an_error(home: Path, capsys: Capsys, command: str) -> None:
    skill(home / "mp" / "grilling")
    os.mkfifo(home / "mp" / "grilling" / "pipe")
    two_sources(home, "/grilling\n")

    assert main([command, "--no-install"] if command == "build" else [command]) == 1

    err = capsys.readouterr().err
    assert "pipe" in err and "not a regular file" in err


def test_link_to_a_fifo_is_an_error(home: Path, capsys: Capsys) -> None:
    grilling = skill(home / "mp" / "grilling")
    (grilling / ".git").mkdir()
    os.mkfifo(grilling / ".git" / "pipe")
    (grilling / "x.md").symlink_to(".git/pipe")
    two_sources(home, "/grilling\n")

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "x.md" in err and "not a regular file" in err


def test_dangling_link_is_caught_before_copying(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    (home / "mp" / "grilling" / "data.txt").symlink_to("gone.txt")
    two_sources(home, "/grilling\n")

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "data.txt" in err and "missing" in err


def test_dangling_link(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    (home / "mp" / "grilling" / "notes.md").symlink_to("gone.md")
    two_sources(home, "/grilling\n")

    code, err = build(capsys)

    assert code == 1 and "notes.md" in err and "Traceback" not in err
    assert vendored() == set()


def with_binds(binds: str) -> None:
    """Appends a [bind] table to the config."""
    file = Path.home() / ".apm" / "skill-graft" / "skill-graft.toml"
    file.write_text(file.read_text() + f"[bind]\n{binds}\n")


def test_bind_across_sources(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    skill(home / "own" / "grill")
    two_sources(home, "/grilling\n")
    with_binds('"mp/grilling" = "own/grill"')

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "grill"}


def test_bind_settles_ambiguity(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "notes", "own\n")
    skill(home / "x" / "notes", "x\n")
    two_sources(home, "/notes\n", x="~/x")
    with_binds('"mp/notes" = "x/notes"')

    assert build(capsys) == (0, "")
    assert (vendored_dir(home) / "notes" / "SKILL.md").read_text() == "x\n"


def test_bind_to_a_missing_skill(home: Path, capsys: Capsys) -> None:
    two_sources(home, "/grilling\n")
    with_binds('"mp/grilling" = "own/nope"')

    code, err = build(capsys)

    assert code == 1 and "mp/grilling" in err and "own/nope" in err


def test_path_in_a_code_block(home: Path, capsys: Capsys) -> None:
    two_sources(home, "```sh\ncd /tmp\n```\n")
    with_binds('"mp/tmp" = false')

    assert build(capsys) == (0, "")


def test_unwanted_match(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tmp")
    two_sources(home, "cd /tmp\n")
    with_binds('"mp/tmp" = false')

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_typo_in_a_bind(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "grilling")
    two_sources(home, "nothing\n")
    with_binds('"mp/grill" = "own/grilling"')

    code, err = build(capsys)

    assert code == 0 and "mp/grill" in err and "binds no reference" in err


def test_bound_self_reference(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tdd")
    two_sources(home, "/tdd\n")
    with_binds('"mp/tdd" = "own/tdd"')

    code, err = build(capsys)

    assert code == 1 and "mp/tdd" in err and "own/tdd" in err
    assert "deployed name" in err


def vendored_dir(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / ".apm" / "skills"
