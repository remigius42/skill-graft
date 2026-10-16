"""The `update` spec, through `skill-graft update`."""

import os
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import FakeApm, Upstream, skill, vendored, write_config

from skill_graft import cache, config, paths
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


def ref(alias: str) -> str | None:
    source = config.load().sources[alias]
    assert isinstance(source, config.GitSource)
    return source.ref


def test_new_commit_upstream(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    new = upstream.commit({"tdd/SKILL.md": "2\n"})
    write_config(git_source("mp", upstream, f'ref = "{old}"\n'))

    assert update(capsys)[0] == 0

    assert ref("mp") == new


def test_named_branch(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    upstream.git("checkout", "-q", "-b", "dev")
    dev = upstream.commit({"tdd/SKILL.md": "dev\n"})
    upstream.git("checkout", "-q", "main")
    write_config(git_source("mp", upstream, 'branch = "dev"\n'))

    assert update(capsys)[0] == 0

    assert ref("mp") == dev


def test_default_branch_renamed(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config(git_source("mp", upstream))
    assert update(capsys)[0] == 0
    upstream.git("checkout", "-q", "-b", "trunk")
    trunk = upstream.commit({"tdd/SKILL.md": "trunk\n"})

    assert update(capsys)[0] == 0

    assert ref("mp") == trunk


def test_source_without_a_ref_then_builds(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))

    assert update(capsys)[0] == 0
    assert main(["build", "--no-install"]) == 0

    assert vendored() == {"tdd"}


def test_only_the_named_sources(tmp_path: Path, capsys: Capsys) -> None:
    a, b = Upstream(tmp_path / "a"), Upstream(tmp_path / "b")
    a_old, b_old = a.commit({"x/SKILL.md": "1\n"}), b.commit({"y/SKILL.md": "1\n"})
    a.commit({"x/SKILL.md": "2\n"})
    b.commit({"y/SKILL.md": "2\n"})
    write_config(
        git_source("a", a, f'ref = "{a_old}"\n')
        + git_source("b", b, f'ref = "{b_old}"\n')
    )

    assert update(capsys, "a")[0] == 0

    assert ref("a") != a_old and ref("b") == b_old


def test_entry_gone_upstream(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    upstream.git("rm", "-q", "-r", "tdd")
    new = upstream.commit({"other/SKILL.md": "# other\n"})
    file = write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    before = file.read_bytes()

    code, out, err = update(capsys)

    assert code == 1 and "mp/tdd" in err
    assert out.splitlines() == [f"mp {new}"]
    assert file.read_bytes() == before


def test_no_deploy(upstream: Upstream, fake_apm: FakeApm, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))

    assert update(capsys)[0] == 0

    assert vendored() == set() and fake_apm.calls == []


def test_comments_survive(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    new = upstream.commit({"tdd/SKILL.md": "2\n"})
    text = (
        "# my skills\n"
        'entries = ["mp/tdd"]  # just one\n'
        "\n"
        "[sources.mp]\n"
        f'git = "{upstream.url}"\n'
        f'ref    = "{old}"  # bumped by update\n'
        "# the end\n"
    )
    file = write_config(text)

    assert update(capsys)[0] == 0

    assert file.read_text() == text.replace(old, new)


def test_ref_added_to_an_inline_table(upstream: Upstream, capsys: Capsys) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "1\n"})
    file = write_config(f'sources.mp = {{ git = "{upstream.url}" }}  # inline\n')

    assert update(capsys)[0] == 0

    assert ref("mp") == sha and file.read_text().endswith("  # inline\n")


@pytest.mark.parametrize(
    "layout",
    [
        'sources = {{ a = {{ git = "{url}" }}, b = {{ git = "{url}" }} }}\n',
        '[sources.b]\ngit = "{url}"\n[sources]\n[sources.a]\ngit = "{url}"\n',
    ],
)
def test_other_layouts(upstream: Upstream, capsys: Capsys, layout: str) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config(layout.format(url=upstream.url))

    assert update(capsys)[0] == 0

    assert ref("a") == ref("b") == sha


def test_symlinked_config(tmp_path: Path, upstream: Upstream, capsys: Capsys) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "1\n"})
    real = tmp_path / "dotfiles" / "skill-graft.toml"
    real.parent.mkdir()
    real.write_text(git_source("mp", upstream))
    link = write_config("")
    link.unlink()
    link.symlink_to(real)

    assert update(capsys)[0] == 0

    assert link.is_symlink() and sha in real.read_text()


def test_nothing_new(upstream: Upstream, capsys: Capsys) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "1\n"})
    file = write_config(git_source("mp", upstream, f'ref = "{sha}"\n'))
    os.utime(file, (1_000_000, 1_000_000))
    before = file.read_bytes()

    assert update(capsys)[0] == 0

    assert file.read_bytes() == before and file.stat().st_mtime == 1_000_000


def snapshot(folder: Path) -> dict[str, tuple[bool, bytes, int]]:
    """Every path under `folder`: whether a link, its content, its mtime."""
    if not folder.exists():
        return {}
    result = {}
    for path in sorted(folder.rglob("*")):
        content = (
            os.readlink(path).encode()
            if path.is_symlink()
            else path.read_bytes()
            if path.is_file()
            else b""
        )
        mtime = path.lstat().st_mtime_ns if not path.is_dir() else 0
        result[str(path.relative_to(folder))] = (path.is_symlink(), content, mtime)
    return result


def test_dry_run(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    file = write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    assert main(["build", "--no-install"]) == 0
    new = upstream.commit({"tdd/SKILL.md": "2\n"})
    before, cached = file.read_bytes(), snapshot(paths.cache())

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0
    assert out.splitlines()[0] == f"mp {new}" and "not written" in out
    assert file.read_bytes() == before and snapshot(paths.cache()) == cached


def test_dry_run_with_an_empty_cache(upstream: Upstream, capsys: Capsys) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and f"mp {sha}" in out
    assert not paths.cache().exists()


def test_dry_run_with_a_failing_entry(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    upstream.git("rm", "-q", "-r", "tdd")
    upstream.commit({"other/SKILL.md": "# other\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )

    code, _, err = update(capsys, "--dry-run")

    assert code == 1 and "mp/tdd" in err


def test_dry_run_with_an_unreachable_unselected_source(
    tmp_path: Path, capsys: Capsys
) -> None:
    a, b = Upstream(tmp_path / "a"), Upstream(tmp_path / "b")
    a.commit({"x/SKILL.md": "1\n"})
    b_ref = b.commit({"y/SKILL.md": "1\n"})
    write_config(
        'entries = ["a/x", "b/y"]\n'
        + git_source("a", a)
        + git_source("b", b, f'ref = "{b_ref}"\n')
    )
    assert update(capsys, "a")[0] == 0
    b.path.rename(tmp_path / "gone")
    a.commit({"x/SKILL.md": "2\n"})

    assert update(capsys, "a", "--dry-run")[0] == 0
    assert update(capsys, "a")[0] == 0
