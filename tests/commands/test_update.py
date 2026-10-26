"""The `update` spec, through `skill-graft update`."""

import os
import tempfile
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import (
    FakeApm,
    Upstream,
    deadline,
    make_patch,
    skill,
    vendored,
    write_config,
)

from skill_graft.cli import main
from skill_graft.commands import edit
from skill_graft.infra import cache, files, paths
from skill_graft.pipeline import config, deployed, lock

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

    assert code == 1 and "'b'" in err and "skill-graft update a b" in err
    assert not paths.cache().exists()


def test_several_sources_without_a_ref(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(git_source("a", upstream) + git_source("b", upstream))

    code, _, err = update(capsys, "a")

    assert code == 1 and "source 'b' has no ref" in err
    assert "skill-graft update a b`" in err and not paths.cache().exists()
    assert update(capsys, "a", "b")[0] == 0


def test_hint_in_config_order(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config("".join(git_source(alias, upstream) for alias in "abc"))

    code, _, err = update(capsys, "c")

    assert code == 1 and "sources 'a', 'b' have no ref" in err
    assert "skill-graft update a b c`" in err


@pytest.mark.parametrize(
    "flags",
    [["--dry-run"], ["--expect", "0" * 64], ["--dry-run", "--expect", "0" * 64]],
)
def test_hint_keeps_the_review(
    upstream: Upstream, tmp_path: Path, capsys: Capsys, flags: list[str]
) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    config = write_config(
        git_source("a", upstream, f'ref = "{sha}"\n') + git_source("b", upstream)
    )
    text = config.read_text()
    review = tmp_path / "my review.diff"

    code, _, err = update(capsys, "a", *flags, "--diff", str(review))

    assert code == 1 and config.read_text() == text
    assert f"skill-graft update a b --dry-run --diff '{review}'`" in err


def test_entries_clash_before_update_fetches(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "own" / "tdd")
    config = write_config(  # no remote there: contacting it would be another error
        'entries = ["mp/tdd", "own/tdd"]\n'
        f'[sources.mp]\ngit = "{tmp_path / "nowhere"}"\nref = "{"0" * 40}"\n'
        '[sources.own]\npath = "~/own"\n'
    )
    text = config.read_text()

    code, _, err = update(capsys, "mp")

    assert code == 1 and "mp/tdd" in err and "own/tdd" in err
    assert not paths.cache().exists()
    assert config.read_text() == text


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


def test_empty_remote(upstream: Upstream, capsys: Capsys) -> None:
    write_config(git_source("mp", upstream))

    code, _, err = update(capsys, "mp")

    assert code == 1 and "'mp'" in err and "no commits" in err


def test_detached_head_is_no_default_branch(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    upstream.git("checkout", "-q", "--detach")
    upstream.commit({"tdd/SKILL.md": "on no branch\n"})
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
    assert out.splitlines()[:2] == [f"a {new}", f"b {same} (unchanged)"]


def test_path_sources_are_skipped(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    skill(home / "src" / "chisel")
    write_config('[sources.own]\npath = "~/src"\n' + git_source("mp", upstream))

    code, out, _ = update(capsys)

    assert code == 0 and out.splitlines()[:1] == [f"mp {sha}"]


def test_config_warnings_are_shown(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    skill(home / ".agents" / "skills" / "chisel")
    write_config(
        '[sources.own]\npath = "~/.agents/skills"\n' + git_source("mp", upstream)
    )

    code, _, err = update(capsys)

    assert code == 0 and "warning:" in err and "'own'" in err


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


def test_failed_write_leaves_no_temporary_file(
    upstream: Upstream, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    file = write_config(git_source("mp", upstream))
    before = file.read_bytes()

    def fail(*args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail)

    code, _, err = update(capsys)

    assert code == 1 and "disk full" in err
    assert file.read_bytes() == before
    assert sorted(p.name for p in file.parent.iterdir()) == ["skill-graft.toml"]


def test_line_endings_and_encoding_survive(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    new = upstream.commit({"tdd/SKILL.md": "2\n"})
    text = f'# 5 € → ✓\r\n[sources.mp]\r\ngit = "{upstream.url}"\r\nref = "{old}"\r\n'
    file = write_config("")
    file.write_bytes(text.encode())

    assert update(capsys)[0] == 0

    assert file.read_bytes() == text.replace(old, new).encode()


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


def lock_file() -> Path:
    return paths.package() / "skill-graft.lock"


def test_lock_follows_the_toml(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    new = upstream.commit({"tdd/SKILL.md": "2\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )

    assert update(capsys)[0] == 0

    assert f'ref = "{new}"' in lock_file().read_text()


def test_lock_written_though_no_ref_moved(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "1\n"})
    notes = skill(home / "own" / "notes")
    file = write_config(
        'entries = ["mp/tdd", "own/notes"]\n'
        + git_source("mp", upstream, f'ref = "{sha}"\n')
        + '[sources.own]\npath = "~/own"\n'
    )
    assert update(capsys)[0] == 0
    before, toml = lock_file().read_text(), file.read_bytes()
    (notes / "SKILL.md").write_text("changed\n")

    assert update(capsys)[0] == 0

    assert lock_file().read_text() != before and file.read_bytes() == toml


def test_dry_run_leaves_the_lock(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"tdd/SKILL.md": "2\n"})
    before = lock_file().read_bytes()

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0
    assert "dry run: skill-graft.toml and skill-graft.lock not written" in out
    assert lock_file().read_bytes() == before


LEGEND = "hull (+ added, - removed, ~ changed):"


def diff_lines(out: str) -> list[str]:
    """What `update` printed after its per-source lines."""
    lines = out.splitlines()
    return lines[lines.index(LEGEND) :] if LEGEND in lines else lines[1:]


def test_skill_added_upstream(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n", "grilling/SKILL.md": "g\n"})
    upstream.commit({"tdd/SKILL.md": "/grilling\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])  # caches the old ref

    code, out, _ = update(capsys)

    assert code == 0
    assert diff_lines(out) == [
        LEGEND,
        "+ mp/grilling",
        "  SKILL.md (new, 2 bytes)",
        "~ mp/tdd",
        "  SKILL.md (changed, 2 -> 10 bytes)",
    ]


def test_skill_dropped_upstream(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "/grilling\n", "grilling/SKILL.md": "g\n"})
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])

    code, out, _ = update(capsys)

    assert code == 0
    assert diff_lines(out) == [
        LEGEND,
        "- mp/grilling",
        "~ mp/tdd",
        "  SKILL.md (changed, 10 -> 2 bytes)",
    ]


def test_nothing_changed(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    upstream.commit({"other.txt": "x\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and diff_lines(out)[0] == "hull unchanged"
    assert "review:" not in out


def test_old_refs_unresolvable(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))

    code, out, _ = update(capsys)

    assert code == 0 and "no previous hull to compare" in out


def test_old_ref_not_cached(upstream: Upstream, capsys: Capsys) -> None:
    tip = upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{tip}"\n')
    )
    main(["build", "--no-install"])  # caches the tip
    missing = "0" * 40  # a ref no cache holds
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{missing}"\n')
    )
    repos = paths.cache() / "repos"
    before = snapshot(repos)

    code, out, _ = update(capsys)

    assert code == 0
    assert (
        f"no previous hull to compare ('mp' ref {missing} is not in the cache; "
        "likely its branch not fetched since it was pushed, history rewritten "
        "upstream, or a ref set to a commit on no branch, such as a tag's)"
    ) in out
    assert snapshot(repos) == before  # nothing fetched


def test_warnings_once(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "/foo\n"})
    upstream.commit({"tdd/SKILL.md": "/foo again\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])
    capsys.readouterr()

    code, _, err = update(capsys)

    assert code == 0 and err.count("calls `/foo`") == 1


@pytest.mark.parametrize(
    ("args", "line"),
    [
        ([], "skill-graft: 1 prose suggestion(s): run skill-graft resolve\n"),
        (
            ["--dry-run"],
            "skill-graft: 1 prose suggestion(s) at the new tips: "
            "update, then run skill-graft resolve\n",
        ),
    ],
)
def test_update_announces_suggestions(
    upstream: Upstream, capsys: Capsys, args: list[str], line: str
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n", "diagnosing-bugs/SKILL.md": "d\n"})
    upstream.commit({"tdd/SKILL.md": "then diagnosing-bugs\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )

    code, _, err = update(capsys, *args)

    assert code == 0
    assert line in err


def test_dry_run_prints_the_diff(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n", "grilling/SKILL.md": "g\n"})
    upstream.commit({"tdd/SKILL.md": "/grilling\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and "+ mp/grilling" in out


def test_reference_turns_ambiguous_upstream(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    x = Upstream(tmp_path / "x")
    x_ref = x.commit({"other/SKILL.md": "1\n"})
    skill(home / "mp" / "tdd", "/notes\n")
    skill(home / "own" / "notes")
    file = write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n' + git_source("x", x, f'ref = "{x_ref}"\n')
    )
    assert update(capsys)[0] == 0
    before, toml = lock_file().read_bytes(), file.read_bytes()
    x.commit({"notes/SKILL.md": "x\n"})

    code, _, err = update(capsys)

    assert code == 1 and "/notes" in err and "own/notes" in err and "x/notes" in err
    assert lock_file().read_bytes() == before and file.read_bytes() == toml


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_failed_lock_leaves_the_toml(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    notes = skill(home / "own" / "notes")
    secret = notes / "data.bin"
    secret.write_text("x")
    secret.chmod(0)
    file = write_config(
        'entries = ["mp/tdd", "own/notes"]\n'
        + git_source("mp", upstream)
        + '[sources.own]\npath = "~/own"\n'
    )
    before = file.read_bytes()

    try:
        code, _, _ = update(capsys)
    finally:
        secret.chmod(0o644)

    assert code == 1 and file.read_bytes() == before and not lock_file().exists()


def test_broken_old_ref_only_skips_the_diff(upstream: Upstream, capsys: Capsys) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    (upstream.path / "tdd" / "data.txt").symlink_to("gone.txt")
    old = upstream.commit({})
    (upstream.path / "tdd" / "data.txt").unlink()
    new = upstream.commit({})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    assert main(["build", "--no-install"]) == 1  # the link is broken; old is cached
    capsys.readouterr()

    code, out, _ = update(capsys)

    assert code == 0 and ref("mp") == new
    assert "no previous hull to compare (the current refs do not resolve:" in out
    assert "data.txt" in out


LINES = "".join(f"line {i}\n" for i in range(1, 11))


def patched_source(upstream: Upstream, ref: str, data: bytes) -> Path:
    """Entry `mp/tdd` from `upstream` at `ref`, patched by `patches/tdd.patch`."""
    folder = Path.home() / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "tdd.patch").write_bytes(data)
    return write_config(
        'entries = ["mp/tdd"]\n'
        + git_source("mp", upstream, f'ref = "{ref}"\n')
        + '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )


def test_patch_fails_at_the_tip(
    upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES})
    tip_text = LINES.replace("line 5\n", "line 5 upstream\n")
    new = upstream.commit({"tdd/SKILL.md": tip_text})
    edited = LINES.replace("line 5\n", "line five\n")
    file = patched_source(
        upstream, old, make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": edited})
    )
    assert main(["build", "--no-install"]) == 0
    before, toml = lock_file().read_bytes(), file.read_bytes()
    capsys.readouterr()

    code, _, err = update(capsys)

    tip = paths.cache() / "trees" / cache.key(upstream.url) / new / "tdd"
    assert code == 1
    assert "patches/tdd.patch: SKILL.md: hunk @@ -2,7 +2,7 @@ does not apply" in err
    assert f"redo it against {tip}" in err
    assert lock_file().read_bytes() == before and file.read_bytes() == toml

    redone = make_patch(
        tmp_path,
        {"SKILL.md": tip_text},
        {"SKILL.md": tip_text.replace("line 5 upstream\n", "line five\n")},
    )
    (Path.home() / ".apm" / "skill-graft" / "patches" / "tdd.patch").write_bytes(redone)

    code, out, _ = update(capsys)

    assert code == 0 and ref("mp") == new
    assert "no previous hull to compare (patches fail at the current refs)" in out
    assert lock_file().read_bytes() != before


def test_other_error_at_the_current_refs_shown(
    upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES, "notes/SKILL.md": "Run /y.\n"})
    tip_text = LINES.replace("line 5\n", "line 5 upstream\n")
    upstream.commit({"tdd/SKILL.md": tip_text, "x/SKILL.md": "# x\n"})
    main(["update"])  # caches both commits; then back to the old ref
    file = patched_source(
        upstream,
        old,
        make_patch(
            tmp_path,
            {"SKILL.md": tip_text},
            {"SKILL.md": tip_text.replace("upstream", "edited")},
        ),
    )
    file.write_text(
        file.read_text().replace('"mp/tdd"]', '"mp/tdd", "mp/notes"]', 1)
        + '[bind]\n"mp/y" = "mp/x"\n'
    )
    capsys.readouterr()

    code, out, _ = update(capsys)

    assert code == 0
    assert "no previous hull to compare (the current refs do not resolve:" in out
    assert "patches fail there" in out and "mp/x" in out


def test_dry_run_with_a_failing_patch(
    upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES})
    edited = LINES.replace("line 5\n", "line five\n")
    patched_source(
        upstream, old, make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": edited})
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"tdd/SKILL.md": LINES.replace("line 5\n", "line 5 upstream\n")})
    capsys.readouterr()

    code, _, err = update(capsys, "--dry-run")

    assert code == 1
    assert "patches/tdd.patch: SKILL.md: hunk @@ -2,7 +2,7 @@ does not apply" in err
    assert "mp/tdd: run `update` without `--dry-run` to fetch the tip" in err
    assert "redo it against" not in err


TAG = "\U000e0041"


def test_dry_run_keeps_the_hidden_characters(
    upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES, "notes/SKILL.md": "# notes\n"})
    edited = LINES.replace("line 5\n", "line five\n")
    file = patched_source(
        upstream, old, make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": edited})
    )
    file.write_text(file.read_text().replace('"mp/tdd"]', '"mp/tdd", "mp/notes"]', 1))
    assert main(["build", "--no-install"]) == 0
    upstream.commit(
        {
            "tdd/SKILL.md": LINES.replace("line 5\n", "line 5 upstream\n"),
            "notes/SKILL.md": f"# notes\n{TAG}\n",
        }
    )
    capsys.readouterr()

    code, _, err = update(capsys, "--dry-run")

    assert code == 1
    assert "mp/tdd: run `update` without `--dry-run` to fetch the tip" in err
    assert "hidden characters:\n  mp/notes: " in err
    assert "notes/SKILL.md:2: U+E0041 (tag character)" in err
    assert "mp/notes: run `update` without `--dry-run` to fetch the tip" in err


def test_hidden_characters_at_the_current_refs(
    upstream: Upstream, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": f"# tdd\n{TAG}\n"})
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))
    assert main(["update"]) == 0  # caches both commits; then back to the old ref
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    capsys.readouterr()

    code, out, _ = update(capsys)

    assert code == 0
    assert "no previous hull to compare (hidden characters at the current refs)" in out


def test_file_lines(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "x" * 119 + "\n"})
    upstream.commit({"tdd/SKILL.md": "x" * 179 + "\n", "tdd/run.sh": "y" * 39 + "\n"})
    (upstream.path / "tdd" / "run.sh").chmod(0o755)
    upstream.commit({})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])

    code, out, _ = update(capsys)

    assert code == 0
    assert diff_lines(out) == [
        LEGEND,
        "~ mp/tdd",
        "  SKILL.md (changed, 120 -> 180 bytes)",
        "  run.sh (new, 40 bytes) (now executable)",
    ]


def test_hint(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    upstream.commit({"tdd/SKILL.md": "2\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])

    code, out, _ = update(capsys, "mp", "--dry-run")

    assert code == 0
    assert out.splitlines()[-2:] == [
        "review: skill-graft update mp --dry-run --diff <file>",
        "dry run: skill-graft.toml and skill-graft.lock not written",
    ]


def test_no_hint_after_a_real_update(upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    upstream.commit({"tdd/SKILL.md": "2\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])

    code, out, _ = update(capsys)

    assert code == 0 and "~ mp/tdd" in out and "review:" not in out


def test_error_while_both_hulls_are_open(
    upstream: Upstream, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n"})
    upstream.commit({"tdd/SKILL.md": "2\n"})
    file = write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    main(["build", "--no-install"])
    before = file.read_bytes()

    def fail(old: object, new: object) -> list[str]:
        raise OSError("disk gone")

    monkeypatch.setattr(deployed, "summary", fail)

    code, out, err = update(capsys)

    assert code == 1 and "skill-graft: disk gone" in err
    assert "no previous hull" not in out and file.read_bytes() == before


EDITED = "edited since skill-graft.lock was written, not shown: "


def edited(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith(EDITED)]


def mp_and_own(home: Path, upstream: Upstream, entries: str, extra: str = "") -> Path:
    """`mp` from `upstream`, at its tip, and path source `own` holding `notes`."""
    upstream.commit({"tdd/SKILL.md": "1\n", "x/SKILL.md": "x\n"})
    skill(home / "own" / "notes")
    return write_config(
        f"entries = {entries}\n"
        + git_source("mp", upstream)
        + '[sources.own]\npath = "~/own"\n'
        + extra
    )


def test_path_source_edited_since_the_lock(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    mp_and_own(home, upstream, '["mp/tdd", "own/notes"]')
    assert update(capsys)[0] == 0
    (home / "own" / "notes" / "SKILL.md").write_text("changed\n")
    upstream.commit({"tdd/SKILL.md": "2\n"})

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and edited(out) == [EDITED + "own/notes"]
    assert out.index("~ mp/tdd") < out.index(EDITED)


def test_skill_left_since_the_lock(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    file = mp_and_own(home, upstream, '["mp/tdd", "mp/x"]')
    assert update(capsys)[0] == 0
    file.write_text(file.read_text().replace('"mp/tdd", "mp/x"', '"mp/tdd"'))

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and edited(out) == [EDITED + "mp/x"]


def test_nothing_edited_since_the_lock(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    mp_and_own(
        home, upstream, '["mp/tdd", "own/notes"]', '[rename]\n"mp/tdd" = "my-tdd"\n'
    )
    assert update(capsys)[0] == 0
    upstream.commit({"tdd/SKILL.md": "2\n"})

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and "~ mp/tdd" in out and edited(out) == []


def test_missing_lock_names_every_skill(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    mp_and_own(home, upstream, '["mp/tdd", "own/notes"]')
    assert update(capsys)[0] == 0
    lock_file().unlink()

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and edited(out) == [EDITED + "mp/tdd", EDITED + "own/notes"]


@pytest.mark.parametrize("text", ["version = 2\nskills = []\n", "not toml [", "\xff"])
def test_unreadable_lock_names_every_skill(
    home: Path, upstream: Upstream, capsys: Capsys, text: str
) -> None:
    mp_and_own(home, upstream, '["mp/tdd"]')
    assert update(capsys)[0] == 0
    lock_file().write_bytes(text.encode("latin-1"))

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and edited(out) == [EDITED + "mp/tdd"]


HEADER = (
    "# skill-graft Deployed diff: each Skill's text as `build` deploys it, Patches and"
    " Renames applied,\n"
    "# at the current refs against the new ones. Not what the Sources changed"
    " upstream. Untrusted text:\n"
    "# read it in an editor, not by printing it to a terminal.\n"
)


def moved_tdd(
    upstream: Upstream, before: str = "1\n", after: str = "2\n", extra: str = ""
) -> tuple[str, str, Path]:
    """Entry `mp/tdd`, built at `before`; the tip then changes it to `after`."""
    old = upstream.commit({"tdd/SKILL.md": before})
    file = write_config(
        'entries = ["mp/tdd"]\n'
        + git_source("mp", upstream, f'ref = "{old}"\n')
        + extra
    )
    assert main(["build", "--no-install"]) == 0
    new = upstream.commit({"tdd/SKILL.md": after})
    return old, new, file


def tdd_diff(old: str, new: str) -> str:
    return (
        "# ~ mp/tdd\n"
        f"# source mp: {old} -> {new}; upstream folder tdd\n"
        "diff --git a/SKILL.md b/SKILL.md\n"
        "--- a/SKILL.md\n"
        "+++ b/SKILL.md\n"
        "@@ -1 +1 @@\n"
        "-1\n"
        "+2\n"
    )


def test_diff_file(home: Path, upstream: Upstream, capsys: Capsys) -> None:
    old, new, _ = moved_tdd(upstream)

    code, out, _ = update(capsys, "--diff", "review.diff")

    assert code == 0 and ref("mp") == new
    assert (home / "review.diff").read_text() == HEADER + tdd_diff(old, new)
    assert "review:" not in out


def test_dry_run_with_a_diff_file(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    old, new, file = moved_tdd(upstream)
    before, lock, cached = (
        file.read_bytes(),
        lock_file().read_bytes(),
        snapshot(paths.cache()),
    )

    code, out, _ = update(capsys, "--dry-run", "--diff", "review.diff")

    assert code == 0 and "review:" not in out
    assert (home / "review.diff").read_text() == HEADER + tdd_diff(old, new)
    assert file.read_bytes() == before and lock_file().read_bytes() == lock
    assert snapshot(paths.cache()) == cached


def test_existing_diff_file(home: Path, upstream: Upstream, capsys: Capsys) -> None:
    old, _, _ = moved_tdd(upstream)
    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0
    newer = upstream.commit({"tdd/SKILL.md": "3\n"})

    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0

    text = (home / "review.diff").read_text()
    assert text.startswith(HEADER) and text.count(HEADER) == 1
    assert f"{old} -> {newer}" in text and "+3\n" in text and "+2\n" not in text


def test_failed_run_removes_the_diff_file(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    moved_tdd(upstream)
    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0
    upstream.git("rm", "-q", "-r", "tdd")
    upstream.commit({"other/SKILL.md": "# other\n"})

    code, _, err = update(capsys, "--dry-run", "--diff", "review.diff")

    assert code == 1 and "mp/tdd" in err
    assert not (home / "review.diff").exists()


def test_a_file_it_did_not_write(
    home: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = home / "repo" / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "skill-graft.toml").write_text("")
    (home / "repo" / "apm.yml").write_text("name: repo\n")
    (home / "repo" / "notes.diff").write_text("my own notes\n")
    monkeypatch.chdir(home / "repo")

    for name in ("apm.yml", "notes.diff"):
        code, _, err = update(capsys, "--dry-run", "--diff", name)

        assert code == 1 and name in err
    assert (home / "repo" / "apm.yml").read_text() == "name: repo\n"
    assert (home / "repo" / "notes.diff").read_text() == "my own notes\n"


def test_diff_file_a_symbolic_link(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    moved_tdd(upstream)
    (home / "target.diff").write_text(HEADER)
    (home / "review.diff").symlink_to("target.diff")

    code, _, err = update(capsys, "--diff", "review.diff")

    assert code == 1 and "review.diff" in err
    assert (home / "review.diff").is_symlink()
    assert (home / "target.diff").read_text() == HEADER


@pytest.mark.parametrize("kind", ["device", "fifo", "folder"])
def test_diff_file_not_a_regular_file(
    home: Path, upstream: Upstream, capsys: Capsys, kind: str
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))
    name = {"device": "/dev/zero", "fifo": "x.diff", "folder": "x.diff"}[kind]
    if kind == "fifo":
        os.mkfifo(home / name)
    elif kind == "folder":
        (home / name).mkdir()

    with deadline():
        code, _, err = update(capsys, "--dry-run", "--diff", name)

    assert code == 1 and name in err
    assert not paths.cache().exists()


@pytest.mark.parametrize(
    "name",
    [".apm/review.diff", ".APM/review.diff", "link/review.diff", "sub/../.apm/r.diff"],
)
def test_diff_file_inside_the_package(
    home: Path, upstream: Upstream, capsys: Capsys, name: str
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))
    (home / "link").symlink_to(home / ".apm")
    (home / "sub").mkdir()

    code, _, err = update(capsys, "--diff", name)

    assert code == 1 and name in err and ".apm" in err
    assert not paths.cache().exists()
    assert not list((home / ".apm").glob("*.diff"))


def test_not_a_diff_file_name(home: Path, upstream: Upstream, capsys: Capsys) -> None:
    moved_tdd(upstream)
    (home / ".claude" / "commands").mkdir(parents=True)

    code, _, err = update(capsys, "--dry-run", "--diff", ".claude/commands/review.md")

    assert (
        code == 1 and ".claude/commands/review.md" in err and "ending in .diff" in err
    )
    assert not (home / ".claude" / "commands" / "review.md").exists()


def test_diff_file_inside_a_skills_folder(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    moved_tdd(upstream)
    skill(home / ".claude" / "skills" / "mp-tdd")
    name = ".claude/skills/mp-tdd/review.diff"

    code, _, err = update(capsys, "--dry-run", "--diff", name)

    assert code == 1 and name in err
    assert not (home / name).exists()


def test_failed_write_after_the_diff(
    home: Path, upstream: Upstream, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    moved_tdd(upstream)

    def fail(document: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(edit, "write", fail)

    code, _, err = update(capsys, "--diff", "review.diff")

    assert code == 1 and "disk full" in err
    assert not (home / "review.diff").exists()


def failing_diff_write(monkeypatch: pytest.MonkeyPatch) -> None:
    write = files.atomic_write

    def atomic_write(file: Path, data: bytes) -> None:
        if file.name == "review.diff":
            raise OSError("disk full")
        write(file, data)

    monkeypatch.setattr(files, "atomic_write", atomic_write)


def test_failed_diff_write(
    upstream: Upstream, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, file = moved_tdd(upstream)
    before, lock = file.read_bytes(), lock_file().read_bytes()
    failing_diff_write(monkeypatch)

    code, _, err = update(capsys, "--diff", "review.diff")

    assert code == 1 and "disk full" in err
    assert file.read_bytes() == before and lock_file().read_bytes() == lock


def test_failed_diff_write_in_a_dry_run(
    upstream: Upstream, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    moved_tdd(upstream)
    failing_diff_write(monkeypatch)

    code, out, _ = update(capsys, "--dry-run", "--diff", "review.diff")

    assert code == 1 and "apply:" not in out


def test_diff_file_without_a_previous_hull(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    sha = upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))

    code, _, _ = update(capsys, "--diff", "review.diff")

    assert code == 0
    assert (home / "review.diff").read_text() == HEADER + (
        "# no previous hull to compare ('mp' had no ref): every Skill shown as added\n"
        "# + mp/tdd\n"
        f"# source mp: {sha}; upstream folder tdd\n"
        "diff --git a/SKILL.md b/SKILL.md\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/SKILL.md\n"
        "@@ -0,0 +1 @@\n"
        "+1\n"
    )


def test_diff_file_after_patches_redone_for_the_tip(
    home: Path, upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES})
    tip_text = LINES.replace("line 5\n", "line 5 upstream\n")
    upstream.commit({"tdd/SKILL.md": tip_text})
    redone = make_patch(
        tmp_path,
        {"SKILL.md": tip_text},
        {"SKILL.md": tip_text.replace("line 5 upstream\n", "line five\n")},
    )
    patched_source(upstream, old, redone)
    capsys.readouterr()

    code, out, _ = update(capsys, "--dry-run", "--diff", "review.diff")

    text = (home / "review.diff").read_text()
    assert code == 0 and apply_line(out)
    assert text.startswith(
        HEADER + "# no previous hull to compare (patches fail at the current refs): "
        "every Skill shown as added\n# + mp/tdd\n"
    )
    assert "+line five\n" in text and "--- /dev/null\n" in text


def test_diff_file_when_nothing_changed(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    moved_tdd(upstream, after="1\n")

    assert update(capsys, "--diff", "review.diff")[0] == 0

    assert (home / "review.diff").read_text() == HEADER + "# hull unchanged\n"


def test_patch_applied_on_both_sides(
    home: Path, upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES})
    edited = LINES.replace("line 3\n", "line three\n")
    patched_source(
        upstream, old, make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": edited})
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"tdd/SKILL.md": LINES.replace("line 9\n", "line 9 upstream\n")})

    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0

    text = (home / "review.diff").read_text()
    changed = [line for line in text.splitlines() if line[:1] in "+-"]
    assert changed == [
        "--- a/SKILL.md",
        "+++ b/SKILL.md",
        "-line 9",
        "+line 9 upstream",
    ]


def test_renamed_skill_in_the_diff(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "# tdd\n", "grilling/SKILL.md": "g\n"})
    write_config(
        'entries = ["mp/tdd"]\n'
        + git_source("mp", upstream, f'ref = "{old}"\nprefix = "mp-"\n')
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"tdd/SKILL.md": "# tdd\n/grilling\n"})

    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0

    assert "\n+/mp-grilling\n" in (home / "review.diff").read_text()


def source_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("# source ")]


def test_source_line(home: Path, upstream: Upstream, capsys: Capsys) -> None:
    old = upstream.commit({"skills/tdd/SKILL.md": "1\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    assert main(["build", "--no-install"]) == 0
    upstream.git("rm", "-q", "-r", "skills/tdd")
    new = upstream.commit({"skills/dev/tdd/SKILL.md": "2\n"})

    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0

    assert source_lines((home / "review.diff").read_text()) == [
        f"# source mp: {old} -> {new}; upstream folder skills/tdd -> skills/dev/tdd"
    ]


@pytest.mark.parametrize(
    ("folder", "quoted"),
    [("a\u2028b", '"a\\342\\200\\250b/tdd"'), ("a\u202eb", '"a\\342\\200\\256b/tdd"')],
)
def test_folder_name_holding_a_line_separator(
    home: Path, upstream: Upstream, capsys: Capsys, folder: str, quoted: str
) -> None:
    old = upstream.commit({f"{folder}/tdd/SKILL.md": "1\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    assert main(["build", "--no-install"]) == 0
    new = upstream.commit({f"{folder}/tdd/SKILL.md": "2\n"})

    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0

    text = (home / "review.diff").read_text()
    assert source_lines(text) == [
        f"# source mp: {old} -> {new}; upstream folder {quoted}"
    ]
    assert text.isascii()


def test_path_source_in_the_diff(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    skill(home / "own" / "notes", "/grilling\n")
    write_config(
        'entries = ["own/notes"]\n'
        + git_source("mp", upstream, f'ref = "{old}"\nprefix = "mp-"\n')
        + '[sources.own]\npath = "~/own"\n'
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"grilling/SKILL.md": "g\n"})

    assert update(capsys, "mp", "--dry-run", "--diff", "review.diff")[0] == 0

    text = (home / "review.diff").read_text()
    assert "# ~ own/notes\n# source own: a path source\n" in text
    assert "\n+/mp-grilling\n" in text


def test_edited_since_the_lock_in_the_diff(
    home: Path, upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES})
    patched_source(
        upstream,
        old,
        make_patch(
            tmp_path,
            {"SKILL.md": LINES},
            {"SKILL.md": LINES.replace("line 3\n", "line three\n")},
        ),
    )
    assert main(["build", "--no-install"]) == 0
    patched_source(
        upstream,
        old,
        make_patch(
            tmp_path,
            {"SKILL.md": LINES},
            {"SKILL.md": LINES.replace("line 3\n", "line 3 edited\n")},
        ),
    )
    upstream.commit({"tdd/SKILL.md": LINES.replace("line 9\n", "line 9 upstream\n")})

    code, out, _ = update(capsys, "--dry-run", "--diff", "review.diff")

    assert code == 0 and EDITED + "mp/tdd" in out
    assert "# ~ mp/tdd\n# source mp: " in (text := (home / "review.diff").read_text())
    assert (
        "\n# edited since skill-graft.lock was written: its earlier text is not shown\n"
        in text
    )


def test_git_configuration_ignored(
    home: Path, upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n", "tdd/a.md": "a\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"tdd/SKILL.md": "2\n", "tdd/a.md": "b\n"})
    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0
    plain = (home / "review.diff").read_text()
    (tmp_path / "attributes").write_text("*.md binary\n")
    (tmp_path / "order").write_text("SKILL.md\na.md\n")
    Path(os.environ["GIT_CONFIG_GLOBAL"]).write_text(
        f"[core]\n\tattributesFile = {tmp_path / 'attributes'}\n"
        f"[diff]\n\torderFile = {tmp_path / 'order'}\n"
    )

    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0

    assert (home / "review.diff").read_text() == plain
    assert "+b\n" in plain


DIGEST = "0123456789abcdef" * 4


def apply_line(out: str) -> list[str]:
    """The `update` arguments of the `apply:` line a dry run printed, if any."""
    prefix = "apply: skill-graft update "
    lines = [line for line in out.splitlines() if line.startswith(prefix)]
    assert len(lines) <= 1
    return lines[0].removeprefix(prefix).split(" ") if lines else []


def test_apply_line(upstream: Upstream, capsys: Capsys) -> None:
    _, new, _ = moved_tdd(upstream)

    code, out, _ = update(capsys, "mp", "--dry-run", "--diff", "review.diff")

    args = apply_line(out)
    assert code == 0 and args[:2] == ["mp", "--expect"] and len(args[2]) == 64
    assert out.splitlines()[-2:] == [
        f"apply: skill-graft update {' '.join(args)}",
        "dry run: skill-graft.toml and skill-graft.lock not written",
    ]
    assert update(capsys, *args)[0] == 0 and ref("mp") == new


def test_no_apply_line_before_a_review(upstream: Upstream, capsys: Capsys) -> None:
    moved_tdd(upstream)

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and "review: skill-graft update --dry-run --diff <file>" in out
    assert apply_line(out) == []


def uncached_ref(upstream: Upstream) -> None:
    """`mp`'s tip is cached; its ref, a commit no cache holds, is not."""
    tip = upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{tip}"\n')
    )
    assert main(["build", "--no-install"]) == 0
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{"0" * 40}"\n')
    )


def test_apply_line_without_a_previous_hull(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    uncached_ref(upstream)

    code, out, _ = update(capsys, "--dry-run", "--diff", "review.diff")

    assert code == 0 and apply_line(out)[:1] == ["--expect"]
    assert "# + mp/tdd\n" in (home / "review.diff").read_text()


def test_hint_without_a_previous_hull(upstream: Upstream, capsys: Capsys) -> None:
    uncached_ref(upstream)

    code, out, _ = update(capsys, "--dry-run")

    assert code == 0 and "review: skill-graft update --dry-run --diff <file>" in out
    assert apply_line(out) == []


def test_no_apply_line_after_an_edit(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    mp_and_own(home, upstream, '["mp/tdd", "own/notes"]')
    assert update(capsys)[0] == 0
    (home / "own" / "notes" / "SKILL.md").write_text("changed\n")

    code, out, _ = update(capsys, "--dry-run", "--diff", "review.diff")

    assert code == 0 and edited(out) == [EDITED + "own/notes"]
    assert apply_line(out) == []


def test_changed_by_resolution_only(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    skill(home / "own" / "notes", "/grilling\n")
    write_config(
        'entries = ["own/notes"]\n'
        + git_source("mp", upstream, f'ref = "{old}"\nprefix = "mp-"\n')
        + '[sources.own]\npath = "~/own"\n'
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"grilling/SKILL.md": "g\n"})

    code, out, _ = update(capsys, "mp", "--dry-run", "--diff", "review.diff")

    assert code == 0 and "~ own/notes" in out and edited(out) == []
    before = lock_file().read_text()
    assert update(capsys, *apply_line(out))[0] == 0
    assert lock_file().read_text() != before
    assert "own/notes" in lock_file().read_text()


def vetted(upstream: Upstream, capsys: Capsys) -> tuple[list[str], Path, bytes, bytes]:
    """`update mp --dry-run --diff review.diff` once `mp/tdd` moved: the apply
    line's arguments, the config, its bytes and the lock's."""
    _, _, file = moved_tdd(upstream, extra="")
    code, out, _ = update(capsys, "mp", "--dry-run", "--diff", "review.diff")
    assert code == 0 and apply_line(out)
    return apply_line(out), file, file.read_bytes(), lock_file().read_bytes()


def refused(
    capsys: Capsys, args: list[str], file: Path, toml: bytes, lock: bytes
) -> str:
    code, _, err = update(capsys, *args)
    assert code == 1
    assert file.read_bytes() == toml and lock_file().read_bytes() == lock
    return err


def test_tip_moved_after_vetting(upstream: Upstream, capsys: Capsys) -> None:
    args, file, toml, lock = vetted(upstream, capsys)
    upstream.commit({"tdd/SKILL.md": "3\n"})

    err = refused(capsys, args, file, toml, lock)

    assert args[2] in err and "not the one reviewed" in err
    assert "skill-graft update mp --dry-run --diff <file>" in err
    assert len([word for word in err.split() if len(word.strip(",;:.")) == 64]) == 2


def test_path_source_edited_after_vetting(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    skill(home / "own" / "notes")
    write_config(
        'entries = ["mp/tdd", "own/notes"]\n'
        + git_source("mp", upstream)
        + '[sources.own]\npath = "~/own"\n'
    )
    assert update(capsys)[0] == 0
    upstream.commit({"tdd/SKILL.md": "2\n"})
    code, out, _ = update(capsys, "mp", "--dry-run", "--diff", "review.diff")
    file = paths.package() / "skill-graft.toml"
    toml, lock = file.read_bytes(), lock_file().read_bytes()
    (home / "own" / "notes" / "SKILL.md").write_text("changed\n")

    refused(capsys, apply_line(out), file, toml, lock)


def test_patch_edited_after_vetting(
    upstream: Upstream, tmp_path: Path, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": LINES})
    file = patched_source(
        upstream,
        old,
        make_patch(
            tmp_path,
            {"SKILL.md": LINES},
            {"SKILL.md": LINES.replace("line 3\n", "line three\n")},
        ),
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"tdd/SKILL.md": LINES.replace("line 9\n", "line 9 upstream\n")})
    code, out, _ = update(capsys, "mp", "--dry-run", "--diff", "review.diff")
    toml, lock = file.read_bytes(), lock_file().read_bytes()
    patched_source(
        upstream,
        old,
        make_patch(
            tmp_path,
            {"SKILL.md": LINES},
            {"SKILL.md": LINES.replace("line 3\n", "line 3 edited\n")},
        ),
    )

    refused(capsys, apply_line(out), file, file.read_bytes(), lock)
    assert file.read_bytes() == toml


def test_rename_after_vetting(upstream: Upstream, capsys: Capsys) -> None:
    args, file, _, lock = vetted(upstream, capsys)
    file.write_text(file.read_text() + '[rename]\n"mp/tdd" = "my-tdd"\n')

    refused(capsys, args, file, file.read_bytes(), lock)


def test_unrelated_push(upstream: Upstream, capsys: Capsys) -> None:
    args, _, _, lock = vetted(upstream, capsys)
    tip = upstream.commit({"other.txt": "x\n"})

    assert update(capsys, *args)[0] == 0

    assert ref("mp") == tip and lock_file().read_bytes() != lock


def test_diff_file_on_a_mismatch(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    _, _, file = moved_tdd(upstream)
    toml, lock = file.read_bytes(), lock_file().read_bytes()

    refused(capsys, ["--expect", DIGEST, "--diff", "review.diff"], file, toml, lock)

    assert not (home / "review.diff").exists()


@pytest.mark.parametrize("digest", ["abc123", DIGEST.upper(), DIGEST + "0"])
def test_malformed_digest(upstream: Upstream, capsys: Capsys, digest: str) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))

    code, _, err = update(capsys, "--expect", digest)

    assert code == 1 and digest in err and "64 hex digits" in err
    assert not paths.cache().exists()


class Stop(BaseException):
    """Neither an `Exception` nor an `OSError`, as Ctrl-C is not."""


def test_old_hull_removed_on_any_error(
    upstream: Upstream, tmp_path: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    moved_tdd(upstream)
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(work))
    calls = []
    skill_hashes = lock.skill_hashes

    def hashes_then_stop(hull: object) -> dict[config.SkillId, str]:
        calls.append(hull)
        if len(calls) == 2:  # the old hull's
            raise Stop
        return skill_hashes(hull)  # type: ignore[arg-type]

    monkeypatch.setattr(lock, "skill_hashes", hashes_then_stop)

    with pytest.raises(Stop) as stopped:
        main(["update"])

    # Its traceback still alive, as when Ctrl-C reaches the top: no collector ran.
    assert stopped.traceback and list(work.iterdir()) == []


@pytest.mark.parametrize("name", ["typo/review.diff", "file.txt/review.diff"])
def test_diff_file_in_no_folder(
    home: Path, upstream: Upstream, capsys: Capsys, name: str
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))
    (home / "file.txt").write_text("x\n")

    code, _, err = update(capsys, "--dry-run", "--diff", name)

    assert code == 1 and name in err and "no such folder" in err
    assert not paths.cache().exists()


def test_diff_file_through_a_folder_named_apm(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))
    (home / "elsewhere").mkdir()
    (home / "proj").mkdir()
    (home / "proj" / ".Apm").symlink_to(home / "elsewhere")

    code, _, err = update(capsys, "--dry-run", "--diff", "proj/.Apm/review.diff")

    assert code == 1 and "proj/.Apm/review.diff" in err and ".apm" in err
    assert not paths.cache().exists() and not list((home / "elsewhere").iterdir())


def test_removed_skill_in_the_diff(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "/grilling\n", "grilling/SKILL.md": "g\n"})
    write_config(
        'entries = ["mp/tdd"]\n' + git_source("mp", upstream, f'ref = "{old}"\n')
    )
    assert main(["build", "--no-install"]) == 0
    upstream.commit({"tdd/SKILL.md": "1\n"})

    assert update(capsys, "--dry-run", "--diff", "review.diff")[0] == 0

    text = (home / "review.diff").read_text()
    assert text.startswith(HEADER + "# - mp/grilling\n# ~ mp/tdd\n")


def test_only_removals_in_the_diff(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    old = upstream.commit({"tdd/SKILL.md": "1\n", "grilling/SKILL.md": "g\n"})
    skill(home / "own" / "notes", "/grilling\n")
    write_config(
        'entries = ["own/notes"]\n'
        + git_source("mp", upstream, f'ref = "{old}"\n')
        + '[sources.own]\npath = "~/own"\n'
    )
    assert main(["build", "--no-install"]) == 0
    upstream.git("rm", "-q", "-r", "grilling")
    upstream.commit({})

    code, out, _ = update(capsys, "--dry-run", "--diff", "review.diff")

    assert code == 0 and diff_lines(out)[:2] == [LEGEND, "- mp/grilling"]
    assert (home / "review.diff").read_text() == HEADER + "# - mp/grilling\n"


def test_diff_file_through_a_link_in_a_skills_folder(
    home: Path, upstream: Upstream, capsys: Capsys
) -> None:
    upstream.commit({"tdd/SKILL.md": "1\n"})
    write_config('entries = ["mp/tdd"]\n' + git_source("mp", upstream))
    (home / "elsewhere").mkdir()
    folder = skill(home / "skills" / "foo")
    (folder / "out").symlink_to(home / "elsewhere")

    code, _, err = update(capsys, "--dry-run", "--diff", "skills/foo/out/x.diff")

    assert code == 1 and "skills/foo/out/x.diff" in err and "SKILL.md" in err
    assert not paths.cache().exists() and not list((home / "elsewhere").iterdir())
