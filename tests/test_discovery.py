"""The `skill-discovery` spec, through `skill-graft build --no-install`."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import build, configure, skill, vendored

Capsys: TypeAlias = pytest.CaptureFixture[str]


def test_nested_layout(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "a")
    skill(home / "src" / "x" / "y" / "z" / "b")
    configure(["own/a", "own/b"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"a", "b"}


def test_hidden_folders_are_searched(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / ".claude" / "skills" / "a")
    configure(["own/a"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"a"}


def test_skill_inside_a_skill_is_part_of_it(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "a")
    skill(home / "src" / "a" / "examples" / "c")
    configure(["own/c"], own="~/src")

    code, err = build(capsys)

    assert code == 1 and "own/c" in err
    configure(["own/a"], own="~/src")
    assert build(capsys) == (0, "")
    skills = home / ".apm" / "skill-graft" / ".apm" / "skills"
    assert (skills / "a" / "examples" / "c" / "SKILL.md").exists()


def test_symlinked_skill_folder(home: Path, capsys: Capsys) -> None:
    target = skill(home / "elsewhere" / "tdd")
    (home / "src").mkdir()
    (home / "src" / "tdd").symlink_to(target)
    configure(["own/tdd"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_symlink_cycle_finds_each_skill_once(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "a")
    (home / "src" / "loop").symlink_to(home / "src")
    configure(["own/a"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"a"}


def test_symlink_into_the_package_is_skipped(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "chisel")
    (home / "src" / "apm").symlink_to(home / ".apm")
    configure(["own/chisel"], own="~/src")
    build(capsys)

    assert build(capsys) == (0, "")
    assert vendored() == {"chisel"}


def test_git_metadata_is_skipped(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / ".git" / "x")
    configure(["own/x"], own="~/src")

    code, err = build(capsys)

    assert code == 1 and "own/x" in err


def test_source_that_is_a_skill(home: Path, capsys: Capsys) -> None:
    skill(home / "chisel")
    configure(["own/chisel"], own="~/chisel")

    assert build(capsys) == (0, "")
    assert vendored() == {"chisel"}


def test_front_matter_name(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd-v2", "---\nname: tdd\ndescription: d\n---\nbody\n")
    configure(["mp/tdd"], mp="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_front_matter_name_replaces_the_folder_name(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd-v2", "---\nname: tdd\n---\n")
    configure(["mp/tdd-v2"], mp="~/src")

    code, err = build(capsys)

    assert code == 1 and "mp/tdd-v2" in err


@pytest.mark.parametrize(
    "text",
    [
        "# no front matter\n",
        "---\ndescription: d\n---\n",
        "---\nname: x\n",
        "---\nmeta:\n  name: other\n---\n",
    ],
    ids=["none", "no name", "unclosed", "indented name"],
)
def test_folder_name_without_front_matter_name(
    home: Path, capsys: Capsys, text: str
) -> None:
    skill(home / "src" / "grilling", text)
    configure(["own/grilling"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"grilling"}


@pytest.mark.parametrize(
    "line", ['name: "tdd" # renamed', "name: 'tdd'", "name:   tdd   ", "name: tdd\t# x"]
)
def test_comment_and_quotes(home: Path, capsys: Capsys, line: str) -> None:
    skill(home / "src" / "x", f"﻿--- \n{line}\n---  \n")
    configure(["own/tdd"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


@pytest.mark.parametrize(
    "value", [">-", "|", "&anchor tdd", "*alias", "[a]", "{a: b}", ""]
)
def test_unsupported_yaml_form(home: Path, capsys: Capsys, value: str) -> None:
    skill(home / "src" / "x", f"---\nname: {value}\n  tdd\n---\n")
    configure(["own/x"], own="~/src")

    code, err = build(capsys)

    assert code == 1 and "x/SKILL.md" in err


@pytest.mark.parametrize(
    ("first", "text"),
    [("a/tdd", "# skill\n"), ("a/x", "---\nname: tdd\n---\n")],
    ids=["folder names", "front matter and folder name"],
)
def test_duplicate_name(home: Path, capsys: Capsys, first: str, text: str) -> None:
    skill(home / "src" / first, text)
    skill(home / "src" / "b" / "tdd")
    configure(["mp/tdd"], mp="~/src")

    code, err = build(capsys)

    assert code == 1
    assert "mp/tdd" in err and first in err and "b/tdd" in err
    assert vendored() == set()


def test_entry_not_found(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd")
    configure(["mp/nope"], mp="~/src")

    code, err = build(capsys)

    assert code == 1 and "mp/nope" in err


def test_traversal_in_name_writes_nothing(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "x", "---\nname: ../../x\n---\n")
    configure(["own/x"], own="~/src")

    code, err = build(capsys)

    assert code == 1 and "x/SKILL.md" in err
    assert vendored() == set()
    assert not (home / ".apm" / "skill-graft" / "x").exists()


def test_other_skills_problems_do_not_block(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd")
    skill(home / "src" / "a" / "dup")
    skill(home / "src" / "b" / "dup")
    skill(home / "src" / "bad", "---\nname: ../bad\n---\n")
    skill(home / "src" / "odd", "---\nname: |\n  odd\n---\n")
    configure(["own/tdd"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_hash_inside_quotes_is_not_a_comment(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "x", '---\nname: "a #b" # comment\n---\n')
    configure(["own/x"], own="~/src")

    code, err = build(capsys)

    assert code == 1 and "'a #b'" in err


@pytest.mark.parametrize("entry", ["own/foo", "own/x"])
def test_name_continued_on_the_next_line(
    home: Path, capsys: Capsys, entry: str
) -> None:
    skill(home / "src" / "x", "---\nname: foo\n  bar\n---\n")
    configure([entry], own="~/src")

    assert build(capsys)[0] == 1
    assert vendored() == set()


def test_unreadable_skill_with_the_entry_folder_name_is_ambiguous(
    home: Path, capsys: Capsys
) -> None:
    skill(home / "src" / "tdd-v2", "---\nname: tdd\n---\n")
    skill(home / "src" / "old" / "tdd", "---\nname: >-\n  tdd\n---\n")
    configure(["mp/tdd"], mp="~/src")

    code, err = build(capsys)

    assert code == 1
    assert "ambiguous" in err and "old/tdd/SKILL.md" in err and "tdd-v2" in err


def unreadable_skill(folder: Path, how: str) -> None:
    folder.mkdir(parents=True)
    if how == "not utf-8":
        (folder / "SKILL.md").write_bytes(b"---\nname: \xff\n---\n")
    else:
        (folder / "SKILL.md").symlink_to(folder / "nowhere")


@pytest.mark.parametrize("how", ["not utf-8", "dangling symlink"])
def test_unreadable_skill_elsewhere_does_not_block(
    home: Path, capsys: Capsys, how: str
) -> None:
    skill(home / "src" / "chisel")
    unreadable_skill(home / "src" / "other", how)
    configure(["own/chisel"], own="~/src")

    assert build(capsys) == (0, "")
    assert vendored() == {"chisel"}


@pytest.mark.parametrize("how", ["not utf-8", "dangling symlink"])
def test_unreadable_named_skill(home: Path, capsys: Capsys, how: str) -> None:
    unreadable_skill(home / "src" / "other", how)
    configure(["own/other"], own="~/src")

    code, err = build(capsys)

    assert code == 1 and "other/SKILL.md" in err
