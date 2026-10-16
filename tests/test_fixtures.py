import os
import shutil
import subprocess
from pathlib import Path

from conftest import FakeApm, Upstream


def test_home_is_temporary(tmp_path: Path) -> None:
    assert Path.home().is_relative_to(tmp_path)


def test_git_config_is_isolated() -> None:
    assert "GIT_DIR" not in os.environ and "GIT_INDEX_FILE" not in os.environ
    assert "XDG_CONFIG_HOME" not in os.environ
    assert "XDG_CACHE_HOME" not in os.environ
    assert Path(os.environ["GIT_CONFIG_GLOBAL"]).read_text() == ""


def test_upstream_commits(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    first = upstream.commit({"a/SKILL.md": "# a\n"})
    second = upstream.commit({"b/SKILL.md": "# b\n"})

    assert first != second and len(first) == len(second) == 40
    log = subprocess.run(
        ["git", "-C", upstream.url, "rev-list", "main"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert log == [second, first]


def test_sha256_upstream(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up", sha256=True)

    assert len(upstream.commit({"a/SKILL.md": "# a\n"})) == 64


def test_git_runs_under_fake_apm(fake_apm: FakeApm) -> None:
    assert shutil.which("git") is not None
