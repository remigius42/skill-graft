from pathlib import Path

import pytest

from skill_graft.infra import paths


def test_in_use_follows_home_while_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    monkeypatch.setenv("HOME", str(first))
    assert paths.in_use().root == first
    monkeypatch.setenv("HOME", str(second))
    assert paths.in_use().root == second


def test_home_root_is_user_scope(home: Path) -> None:
    assert paths.Scope(home).user


def test_any_other_root_is_project_scope(tmp_path: Path) -> None:
    assert not paths.Scope(tmp_path / "project").user


def test_symlink_to_home_is_user_scope(home: Path, tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.symlink_to(home)
    assert paths.Scope(link).user


def test_paths_under_the_package(tmp_path: Path) -> None:
    scope = paths.Scope(tmp_path)
    package = tmp_path / ".apm" / "skill-graft"
    assert scope.package == package
    assert scope.lock_file == package / "skill-graft.lock"
    assert scope.skills == package / ".apm" / "skills"
