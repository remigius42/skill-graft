from pathlib import Path

import pytest

from skill_graft.discovery import read_name, skill_folders
from skill_graft.errors import SkillGraftError


def skill(folder: Path, text: str = "# skill\n") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(text)
    return folder


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
