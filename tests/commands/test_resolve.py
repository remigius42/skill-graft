"""The `resolve` spec: the command, the lock it writes, and the tree it prints; and
the one place that resolves the hull and writes the lock."""

import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import Upstream, configure, make_patch, skill, write_config

from skill_graft.cli import main
from skill_graft.commands import resolve
from skill_graft.infra import files, paths
from skill_graft.infra.cache import Cache
from skill_graft.pipeline import config, lock, vendor
from skill_graft.pipeline.config import SkillId
from skill_graft.pipeline.hull import Hull

Capsys: TypeAlias = pytest.CaptureFixture[str]


def lock_file(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / "skill-graft.lock"


def test_resolve_succeeds(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tdd", "/grilling\n")
    skill(home / "own" / "grilling")
    configure(["own/tdd"], own="~/own")
    config = home / ".apm" / "skill-graft" / "skill-graft.toml"
    before = config.read_bytes()

    assert main(["resolve"]) == 0

    skills = tomllib.loads(lock_file(home).read_text())["skills"]
    assert [s["id"] for s in skills] == ["own/grilling", "own/tdd"]
    assert config.read_bytes() == before
    assert not (home / ".apm" / "skill-graft" / ".apm").exists()


def test_tree(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, /notes and Skill(x)\n")
    skill(home / "mp" / "grilling", "/notes and /tdd\n")
    skill(home / "mp" / "notes")
    skill(home / "own" / "x")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/x" = "own/x"\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd\n"
        "├── mp/grilling (/grilling)\n"
        "│   ├── mp/notes (/notes)\n"
        "│   └── mp/tdd (/tdd) (*)\n"
        "├── mp/notes (/notes) (*)\n"
        "└── own/x (Skill(x), bind)\n"
    )


def test_tree_of_two_entries(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "a", "/b\n")
    skill(home / "own" / "b")
    configure(["own/a", "own/b"], own="~/own")

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == "own/a\n└── own/b (/b) (*)\nown/b\n"


def test_renames_marked(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, `grilling` and `notes`\n")
    skill(home / "mp" / "grilling")
    skill(home / "mp" / "notes")
    write_config(
        'entries = ["mp/tdd", "mp/notes"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/tdd" = "mp-tdd"\n"mp/grilling" = "mp-grilling"\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd as mp-tdd\n"
        "├── mp/grilling as mp-grilling (/grilling)\n"
        "└── mp/grilling as mp-grilling (`grilling`, prose) (*)\n"
        "mp/notes\n"
    )


def test_patches_marked(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling", "# grilling\n")
    folder = home / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True)
    for name, text in [("tdd", "/grilling\n"), ("grilling", "# grilling\n")]:
        data = make_patch(tmp_path, {"SKILL.md": text}, {"SKILL.md": text + "more\n"})
        (folder / f"{name}.patch").write_bytes(data)
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/grilling" = "mp-grilling"\n[patches]\n'
        '"mp/tdd" = ["patches/tdd.patch"]\n"mp/grilling" = ["patches/grilling.patch"]\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd (patched)\n└── mp/grilling as mp-grilling (patched) (/grilling)\n"
    )


def test_bound_prose_shown(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/notes and `notes`, then notes-x\n")
    skill(home / "own" / "grill")
    skill(home / "own" / "g-x")
    write_config(
        'entries = ["mp/tdd", "own/g-x"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n'
        '[bind]\n"mp/notes" = "own/grill"\n"mp/notes-x" = "own/g-x"\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd\n"
        "├── own/grill (/notes, bind)\n"
        "├── own/grill (`notes`, prose, bind) (*)\n"
        "└── own/g-x (notes-x, prose, bind) (*)\n"
        "own/g-x\n"
    )


def test_suggestion_printed(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, then diagnosing-bugs and `notes`\n")
    skill(home / "mp" / "grilling", "see diagnosing-bugs\n")
    skill(home / "mp" / "diagnosing-bugs")
    skill(home / "mp" / "notes")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd\n"
        "└── mp/grilling (/grilling)\n"
        "\n"
        "mentioned in prose, not in the hull (`skill-graft add <skill id>` to include):\n"
        "  mp/diagnosing-bugs, by mp/grilling, mp/tdd\n"
        "  mp/notes, by mp/tdd\n"
    )


def test_build_announces_suggestions(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "then diagnosing-bugs and `notes`\n")
    skill(home / "mp" / "diagnosing-bugs")
    skill(home / "mp" / "notes")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["build", "--no-install"]) == 0

    out, err = capsys.readouterr()
    assert "skill-graft: 2 prose suggestion(s): run skill-graft resolve\n" in err
    assert "diagnosing-bugs" not in out + err


def test_build_without_suggestions_prints_no_line(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/notes\n")
    skill(home / "mp" / "notes")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["build", "--no-install"]) == 0

    assert "prose suggestion(s)" not in capsys.readouterr().err


def test_tree_leaves_out_prose_not_rewritten(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "a", "/b, then `b` and `c`\n")
    skill(home / "own" / "b")
    skill(home / "own" / "c")
    configure(["own/a", "own/c"], own="~/own")

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == "own/a\n└── own/b (/b)\nown/c\n"


def test_resolution_error(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tdd", "/notes\n")
    skill(home / "own" / "notes")
    configure(["own/tdd"], own="~/own")
    main(["resolve"])
    before = lock_file(home).read_bytes()
    skill(home / "own" / "tdd", "/missing-entry\n")
    configure(["own/tdd", "own/nope"], own="~/own")

    assert main(["resolve"]) == 1

    assert lock_file(home).read_bytes() == before


def test_git_source_without_ref(tmp_path: Path, capsys: Capsys) -> None:
    write_config('[sources.mp]\ngit = "/srv/s"\n')

    assert main(["resolve"]) == 1

    assert "skill-graft update mp" in capsys.readouterr().err


def test_upstream_moved_on(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    a = upstream.commit({"tdd/SKILL.md": "a\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{a}"\n'
    )
    main(["resolve"])
    upstream.commit({"tdd/SKILL.md": "b\n"})
    upstream.path.rename(tmp_path / "gone")  # contacting the remote would fail

    assert main(["resolve"]) == 0

    assert tomllib.loads(lock_file(home).read_text())["sources"]["mp"]["ref"] == a


def test_symlinked_config(home: Path, tmp_path: Path) -> None:
    skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    config = home / ".apm" / "skill-graft" / "skill-graft.toml"
    elsewhere = tmp_path / "dotfiles"
    elsewhere.mkdir()
    config.rename(elsewhere / "skill-graft.toml")
    config.symlink_to(elsewhere / "skill-graft.toml")

    assert main(["resolve"]) == 0

    assert lock_file(home).is_file()
    assert [p.name for p in elsewhere.iterdir()] == ["skill-graft.toml"]


def test_build_writes_the_lock(home: Path) -> None:
    skill(home / "own" / "tdd", "/grilling\n")
    skill(home / "own" / "grilling")
    configure(["own/tdd"], own="~/own")

    assert main(["build", "--no-install"]) == 0

    skills = tomllib.loads(lock_file(home).read_text())["skills"]
    assert [s["id"] for s in skills] == ["own/grilling", "own/tdd"]


def test_lock_hashes_what_was_vendored(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tdd = skill(home / "own" / "tdd", "vendored\n")
    configure(["own/tdd"], own="~/own")
    copy = vendor.vendor

    def copy_then_edit(hull: Hull, skills: Path) -> None:
        copy(hull, skills)
        (tdd / "SKILL.md").write_text("edited during the build\n")

    monkeypatch.setattr(vendor, "vendor", copy_then_edit)

    assert main(["build", "--no-install"]) == 0

    vendored = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd"
    locked = tomllib.loads(lock_file(home).read_text())["skills"][0]["hash"]
    assert locked == lock.folder_hash(vendored)


def test_git_file_is_not_hashed(home: Path) -> None:
    tdd = skill(home / "own" / "tdd")
    (tdd / ".git").write_text("gitdir: ../.git/modules/tdd\n")  # a submodule
    configure(["own/tdd"], own="~/own")

    def locked() -> str:
        hash_: str = tomllib.loads(lock_file(home).read_text())["skills"][0]["hash"]
        return hash_

    assert main(["resolve"]) == 0
    resolved = locked()
    assert main(["build", "--no-install"]) == 0

    assert locked() == resolved


def test_vendoring_fails(home: Path) -> None:
    tdd = skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    main(["build", "--no-install"])
    before = lock_file(home).read_bytes()
    (tdd / "dangling").symlink_to("missing")

    assert main(["build", "--no-install"]) == 1

    assert lock_file(home).read_bytes() == before


def test_lock_edited_by_hand(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    a = upstream.commit({"tdd/SKILL.md": "a\n"})
    b = upstream.commit({"tdd/SKILL.md": "b\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{a}"\n'
    )
    main(["build", "--no-install"])
    lock_file(home).write_text(lock_file(home).read_text().replace(a, b))

    assert main(["build", "--no-install"]) == 0

    vendored = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd" / "SKILL.md"
    assert vendored.read_text() == "a\n"
    assert tomllib.loads(lock_file(home).read_text())["sources"]["mp"]["ref"] == a


@pytest.fixture
def scope(home: Path) -> paths.Scope:
    """User scope whose entry `own/tdd` calls `/foo`, which no source has."""
    skill(home / "src" / "tdd", "Run /foo.\n")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')
    return paths.Scope(home)


def writing(file: Path, data: bytes) -> tuple[Path, Callable[[], None]]:
    """A write the caller appends: replaces `file` with `data`."""

    def write() -> None:
        file.write_bytes(data)

    return file, write


def recording(calls: list[object]) -> Callable[..., str]:
    """A stand-in for `lock.render` that notes each call."""

    def render(*args: object) -> str:
        calls.append(args)
        return ""

    return render


def failing(error: BaseException) -> Callable[..., None]:
    def fail(*args: object, **kwargs: object) -> None:
        raise error

    return fail


def test_nothing_written_when_the_block_raises(
    scope: paths.Scope, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[object] = []
    monkeypatch.setattr(lock, "render", recording(rendered))
    file = tmp_path / "file"

    with pytest.raises(RuntimeError):
        with resolve.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(file, b"new"))
            raise RuntimeError

    assert rendered == [] and not file.exists() and not scope.lock_file.exists()


def test_render_failing_runs_no_write(
    scope: paths.Scope, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lock, "render", failing(OSError("render")))
    file = tmp_path / "file"

    with pytest.raises(OSError, match="render"):
        with resolve.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(file, b"new"))

    assert not file.exists()


def test_failing_lock_write_restores_the_writes(
    scope: paths.Scope, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kept, missing = tmp_path / "kept", tmp_path / "missing"
    kept.write_bytes(b"old")
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))

    with pytest.raises(OSError, match="disk full"):
        with resolve.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(kept, b"new"))
            resolution.writes.append(writing(missing, b"new"))

    assert kept.read_bytes() == b"old" and not missing.exists()


def test_restores_in_reverse_order(
    scope: paths.Scope, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    restored = []
    monkeypatch.setattr(files, "atomic_write", lambda f, d: restored.append(f))
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))

    with pytest.raises(OSError):
        with resolve.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(first, b"new"))
            resolution.writes.append(writing(second, b"new"))

    assert restored == [second, first]


def test_interrupted_write_restores_itself_and_the_earlier(
    scope: paths.Scope, tmp_path: Path
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"1")
    second.write_bytes(b"2")

    def replace_then_interrupt() -> None:
        second.write_bytes(b"new")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        with resolve.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(first, b"new"))
            resolution.writes.append((second, replace_then_interrupt))

    assert (first.read_bytes(), second.read_bytes()) == (b"1", b"2")
    assert not scope.lock_file.exists()


def test_restores_the_bytes_found_right_before_the_write(
    scope: paths.Scope, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / "file"
    file.write_bytes(b"at entry")
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))

    with pytest.raises(OSError):
        with resolve.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            file.write_bytes(b"saved meanwhile")
            resolution.writes.append(writing(file, b"new"))

    assert file.read_bytes() == b"saved meanwhile"


def test_failed_restore_is_a_notice_and_the_next_still_runs(
    scope: paths.Scope,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    first.write_bytes(b"1")
    second.write_bytes(b"2")
    real = files.atomic_write

    def refusing_second(file: Path, data: bytes) -> None:
        if file == second:
            raise OSError("read-only")
        real(file, data)

    monkeypatch.setattr(files, "atomic_write", refusing_second)
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))

    with pytest.raises(OSError, match="disk full"):
        with resolve.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(first, b"new"))
            resolution.writes.append(writing(second, b"new"))

    assert first.read_bytes() == b"1"
    err = capsys.readouterr().err
    assert str(second) in err and "read-only" in err


def test_lock_goes_through_lock_write(
    scope: paths.Scope, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    written: list[Path | None] = []
    monkeypatch.setattr(lock, "write", lambda text, file: written.append(file))
    other = tmp_path / "other.lock"

    with resolve.resolving(scope, config.load(scope), [], Cache.default()):
        pass
    with resolve.resolving(
        scope, config.load(scope), [], Cache.default(), lock_file=other
    ):
        pass

    assert written == [scope.lock_file, other]


def test_set_hashes_are_recorded_and_none_computed(
    scope: paths.Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    computed = []
    monkeypatch.setattr(lock, "skill_hashes", lambda hull: computed.append(hull))

    with resolve.resolving(
        scope, config.load(scope), [], Cache.default()
    ) as resolution:
        resolution.hashes = {SkillId("own", "tdd"): "f" * 64}

    assert computed == []
    assert "f" * 64 in scope.lock_file.read_text()


def test_no_write_renders_and_writes_nothing(
    scope: paths.Scope, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rendered: list[object] = []
    monkeypatch.setattr(lock, "render", recording(rendered))
    file = tmp_path / "file"

    with resolve.resolving(
        scope, config.load(scope), [], Cache.default(), write=False
    ) as resolution:
        resolution.writes.append(writing(file, b"new"))

    assert rendered == [] and not file.exists() and not scope.lock_file.exists()


def test_hull_warnings_kept_though_the_lock_write_fails(
    scope: paths.Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))
    warnings: list[str] = []

    with pytest.raises(OSError):
        with resolve.resolving(scope, config.load(scope), warnings, Cache.default()):
            pass

    assert any("`own/tdd` calls `/foo`" in warning for warning in warnings)
