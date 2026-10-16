from pathlib import Path

import pytest
from conftest import skill

from skill_graft.config import SkillId
from skill_graft.discovery import find, read_name, skill_folders
from skill_graft.errors import SkillGraftError


def found(source: Path) -> set[str]:
    return {str(folder.relative_to(source)) for folder in skill_folders(source)}


def test_nested_layout(tmp_path: Path) -> None:
    skill(tmp_path / "a")
    skill(tmp_path / "x" / "y" / "z" / "b")
    assert found(tmp_path) == {"a", "x/y/z/b"}


def test_hidden_folders_are_searched(tmp_path: Path) -> None:
    skill(tmp_path / ".claude" / "skills" / "a")
    assert found(tmp_path) == {".claude/skills/a"}


def test_skill_inside_a_skill(tmp_path: Path) -> None:
    skill(tmp_path / "a")
    skill(tmp_path / "a" / "examples" / "c")
    assert found(tmp_path) == {"a"}


def test_symlinked_skill_folder(tmp_path: Path) -> None:
    target = skill(tmp_path / "elsewhere" / "tdd")
    source = tmp_path / "source"
    source.mkdir()
    (source / "tdd").symlink_to(target)
    assert found(source) == {"tdd"}


def test_symlink_cycle(tmp_path: Path) -> None:
    skill(tmp_path / "a")
    (tmp_path / "loop").symlink_to(tmp_path)
    assert found(tmp_path) == {"a"}


def test_git_metadata_is_skipped(tmp_path: Path) -> None:
    skill(tmp_path / ".git" / "x")
    assert found(tmp_path) == set()


def test_source_that_is_a_skill(tmp_path: Path) -> None:
    skill(tmp_path)
    assert found(tmp_path) == {"."}


def test_front_matter_name(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd-v2", "---\nname: tdd\ndescription: d\n---\nbody\n")
    assert read_name(folder) == "tdd"


@pytest.mark.parametrize(
    "text", ["# no front matter\n", "---\ndescription: d\n---\n", "---\nname: x\n"]
)
def test_no_front_matter_name(tmp_path: Path, text: str) -> None:
    assert read_name(skill(tmp_path / "grilling", text)) == "grilling"


@pytest.mark.parametrize(
    "line", ['name: "tdd" # renamed', "name: 'tdd'", "name:   tdd   ", "name: tdd\t# x"]
)
def test_comment_and_quotes(tmp_path: Path, line: str) -> None:
    folder = skill(tmp_path / "x", f"﻿--- \n{line}\n---  \n")
    assert read_name(folder) == "tdd"


def test_indented_name_is_not_the_skill_name(tmp_path: Path) -> None:
    folder = skill(tmp_path / "x", "---\nmeta:\n  name: other\n---\n")
    assert read_name(folder) == "x"


@pytest.mark.parametrize(
    "value", [">-", "|", "&anchor tdd", "*alias", "[a]", "{a: b}", ""]
)
def test_unsupported_yaml_form(tmp_path: Path, value: str) -> None:
    folder = skill(tmp_path / "x", f"---\nname: {value}\n  tdd\n---\n")
    with pytest.raises(SkillGraftError, match=r"x/SKILL\.md"):
        read_name(folder)


def test_find_by_front_matter_name(tmp_path: Path) -> None:
    folder = skill(tmp_path / "skills" / "tdd-v2", "---\nname: tdd\n---\n")
    assert find(tmp_path, SkillId("mp", "tdd")) == folder


def test_duplicate_name(tmp_path: Path) -> None:
    skill(tmp_path / "a" / "tdd")
    skill(tmp_path / "b" / "tdd")
    with pytest.raises(SkillGraftError, match=r"mp/tdd.*a/tdd.*b/tdd"):
        find(tmp_path, SkillId("mp", "tdd"))


def test_entry_not_found(tmp_path: Path) -> None:
    skill(tmp_path / "tdd")
    with pytest.raises(SkillGraftError, match=r"mp/nope"):
        find(tmp_path, SkillId("mp", "nope"))


def test_traversal_in_name(tmp_path: Path) -> None:
    skill(tmp_path / "x", "---\nname: ../../x\n---\n")
    with pytest.raises(SkillGraftError, match=r"x/SKILL\.md"):
        find(tmp_path, SkillId("mp", "x"))


def test_unsupported_form_of_the_named_skill(tmp_path: Path) -> None:
    skill(tmp_path / "x", "---\nname: >-\n  x\n---\n")
    with pytest.raises(SkillGraftError, match=r"x/SKILL\.md"):
        find(tmp_path, SkillId("mp", "x"))


def test_other_skills_problems_do_not_block(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    skill(tmp_path / "a" / "dup")
    skill(tmp_path / "b" / "dup")
    skill(tmp_path / "bad", "---\nname: ../bad\n---\n")
    skill(tmp_path / "odd", "---\nname: |\n  odd\n---\n")
    assert find(tmp_path, SkillId("mp", "tdd")) == folder
