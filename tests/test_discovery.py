from pathlib import Path

from skill_graft.discovery import skill_folders


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
