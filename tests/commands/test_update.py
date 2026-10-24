"""The `update` spec, through `skill-graft update`."""

import os
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import FakeApm, Upstream, make_patch, skill, vendored, write_config

from skill_graft.cli import main
from skill_graft.infra import cache, paths
from skill_graft.pipeline import config, deployed

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
