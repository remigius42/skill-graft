import tomllib
from pathlib import Path

import pytest
from conftest import FakeApm

from skill_graft.cli import main


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
    for word in ("git =", "branch =", "ref =", "skill-graft update"):
        assert word in text


def test_folder_exists(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    package = home / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "skill-graft.toml").write_text("entries = []\n")

    assert main(["init"]) == 1

    assert str(package) in capsys.readouterr().err
    assert [p.name for p in package.iterdir()] == ["skill-graft.toml"]
    assert (package / "skill-graft.toml").read_text() == "entries = []\n"
    assert fake_apm.calls == []


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
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["init"]) == 1

    assert f"apm install -g {package}" in capsys.readouterr().err
    assert (package / "skill-graft.toml").exists()
