"""The `git-sources` cache: where it lives and how URLs name repositories."""

import subprocess
from pathlib import Path

import pytest
from conftest import Upstream

from skill_graft import cache, paths
from skill_graft.errors import SkillGraftError


def test_default_location(home: Path) -> None:
    assert paths.cache() == home / ".cache" / "skill-graft"


def test_xdg_cache_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))

    assert paths.cache() == tmp_path / "xdg" / "skill-graft"


def test_relative_xdg_cache_home_is_ignored(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "rel")

    assert paths.cache() == home / ".cache" / "skill-graft"


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("https://github.com/mattpocock/skills.git", "skills"),
        ("https://github.com/mattpocock/skills/", "skills"),
        ("git@github.com:me/my skills.git", "my_skills"),
        ("/srv/skills", "skills"),
        ("https://example.com/", "example.com"),
        ("file:///", "repo"),
    ],
)
def test_key_is_readable(url: str, name: str) -> None:
    key = cache.key(url)

    assert key.rsplit("-", 1)[0] == name
    assert len(key.rsplit("-", 1)[1]) == 12


def test_key_is_distinct_per_url() -> None:
    assert cache.key("/a/skills") != cache.key("/b/skills")
    assert cache.key("/a/skills") == cache.key("/a/skills")


def test_fetch_clones_into_the_cache(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache(paths.cache())

    git_cache.fetch("mp", upstream.url)

    assert git_cache.has_commit(upstream.url, sha)
    assert (paths.cache() / "repos" / f"{cache.key(upstream.url)}.git").is_dir()


def test_fetch_once_per_url_per_command(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache(paths.cache())
    git_cache.fetch("a", upstream.url)
    newer = upstream.commit({"b/SKILL.md": "# b\n"})

    git_cache.fetch("b", upstream.url)

    assert not git_cache.has_commit(upstream.url, newer)
    later = cache.Cache(paths.cache())
    later.fetch("a", upstream.url)
    assert later.has_commit(upstream.url, newer)


def test_interrupted_clone_does_not_block(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    leftover = paths.cache() / "repos" / f"{cache.key(upstream.url)}.git.tmp"
    leftover.mkdir(parents=True)
    (leftover / "junk").write_text("half a clone")
    git_cache = cache.Cache(paths.cache())

    git_cache.fetch("mp", upstream.url)

    assert git_cache.has_commit(upstream.url, sha)
    assert not leftover.exists()


def test_sha256_remote(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up", sha256=True)
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache(paths.cache())

    git_cache.fetch("mp", upstream.url)

    assert git_cache.has_commit(upstream.url, sha)


def test_git_dir_from_a_hook_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    other = Upstream(tmp_path / "other")
    monkeypatch.setenv("GIT_DIR", str(other.path / ".git"))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(other.path / ".git" / "objects"))

    cache.Cache(paths.cache()).fetch("mp", upstream.url)

    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_OBJECT_DIRECTORY")
    assert cache.Cache(paths.cache()).has_commit(upstream.url, sha)
    with pytest.raises(subprocess.CalledProcessError):
        other.git("cat-file", "-e", sha)


def test_unreachable_remote(tmp_path: Path) -> None:
    url = str(tmp_path / "nowhere")

    with pytest.raises(SkillGraftError) as error:
        cache.Cache(paths.cache()).fetch("mp", url)

    assert "'mp'" in str(error.value) and url in str(error.value)


def test_git_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(SkillGraftError, match="git is not installed"):
        cache.Cache(paths.cache()).fetch("mp", "/srv/skills")
