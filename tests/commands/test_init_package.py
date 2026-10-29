import os
import re
import shutil
import tomllib
from pathlib import Path

import pytest
from conftest import FakeApm, write_config

from skill_graft.cli import main
from skill_graft.infra import apm, paths
from skill_graft.pipeline import config


def test_fresh_home(home: Path, fake_apm: FakeApm) -> None:
    package = home / ".apm" / "skill-graft"

    assert main(["init"]) == 0

    assert tomllib.loads((package / "skill-graft.toml").read_text()) == {}
    assert "[sources." in (package / "skill-graft.toml").read_text()
    assert (package / "apm.yml").read_text() == "name: skill-graft\nversion: 0.1.0\n"
    assert fake_apm.calls == [["install", "-g", str(package)]]
    assert f"- {package}" in (home / ".apm" / "apm.yml").read_text()


def test_template_shows_a_git_source(home: Path, fake_apm: FakeApm) -> None:
    assert main(["init"]) == 0

    text = (home / ".apm" / "skill-graft" / "skill-graft.toml").read_text()
    for word in ("git =", "branch =", "ref =", "subdirectory =", "skill-graft update"):
        assert word in text


def test_template_shows_graft_check(
    scope: paths.Scope, home: Path, fake_apm: FakeApm
) -> None:
    assert main(["init"]) == 0

    text = (home / ".apm" / "skill-graft" / "skill-graft.toml").read_text()
    lines = text.splitlines()
    start = lines.index("# [sources.skill-graft]")
    block = []
    for line in lines[start:]:
        if not re.match(r"# (\[|\w+ = )", line):
            break
        block.append(line.removeprefix("# "))
    write_config("\n".join(block) + "\n")
    source = config.load(scope).sources["skill-graft"]
    assert isinstance(source, config.GitSource)
    assert source.url == "https://github.com/remigius42/skill-graft.git"
    assert source.subdirectory == "skills"
    rest = "\n".join(lines[start + len(block) :])
    update = rest.index("skill-graft update skill-graft")
    add = rest.index("skill-graft add skill-graft/graft-check")
    assert update < add < rest.index("skill-graft build")
    assert "every `build` fails" in rest


def test_folder_exists(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    package = home / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "apm.yml").write_text("name: skill-graft\n")
    (home / ".apm" / "apm.yml").write_text(f"dependencies:\n  apm:\n    - {package}\n")

    assert main(["init"]) == 1

    err = capsys.readouterr().err
    assert str(package) in err
    assert "apm install" not in err
    assert (package / "apm.yml").read_text() == "name: skill-graft\n"
    assert fake_apm.calls == []


def test_folder_without_its_apm_yml(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    package = home / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "skill-graft.toml").write_text("entries = []\n")

    assert main(["init"]) == 1

    err = capsys.readouterr().err
    assert str(package) in err
    assert "apm install" not in err
    assert [p.name for p in package.iterdir()] == ["skill-graft.toml"]
    assert (package / "skill-graft.toml").read_text() == "entries = []\n"
    assert fake_apm.calls == []


def test_unregistered_folder_exists(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    package = home / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "apm.yml").write_text("name: skill-graft\n")

    assert main(["init"]) == 1

    err = capsys.readouterr().err
    assert f"to register it, run: apm install -g {package}\n" in err
    assert (package / "apm.yml").read_text() == "name: skill-graft\n"
    assert fake_apm.calls == []


def test_unregistered_folder_exists_without_apm(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = home / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "apm.yml").write_text("name: skill-graft\n")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["init"]) == 1

    err = capsys.readouterr().err
    assert f"to register it, run: apm install -g {package}\n" in err
    assert "skill-graft init" not in err


def test_dangling_symlink(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = home / ".apm" / "skill-graft"
    package.parent.mkdir()
    package.symlink_to(tmp_path / "gone")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["init"]) == 1

    err = capsys.readouterr().err
    assert f"{package} already exists" in err
    assert [p.name for p in (home / ".apm").iterdir()] == ["skill-graft"]
    assert not (tmp_path / "gone").exists()


def test_symlink_to_itself(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    package = home / ".apm" / "skill-graft"
    package.parent.mkdir()
    (home / ".apm" / "apm.yml").write_text("dependencies:\n  apm:\n    - ./x\n")
    package.symlink_to(package)

    assert main(["init"]) == 1

    err = capsys.readouterr().err
    assert f"{package} already exists" in err
    assert "apm install" not in err
    assert fake_apm.calls == []


def test_register_hint_quotes_the_package(
    tmp_path: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    home = tmp_path / "a b"
    package = home / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "apm.yml").write_text("name: skill-graft\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(home)

    assert main(["init"]) == 1

    assert f"run: apm install -g '{package}'\n" in capsys.readouterr().err


@pytest.mark.parametrize("failure", ["exit", "unregistered", "missing"])
def test_apm_fails(
    home: Path,
    fake_apm: FakeApm,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    package = home / ".apm" / "skill-graft"
    if failure == "exit":
        fake_apm.exit_code = 1
    elif failure == "unregistered":
        fake_apm.register = False
    else:
        # Found by the check, gone when `init` runs it.
        monkeypatch.setattr(apm, "require", lambda: None)
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["init"]) == 1

    assert f"apm install -g {package}" in capsys.readouterr().err
    assert (package / "skill-graft.toml").exists()


def test_retry_hint_quotes_the_package(
    tmp_path: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    home = tmp_path / "a b"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(home)
    fake_apm.exit_code = 1

    assert main(["init"]) == 1

    package = home / ".apm" / "skill-graft"
    err = capsys.readouterr().err
    assert f"`apm install -g '{package}'` failed" in err
    assert f"to retry, run: apm install -g '{package}'\n" in err


def test_apm_not_installed(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["init"]) == 1

    err = capsys.readouterr().err
    assert "APM is not installed" in err
    assert "install APM, then run: skill-graft init\n" in err
    assert not (home / ".apm").exists()


def test_retry_after_installing_apm(
    home: Path, fake_apm: FakeApm, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed = os.environ["PATH"]
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert main(["init"]) == 1

    monkeypatch.setenv("PATH", installed)

    assert main(["init"]) == 0
    assert (home / ".apm" / "skill-graft" / "skill-graft.toml").exists()


def project_root(home: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """`~/repo` with a `.claude/` harness marker, the working folder."""
    repo = home / "repo"
    (repo / ".claude").mkdir(parents=True)
    monkeypatch.chdir(repo)
    return repo


def test_project_package(
    home: Path, fake_apm: FakeApm, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = project_root(home, monkeypatch)

    assert main(["init", "--project"]) == 0

    package = repo / ".apm" / "skill-graft"
    assert tomllib.loads((package / "skill-graft.toml").read_text()) == {}
    assert (package / "apm.yml").read_text() == "name: skill-graft\nversion: 0.1.0\n"
    assert not (home / ".apm" / "skill-graft").exists()
    assert fake_apm.calls == [["install", "./.apm/skill-graft"]]
    assert fake_apm.working_folders == [str(repo)]
    assert "    - ./.apm/skill-graft\n" in (repo / "apm.yml").read_text()


def test_apm_not_installed_for_a_project(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = project_root(home, monkeypatch)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["init", "--project"]) == 1

    err = capsys.readouterr().err
    assert "APM is not installed" in err
    assert "install APM, then run: skill-graft init --project\n" in err
    assert not (repo / ".apm").exists()


def test_no_harness_in_the_project(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = home / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    fake_apm.exit_code = 2
    fake_apm.register = False

    assert main(["init", "--project"]) == 1

    assert "fix that, then run: skill-graft init --project" in capsys.readouterr().err
    assert not (repo / ".apm").exists()


def test_project_cleanup_despite_an_undecodable_manifest(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = project_root(home, monkeypatch)
    (repo / "apm.yml").write_bytes(b"\xff\n")
    fake_apm.exit_code = 2
    fake_apm.register = False

    assert main(["init", "--project"]) == 1

    assert "fix that, then run: skill-graft init --project" in capsys.readouterr().err
    assert not (repo / ".apm").exists()


def test_project_cleanup_when_the_manifest_cannot_be_read(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = project_root(home, monkeypatch)
    (repo / "apm.yml").mkdir()  # reading it raises an OSError, not a SkillGraftError
    fake_apm.register = False

    assert main(["init", "--project"]) == 1

    assert "skill-graft init --project" in capsys.readouterr().err
    assert not (repo / ".apm").exists()


def test_project_cleanup_failure_keeps_the_hint(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root(home, monkeypatch)
    fake_apm.exit_code = 2
    fake_apm.register = False

    def refuse(path: object) -> None:
        raise PermissionError(13, "Permission denied", str(path))

    monkeypatch.setattr(shutil, "rmtree", refuse)

    assert main(["init", "--project"]) == 1

    err = capsys.readouterr().err
    assert "failed with exit code 2" in err
    assert "cannot remove" in err and "Permission denied" in err
    assert "skill-graft init --project" in err


def test_project_apm_fails_keeps_existing_apm_folder(
    home: Path, fake_apm: FakeApm, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = project_root(home, monkeypatch)
    (repo / ".apm" / "skills").mkdir(parents=True)
    fake_apm.register = False

    assert main(["init", "--project"]) == 1

    assert (repo / ".apm" / "skills").is_dir()
    assert not (repo / ".apm" / "skill-graft").exists()


def test_apm_fails_after_registering(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = project_root(home, monkeypatch)
    fake_apm.exit_code = 1

    assert main(["init", "--project"]) == 1

    assert "fix that, then run: skill-graft build" in capsys.readouterr().err
    assert (repo / ".apm" / "skill-graft" / "skill-graft.toml").exists()


def test_project_folder_exists(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = project_root(home, monkeypatch)
    (repo / ".apm" / "skill-graft").mkdir(parents=True)
    (repo / ".apm" / "skill-graft" / "apm.yml").write_text("name: skill-graft\n")
    (repo / "apm.yml").write_text("dependencies:\n  apm:\n    - ./.apm/skill-graft\n")

    assert main(["init", "--project"]) == 1

    assert "apm install" not in capsys.readouterr().err
    assert [p.name for p in (repo / ".apm" / "skill-graft").iterdir()] == ["apm.yml"]
    assert fake_apm.calls == []


def test_project_folder_without_its_apm_yml(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = project_root(home, monkeypatch)
    (repo / ".apm" / "skill-graft").mkdir(parents=True)

    assert main(["init", "--project"]) == 1

    assert "apm install" not in capsys.readouterr().err
    assert list((repo / ".apm" / "skill-graft").iterdir()) == []
    assert fake_apm.calls == []


@pytest.mark.parametrize("manifest", ["missing", "unreadable", "not-listing"])
def test_unregistered_project_folder_exists(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    manifest: str,
) -> None:
    repo = project_root(home, monkeypatch)
    package = repo / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "apm.yml").write_text("name: skill-graft\n")
    if manifest == "unreadable":
        (repo / "apm.yml").write_bytes(b"\xff\n")
    elif manifest == "not-listing":
        (repo / "apm.yml").write_text("dependencies:\n  apm: []\n")

    assert main(["init", "--project"]) == 1

    err = capsys.readouterr().err
    assert f"to register it, run in {repo}: apm install ./.apm/skill-graft\n" in err
    assert (package / "apm.yml").read_text() == "name: skill-graft\n"
    assert fake_apm.calls == []


@pytest.mark.parametrize("via_symlink", [False, True])
def test_project_init_at_home(
    home: Path,
    tmp_path: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    via_symlink: bool,
) -> None:
    if via_symlink:
        (tmp_path / "link").symlink_to(home)
        monkeypatch.chdir(tmp_path / "link")

    assert main(["init", "--project"]) == 1

    assert "`skill-graft init`" in capsys.readouterr().err
    assert not (home / ".apm").exists()
    assert fake_apm.calls == []


@pytest.mark.parametrize(
    "inside", [".apm", ".apm/skill-graft", "repo/.apm/skill-graft"]
)
def test_project_init_inside_an_apm_folder(
    home: Path,
    fake_apm: FakeApm,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    inside: str,
) -> None:
    (home / inside).mkdir(parents=True)
    monkeypatch.chdir(home / inside)

    assert main(["init", "--project"]) == 1

    assert ".apm" in capsys.readouterr().err
    assert not (home / inside / ".apm").exists()
    assert fake_apm.calls == []


def test_project_init_inside_another_project(
    home: Path, fake_apm: FakeApm, monkeypatch: pytest.MonkeyPatch
) -> None:
    (home / "a" / ".apm" / "skill-graft").mkdir(parents=True)
    inner = project_root(home / "a", monkeypatch)

    assert main(["init", "--project"]) == 0

    assert (inner / ".apm" / "skill-graft" / "skill-graft.toml").exists()
    assert fake_apm.working_folders == [str(inner)]


def test_init_help_describes_project(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["init", "--help"])

    assert "--project" in capsys.readouterr().out
