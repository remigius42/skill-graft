"""Which package a command acts on: the nearest `.apm/skill-graft/` up to home."""

from pathlib import Path

import pytest
from conftest import FakeApm, skill

from skill_graft import paths
from skill_graft.cli import main


def project(root: Path, entries: str = '["own/chisel"]') -> Path:
    """A project package at `root` whose source `own` is `root/src`, holding `chisel`."""
    skill(root / "src" / "chisel")
    package = root / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "skill-graft.toml").write_text(
        f'entries = {entries}\n[sources.own]\npath = "../../src"\n'
    )
    return package


def test_inside_a_project(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    package = project(home / "repo")
    monkeypatch.chdir(home / "repo" / "src")

    assert main(["build", "--no-install"]) == 0

    assert (package / ".apm" / "skills" / "chisel" / "SKILL.md").exists()
    assert (package / "skill-graft.lock").exists()
    assert not (home / ".apm" / "skill-graft").exists()


def test_project_without_a_package(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (home / "repo").mkdir()
    monkeypatch.chdir(home / "repo")

    assert main(["resolve"]) == 1

    assert f"{home}/.apm/skill-graft/skill-graft.toml" in capsys.readouterr().err


def test_nested_projects(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outer = project(home / "a")
    inner = project(home / "a" / "b")
    (home / "a" / "b" / "c").mkdir()
    monkeypatch.chdir(home / "a" / "b" / "c")

    assert main(["build", "--no-install"]) == 0

    assert (inner / "skill-graft.lock").exists()
    assert not (outer / "skill-graft.lock").exists()


def test_package_above_the_home_folder(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project(home.parent)
    (home / "repo").mkdir()
    monkeypatch.chdir(home / "repo")

    assert main(["resolve"]) == 1

    assert f"{home}/.apm/skill-graft/skill-graft.toml" in capsys.readouterr().err
    assert not (home.parent / ".apm" / "skill-graft" / "skill-graft.lock").exists()


def test_working_folder_outside_home(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The package sits at the working folder, so the walk never leaves tmp_path.
    package = project(tmp_path / "srv" / "repo")
    monkeypatch.chdir(tmp_path / "srv" / "repo")

    assert main(["build", "--no-install"]) == 0

    assert (package / "skill-graft.lock").exists()


def test_root_unset_after_main(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project(home / "repo")
    monkeypatch.chdir(home / "repo")
    main(["build", "--no-install"])

    assert paths.package() == home / ".apm" / "skill-graft"


def test_deleted_working_folder(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    gone = home / "gone"
    gone.mkdir()
    monkeypatch.chdir(gone)
    monkeypatch.setenv("PWD", str(gone))
    gone.rmdir()

    assert main(["tree"]) == 1

    err = capsys.readouterr().err
    assert err.startswith("skill-graft: ")
    assert f"working folder {gone} no longer exists" in err


def test_project_package_without_config(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    package = home / "repo" / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    monkeypatch.chdir(home / "repo")

    assert main(["build", "--no-install"]) == 1

    err = capsys.readouterr().err
    assert f"{package}/skill-graft.toml" in err
    assert "skill-graft init --project" in err
    assert "run `skill-graft init`" not in err


def test_project_build_from_a_subfolder(
    home: Path, monkeypatch: pytest.MonkeyPatch, fake_apm: FakeApm
) -> None:
    project(home / "repo")
    monkeypatch.chdir(home / "repo" / "src")

    assert main(["build"]) == 0

    assert fake_apm.calls == [["install", "./.apm/skill-graft"]]
    assert fake_apm.working_folders == [str(home / "repo")]
    assert "    - ./.apm/skill-graft\n" in (home / "repo" / "apm.yml").read_text()


def test_project_package_not_registered(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_apm: FakeApm,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project(home / "repo")
    monkeypatch.chdir(home / "repo")
    fake_apm.register = False

    assert main(["build"]) == 1

    err = capsys.readouterr().err
    assert f"{home}/repo/apm.yml does not list {home}/repo/.apm/skill-graft" in err


def test_no_install_reads_no_project_manifest(
    home: Path, monkeypatch: pytest.MonkeyPatch, fake_apm: FakeApm
) -> None:
    project(home / "repo")
    (home / "repo" / "apm.yml").mkdir()  # unreadable as a file
    monkeypatch.chdir(home / "repo")

    assert main(["build", "--no-install"]) == 0

    assert fake_apm.calls == []
