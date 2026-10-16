"""The `git-sources` cache: where it lives and how URLs name repositories."""

from pathlib import Path

import pytest

from skill_graft import cache, paths


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
