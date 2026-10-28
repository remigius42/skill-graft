"""The scope each command acts on, built in one place."""

import shutil
from pathlib import Path

import pytest

from skill_graft.commands import scope
from skill_graft.infra import paths


def test_init_takes_home_without_the_working_folder(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gone = home / "gone"
    gone.mkdir()
    monkeypatch.chdir(gone)
    shutil.rmtree(gone)

    with scope.of("init", False) as current:
        assert current == paths.Scope(Path.home())


def test_init_project_takes_the_working_folder(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (home / "repo").mkdir()
    monkeypatch.chdir(home / "repo")

    with scope.of("init", True) as current:
        assert current == paths.Scope(home / "repo")


def test_tree_takes_the_discovered_package_and_names_none(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (home / "repo" / ".apm" / "skill-graft").mkdir(parents=True)
    (home / "repo" / "src").mkdir()
    monkeypatch.chdir(home / "repo" / "src")

    with scope.of("tree", False) as current:
        assert current.root.resolve() == (home / "repo").resolve()
    assert "package:" not in capsys.readouterr().err


def test_build_names_the_package(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with scope.of("build", False):
        pass

    package = home / ".apm" / "skill-graft"
    assert capsys.readouterr().err == f"skill-graft: package: {package}\n"


def test_reset_after_the_block(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (home / "repo" / ".apm" / "skill-graft").mkdir(parents=True)
    monkeypatch.chdir(home / "repo")

    with scope.of("tree", False):
        assert paths.in_use().root != home
    assert paths.in_use().root == home


def test_reset_when_the_block_raises(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (home / "repo" / ".apm" / "skill-graft").mkdir(parents=True)
    monkeypatch.chdir(home / "repo")

    with pytest.raises(RuntimeError), scope.of("tree", False):
        raise RuntimeError
    assert paths.in_use().root == home
