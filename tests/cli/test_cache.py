"""The `git-sources` cache pruning itself, through the commands that end."""

import os
import time
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import Upstream, build, configure, make_patch, skill, write_config

from skill_graft.cli import main
from skill_graft.infra import paths

Capsys: TypeAlias = pytest.CaptureFixture[str]

DAY = 86_400


def export(name: str, days: int) -> Path:
    """An export, or leftover, in the cache, last used `days` ago."""
    folder = paths.cache() / "trees" / "up-0123456789ab" / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("# x\n")
    return aged(folder, days)


def aged(path: Path, days: int) -> Path:
    then = time.time() - days * DAY
    os.utime(path, (then, then))
    return path


def git_config(upstream: Upstream, sha: str, extra: str = "") -> None:
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\n'
        f'ref = "{sha}"\n{extra}'
    )


def test_stale_export_removed(home: Path) -> None:
    skill(home / "own" / "notes")
    configure(["own/notes"], own="~/own")
    stale = export("a" * 40, 31)

    assert main(["resolve"]) == 0

    assert not stale.exists()


def test_export_in_use_kept(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    git_config(upstream, sha)
    assert build(capsys) == (0, "")
    (tree,) = (paths.cache() / "trees").glob(f"*/{sha}")
    aged(tree, 31)

    assert build(capsys) == (0, "")

    assert (tree / "tdd" / "SKILL.md").exists()


def test_recent_export_kept(home: Path) -> None:
    skill(home / "own" / "notes")
    configure(["own/notes"], own="~/own")
    recent = export("b" * 40, 29)

    assert main(["resolve"]) == 0

    assert recent.exists()


def test_failed_command_prunes_too(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    patch = make_patch(tmp_path, {"SKILL.md": "other\n"}, {"SKILL.md": "patched\n"})
    folder = Path.home() / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True)
    (folder / "tdd.patch").write_bytes(patch)
    git_config(upstream, sha, '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n')
    stale = export("a" * 40, 31)

    assert build(capsys)[0] == 1

    assert not stale.exists()


def test_leftover_removed(home: Path) -> None:
    skill(home / "own" / "notes")
    configure(["own/notes"], own="~/own")
    leftover = export(f"{'a' * 40}.x1y2.tmp", 31)

    assert main(["resolve"]) == 0

    assert not leftover.exists()


def test_dry_run_prunes_nothing(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    git_config(upstream, sha)
    assert build(capsys) == (0, "")
    upstream.commit({"tdd/SKILL.md": "# new\n"})
    (tree,) = (paths.cache() / "trees").glob(f"*/{sha}")
    used = aged(tree, 31).stat().st_mtime
    stale = export("a" * 40, 31)

    assert main(["update", "--dry-run"]) == 0

    assert stale.exists() and tree.stat().st_mtime == used


def test_path_sources_on_an_empty_cache(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "empty"))
    skill(home / "own" / "notes")
    configure(["own/notes"], own="~/own")

    assert main(["resolve"]) == 0
