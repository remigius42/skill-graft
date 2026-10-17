"""`git.apply`: a patch applied to a folder, strictly, whatever git config is around."""

import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import make_patch

from skill_graft import git
from skill_graft.errors import SkillGraftError


def folder_with(tmp_path: Path, files: dict[str, str]) -> Path:
    folder = tmp_path / "work" / "copy"
    folder.mkdir(parents=True)
    for path, text in files.items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
    return folder


def home_in(tmp_path: Path) -> Path:
    home = tmp_path / "work" / "home"
    home.mkdir(parents=True, exist_ok=True)
    return home


LINES = "".join(f"line {i}\n" for i in range(1, 11))


def test_applies(tmp_path: Path) -> None:
    patch = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 5\n", "line five\n")},
    )
    folder = folder_with(tmp_path, {"SKILL.md": LINES})

    ok, _ = git.apply(folder, patch, home_in(tmp_path))

    assert ok
    assert (folder / "SKILL.md").read_text() == LINES.replace("line 5\n", "line five\n")


def test_context_moved(tmp_path: Path) -> None:
    patch = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 8\n", "line eight\n")},
    )
    folder = folder_with(tmp_path, {"SKILL.md": "new 1\nnew 2\nnew 3\n" + LINES})

    ok, _ = git.apply(folder, patch, home_in(tmp_path))

    assert ok
    assert "line eight\n" in (folder / "SKILL.md").read_text()


def test_anchored_at_the_start(tmp_path: Path) -> None:
    patch = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 2\n", "line two\n")},
    )
    folder = folder_with(tmp_path, {"SKILL.md": "new\n" + LINES})

    ok, _ = git.apply(folder, patch, home_in(tmp_path))

    assert not ok
    assert (folder / "SKILL.md.rej").exists()


def test_config_in_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "apply.ignoreWhitespace")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "change")
    assert_whitespace_strict(tmp_path)

    monkeypatch.delenv("GIT_CONFIG_COUNT")
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "'apply.ignorewhitespace'='change'")
    assert_whitespace_strict(tmp_path)


def test_user_git_config(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = "[apply]\n\tignoreWhitespace = change\n[core]\n\tautocrlf = true\n"
    (home / ".gitconfig").write_text(config)
    (home / ".config" / "git").mkdir(parents=True)
    (home / ".config" / "git" / "config").write_text(config)
    (tmp_path / "global").write_text(config)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "global"))

    assert_whitespace_strict(tmp_path)
    assert b"\r" not in (tmp_path / "work" / "copy" / "SKILL.md").read_bytes()


def test_enclosing_repository(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "apply.ignoreWhitespace", "change"],
        check=True,
    )

    assert_whitespace_strict(tmp_path)


def test_no_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = folder_with(tmp_path, {"SKILL.md": LINES})
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(SkillGraftError, match=r"\[patches\] needs git"):
        git.apply(folder, b"", home_in(tmp_path))


def assert_whitespace_strict(tmp_path: Path) -> None:
    """A hunk whose context differs only in spacing fails; added spaces stay."""
    shutil.rmtree(tmp_path / "work", ignore_errors=True)
    spaced = LINES.replace("line 5\n", "line five   \n")
    patch = make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": spaced})
    folder = folder_with(tmp_path, {"SKILL.md": LINES})
    assert git.apply(folder, patch, home_in(tmp_path))[0]
    assert (folder / "SKILL.md").read_text() == spaced

    shutil.rmtree(tmp_path / "work")
    folder = folder_with(tmp_path, {"SKILL.md": LINES.replace("line 4\n", "line  4\n")})
    assert not git.apply(folder, patch, home_in(tmp_path))[0]
