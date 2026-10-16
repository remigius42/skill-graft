"""The `update` spec, through `skill-graft update`."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import Upstream, skill, write_config

from skill_graft import cache, paths
from skill_graft.cli import main

Capsys: TypeAlias = pytest.CaptureFixture[str]


def update(capsys: Capsys, *args: str) -> tuple[int, str, str]:
    """Runs `skill-graft update args`; returns its exit code, stdout and stderr."""
    code = main(["update", *args])
    out, err = capsys.readouterr()
    return code, out, err


def git_source(alias: str, upstream: Upstream, extra: str = "") -> str:
    return f'[sources.{alias}]\ngit = "{upstream.url}"\n{extra}'


@pytest.fixture
def upstream(tmp_path: Path) -> Upstream:
    return Upstream(tmp_path / "up")


def test_path_source_named(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "chisel")
    config = write_config('[sources.own]\npath = "~/src"\n')
    text = config.read_text()

    code, _, err = update(capsys, "own")

    assert code == 1 and "'own' is a path source" in err
    assert config.read_text() == text


def test_unknown_alias(capsys: Capsys) -> None:
    write_config("")

    code, _, err = update(capsys, "nope")

    assert code == 1 and "'nope'" in err


def test_other_source_without_a_ref(upstream: Upstream, capsys: Capsys) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(
        git_source("a", upstream, f'ref = "{sha}"\n') + git_source("b", upstream)
    )

    code, _, err = update(capsys, "a")

    assert code == 1 and "'b'" in err and "skill-graft update b" in err
    assert not paths.cache().exists()


@pytest.mark.parametrize("branch", ["main~3", "main@{1}", "a..b", "@{-1}"])
def test_revision_syntax_as_branch(tmp_path: Path, capsys: Capsys, branch: str) -> None:
    write_config(f'[sources.mp]\ngit = "{tmp_path / "nowhere"}"\nbranch = "{branch}"\n')

    code, _, err = update(capsys, "mp")

    assert code == 1 and "'sources.mp.branch'" in err


def test_missing_branch(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(git_source("mp", upstream, 'branch = "gone"\n'))

    code, _, err = update(capsys, "mp")

    assert code == 1 and "'mp'" in err and "'gone'" in err


def test_branch_deleted_upstream(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    upstream.git("branch", "dev")
    write_config(git_source("mp", upstream, 'branch = "dev"\n'))
    assert update(capsys, "mp")[0] == 0
    upstream.git("branch", "-D", "dev")

    code, _, err = update(capsys, "mp")

    assert code == 1 and "'mp'" in err and "'dev'" in err


def test_no_default_branch(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    upstream.git("symbolic-ref", "HEAD", "refs/heads/nothing")
    write_config(git_source("mp", upstream))

    code, _, err = update(capsys, "mp")

    assert code == 1 and "'mp'" in err and "branch = " in err


def test_output(tmp_path: Path, capsys: Capsys) -> None:
    a, b = Upstream(tmp_path / "a"), Upstream(tmp_path / "b")
    old = a.commit({"x/SKILL.md": "1\n"})
    new = a.commit({"x/SKILL.md": "2\n"})
    same = b.commit({"y/SKILL.md": "1\n"})
    write_config(
        git_source("a", a, f'ref = "{old}"\n') + git_source("b", b, f'ref = "{same}"\n')
    )

    code, out, _ = update(capsys)

    assert code == 0
    assert out.splitlines() == [f"a {new}", f"b {same} (unchanged)"]


def test_path_sources_are_skipped(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    skill(home / "src" / "chisel")
    write_config('[sources.own]\npath = "~/src"\n' + git_source("mp", upstream))

    code, out, _ = update(capsys)

    assert code == 0 and out.splitlines() == [f"mp {sha}"]


def test_tip_already_cached(upstream: Upstream, capsys: Capsys) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(git_source("mp", upstream, f'ref = "{sha}"\n'))
    assert update(capsys, "mp")[0] == 0
    repo = cache.Cache(paths.cache()).repository(upstream.url)
    assert not (repo / "FETCH_HEAD").exists()  # cloned, never fetched

    assert update(capsys, "mp")[0] == 0

    assert not (repo / "FETCH_HEAD").exists()
