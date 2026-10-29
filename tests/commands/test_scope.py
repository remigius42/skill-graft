"""Which package a command acts on: the nearest `.apm/skill-graft/` up to home,
the scope built in one place."""

import shutil
import tomllib
from contextlib import nullcontext
from pathlib import Path

import pytest
from conftest import FakeApm, skill

from skill_graft.cli import main
from skill_graft.commands import scope
from skill_graft.infra import paths


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


def test_undecodable_project_manifest(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_apm: FakeApm,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project(home / "repo")
    (home / "repo" / "apm.yml").write_bytes(b"dependencies:\n  apm:\n    - \xff\n")
    monkeypatch.chdir(home / "repo")
    fake_apm.register = False

    assert main(["build"]) == 1

    assert f"skill-graft: {home}/repo/apm.yml:" in capsys.readouterr().err


def test_no_install_reads_no_project_manifest(
    home: Path, monkeypatch: pytest.MonkeyPatch, fake_apm: FakeApm
) -> None:
    project(home / "repo")
    (home / "repo" / "apm.yml").mkdir()  # unreadable as a file
    monkeypatch.chdir(home / "repo")

    assert main(["build", "--no-install"]) == 0

    assert fake_apm.calls == []


def project_source(home: Path, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """A project package in `~/repo` with source `own` at `path`, entered."""
    package = project(home / "repo", "[]")
    (package / "skill-graft.toml").write_text(f'[sources.own]\npath = "{path}"\n')
    monkeypatch.chdir(home / "repo")


@pytest.mark.parametrize(
    ("path", "deploy"),
    [
        ("../../.claude/skills", "repo/.claude/skills"),
        ("~/.claude/skills", ".claude/skills"),
    ],
)
def test_project_source_overlapping_a_deploy_folder_warns(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    path: str,
    deploy: str,
) -> None:
    (home / deploy).mkdir(parents=True)
    project_source(home, monkeypatch, path)

    assert main(["resolve"]) == 0

    err = capsys.readouterr().err
    assert "'own'" in err and f"{home / deploy}, where APM deploys skills" in err


@pytest.mark.parametrize(
    ("path", "package"),
    [("../..", "repo/.apm/skill-graft"), ("~/.apm", ".apm/skill-graft")],
)
def test_project_source_overlapping_a_package_fails(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    path: str,
    package: str,
) -> None:
    (home / ".apm" / "skill-graft").mkdir(parents=True)
    project_source(home, monkeypatch, path)

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "'own'" in err and f"overlaps {home / package}" in err
    assert not (home / "repo" / ".apm" / "skill-graft" / "skill-graft.lock").exists()


def test_build_names_the_package(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    package = project(home / "repo")
    monkeypatch.chdir(home / "repo" / "src")

    assert main(["build", "--no-install"]) == 0

    assert capsys.readouterr().err.startswith(f"skill-graft: package: {package}\n")


def test_user_scope_names_the_package_even_on_failure(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert err.startswith(f"skill-graft: package: {home}/.apm/skill-graft\n")


@pytest.mark.parametrize("argv", [["bind", "own/tmp", "false"], ["unbind", "own/tmp"]])
def test_bind_and_unbind_name_the_package(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    package = project(home / "repo")
    monkeypatch.chdir(home / "repo")

    main(argv)

    assert capsys.readouterr().err.startswith(f"skill-graft: package: {package}\n")


@pytest.mark.parametrize("argv", [["tree"], ["why", "own/chisel"], ["rename", "x"]])
def test_no_package_line(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
) -> None:
    project(home / "repo")
    monkeypatch.chdir(home / "repo")

    with pytest.raises(SystemExit) if argv[0] == "rename" else nullcontext():
        main(argv)

    assert "package:" not in capsys.readouterr().err


def test_project_source_linking_into_the_user_package(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    vendored_skills = home / ".apm" / "skill-graft" / ".apm" / "skills"
    skill(vendored_skills / "tdd")
    (home / "skills").mkdir()
    (home / "skills" / "vendored").symlink_to(vendored_skills)
    package = project(home / "repo", '["own/tdd"]')
    (package / "skill-graft.toml").write_text(
        'entries = ["own/tdd"]\n[sources.own]\npath = "~/skills"\n'
    )
    monkeypatch.chdir(home / "repo")

    assert main(["resolve"]) == 1

    assert "own/tdd" in capsys.readouterr().err


def lock_sources(package: Path) -> object:
    return tomllib.loads((package / "skill-graft.lock").read_text())["sources"]


def test_project_source_inside_the_project(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = project(home / "repo")
    monkeypatch.chdir(home / "repo")

    assert main(["resolve"]) == 0

    assert lock_sources(package) == {"own": {"path": "../../src"}}


def test_project_source_outside_the_project(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = project(home / "repo", "[]")
    (home / "skills").mkdir()
    (package / "skill-graft.toml").write_text('[sources.own]\npath = "~/skills"\n')
    monkeypatch.chdir(home / "repo")

    assert main(["resolve"]) == 0

    assert lock_sources(package) == {"own": {"path": str((home / "skills").resolve())}}


def test_same_lock_on_another_machine(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project(home / "repo")
    monkeypatch.chdir(home / "repo")
    assert main(["resolve"]) == 0
    other = tmp_path / "other-home"
    shutil.copytree(home / "repo", other / "repo")
    monkeypatch.setenv("HOME", str(other))
    monkeypatch.chdir(other / "repo")

    assert main(["resolve"]) == 0

    lock = Path(".apm") / "skill-graft" / "skill-graft.lock"
    assert (other / "repo" / lock).read_bytes() == (home / "repo" / lock).read_bytes()


def test_build_into_keeps_project_paths(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project(home / "repo")
    monkeypatch.chdir(home / "repo")
    into = tmp_path / "into"
    into.mkdir()

    assert main(["build", "--into", str(into)]) == 0

    assert lock_sources(into) == {"own": {"path": "../../src"}}


def test_build_into_names_both(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    package = project(home / "repo")
    monkeypatch.chdir(home / "repo")
    (home / "repo" / "into").mkdir()

    assert main(["build", "--into", "into"]) == 0

    assert capsys.readouterr().err.startswith(
        f"skill-graft: package: {package}\n"
        f"skill-graft: into: {home / 'repo' / 'into'}\n"
    )


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


def test_of_build_names_the_package(
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
