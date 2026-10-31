"""The one place that resolves the hull and writes the lock."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import skill, write_config

from skill_graft.commands import transaction
from skill_graft.commands.transaction import Resolution
from skill_graft.infra import files, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import config, lock, vendor
from skill_graft.pipeline.config import SkillId


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
        with transaction.resolving(
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
        with transaction.resolving(
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
        with transaction.resolving(
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
        with transaction.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(first, b"new"))
            resolution.writes.append(writing(second, b"new"))

    assert [f for f in restored if f in (first, second)] == [second, first]


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
        with transaction.resolving(
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
        with transaction.resolving(
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
        with transaction.resolving(
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

    with transaction.resolving(scope, config.load(scope), [], Cache.default()):
        pass
    with transaction.resolving(
        scope, config.load(scope), [], Cache.default(), lock_file=other, checked=True
    ):
        pass

    assert written == [scope.lock_file, other]


def test_set_hashes_are_recorded_and_none_computed(
    scope: paths.Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    computed = []
    monkeypatch.setattr(lock, "skill_hashes", lambda hull: computed.append(hull))

    with transaction.resolving(
        scope, config.load(scope), [], Cache.default()
    ) as resolution:
        resolution.hashes = {SkillId("own", "tdd"): "f" * 64}

    assert computed == []
    assert "f" * 64 in scope.lock_file.read_text()


def test_no_write_writes_nothing(scope: paths.Scope, tmp_path: Path) -> None:
    file = tmp_path / "file"

    with transaction.resolving(
        scope, config.load(scope), [], Cache.default(), write=False
    ) as resolution:
        resolution.writes.append(writing(file, b"new"))

    assert not file.exists() and not scope.lock_file.exists()


def test_no_write_keeps_the_lock_it_would_write(scope: paths.Scope) -> None:
    hashes = {SkillId("own", "tdd"): "f" * 64}
    with transaction.resolving(
        scope, config.load(scope), [], Cache.default(), write=False
    ) as dry:
        dry.hashes = hashes

    with transaction.resolving(scope, config.load(scope), [], Cache.default()) as real:
        real.hashes = hashes

    assert dry.lock_text == scope.lock_file.read_text()


def test_hull_warnings_kept_though_the_lock_write_fails(
    scope: paths.Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))
    warnings: list[str] = []

    with pytest.raises(OSError):
        with transaction.resolving(
            scope, config.load(scope), warnings, Cache.default()
        ):
            pass

    assert any("`own/tdd` calls `/foo`" in warning for warning in warnings)


def resolve(scope: paths.Scope, **options: Any) -> Resolution:
    """Runs `resolving` with an empty block."""
    with transaction.resolving(
        scope, config.load(scope), [], Cache.default(), **options
    ) as resolution:
        pass
    return resolution


def snapshot(folder: Path) -> dict[str, bytes]:
    """Each file under `folder` by relative path, with its bytes."""
    return {
        str(f.relative_to(folder)): f.read_bytes()
        for f in sorted(folder.rglob("*"))
        if f.is_file()
    }


def copy_of(scope: paths.Scope) -> Path:
    """`own/tdd`'s Vendored copy's `SKILL.md`."""
    return scope.skills / "tdd" / "SKILL.md"


def test_writes_copies_with_the_lock(scope: paths.Scope) -> None:
    resolve(scope)

    hashes = lock.recorded(lock.load(scope.lock_file))
    assert hashes == {SkillId("own", "tdd"): lock.folder_hash(scope.skills / "tdd")}
    assert copy_of(scope).read_text() == "Run /foo.\n"
    assert sorted(p.name for p in scope.skills.parent.iterdir()) == ["skills"]


@pytest.mark.parametrize("error", [OSError("disk full"), KeyboardInterrupt()])
def test_lock_write_fails_restores_copies(
    scope: paths.Scope,
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    resolve(scope)
    before = snapshot(scope.package)
    (home / "src" / "tdd" / "SKILL.md").write_text("changed\n")
    monkeypatch.setattr(lock, "write", failing(error))

    with pytest.raises(type(error)):
        resolve(scope)

    assert snapshot(scope.package) == before
    assert sorted(p.name for p in scope.skills.parent.iterdir()) == ["skills"]


def test_interrupt_restores_copies(
    scope: paths.Scope, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolve(scope)
    before = snapshot(scope.package)
    (home / "src" / "tdd" / "SKILL.md").write_text("changed\n")
    swap = vendor.swap

    def swap_then_interrupt(skills: Path) -> None:
        swap(skills)
        raise KeyboardInterrupt

    monkeypatch.setattr(vendor, "swap", swap_then_interrupt)

    with pytest.raises(KeyboardInterrupt):
        resolve(scope)

    assert snapshot(scope.package) == before


def test_swap_back_failure_still_restores_the_toml(
    scope: paths.Scope,
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    resolve(scope)
    toml = scope.config_file.read_bytes()
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))
    monkeypatch.setattr(vendor, "swap_back", failing(OSError("busy")))

    with pytest.raises(OSError, match="disk full"):
        with transaction.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(scope.config_file, b"edited"))

    assert scope.config_file.read_bytes() == toml
    err = capsys.readouterr().err
    assert str(scope.skills) in err and "busy" in err


def test_clear_old_failure_keeps_lock_and_copies(
    scope: paths.Scope, home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolve(scope)
    (home / "src" / "tdd" / "SKILL.md").write_text("changed\n")
    monkeypatch.setattr(vendor, "clear_old", failing(OSError("busy")))

    resolve(scope)

    assert copy_of(scope).read_text() == "changed\n"
    assert lock.copy_problems(scope.skills, lock.load(scope.lock_file) or {}) == []


def test_previous_copies_left_behind_never_replace_an_edit(
    scope: paths.Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolve(scope)
    real = shutil.rmtree
    stuck = [True]

    def refusing_previous(path: Path, *args: Any, **kwargs: Any) -> None:
        if stuck[0] and Path(path).name.startswith("skills."):
            raise OSError("busy")
        real(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", refusing_previous)
    resolve(scope)  # the same hull: the previous copies are the lock's too
    stuck[0] = False
    copy_of(scope).write_text("edited\n")

    with pytest.raises(SkillGraftError, match="tdd"):
        resolve(scope)

    assert copy_of(scope).read_text() == "edited\n"


def test_edited_copy_refused_before_any_write(
    scope: paths.Scope, tmp_path: Path
) -> None:
    resolve(scope)
    copy_of(scope).write_text("edited\n")
    before = snapshot(scope.package)
    file = tmp_path / "file"

    with pytest.raises(SkillGraftError) as raised:
        with transaction.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.writes.append(writing(file, b"new"))

    message = str(raised.value)
    assert str(scope.skills / "tdd") in message
    assert "patch" in message and "delete" in message
    assert snapshot(scope.package) == before and not file.exists()


@pytest.mark.parametrize("text", ["not [toml\n", "version = 2\n", None])
def test_unreadable_lock_cannot_check(scope: paths.Scope, text: str | None) -> None:
    resolve(scope)
    if text is None:
        scope.lock_file.unlink()
    else:
        scope.lock_file.write_text(text)
    before = snapshot(scope.package)

    with pytest.raises(SkillGraftError) as raised:
        resolve(scope)

    message = str(raised.value)
    assert "cannot be checked" in message and "differs" not in message
    assert f"delete {scope.skills}" in message and "skill-graft resolve" in message
    assert snapshot(scope.package) == before


def test_dry_run_checks_copies(scope: paths.Scope) -> None:
    resolve(scope)
    copy_of(scope).write_text("edited\n")

    with pytest.raises(SkillGraftError, match="tdd"):
        resolve(scope, write=False)


def killed_run(scope: paths.Scope) -> dict[str, bytes]:
    """Leaves `skills.old` and `skills.new` beside the copies, as a run killed
    mid-swap; returns what `.apm/` holds."""
    resolve(scope)
    shutil.copytree(scope.skills, scope.skills.with_name("skills.old"))
    skill(scope.skills.with_name("skills.new") / "half")
    return snapshot(scope.skills.parent)


def test_dry_run_leaves_a_killed_run(scope: paths.Scope) -> None:
    before = killed_run(scope)

    resolve(scope, write=False)

    assert snapshot(scope.skills.parent) == before


def test_verify_refusal_touches_nothing(scope: paths.Scope, home: Path) -> None:
    before = killed_run(scope)
    (home / "src" / "tdd" / "SKILL.md").write_text("changed\n")
    lock_bytes = scope.lock_file.read_bytes()
    seen: list[str] = []

    def refuse(text: str) -> None:
        seen.append(text)
        raise SkillGraftError("refused")

    with pytest.raises(SkillGraftError, match="refused"):
        with transaction.resolving(
            scope, config.load(scope), [], Cache.default()
        ) as resolution:
            resolution.verify = refuse

    assert len(seen) == 1 and "changed" not in seen[0] and "own/tdd" in seen[0]
    assert snapshot(scope.skills.parent) == before
    assert scope.lock_file.read_bytes() == lock_bytes


def test_killed_before_lock_recovered(scope: paths.Scope) -> None:
    resolve(scope)
    # Swapped in, the lock not yet written: `skills.old` holds what it records.
    shutil.copytree(scope.skills, scope.skills.with_name("skills.old"))
    copy_of(scope).write_text("vendored by the killed run\n")

    resolve(scope)

    assert copy_of(scope).read_text() == "Run /foo.\n"
    assert not scope.skills.with_name("skills.old").exists()


def test_killed_after_lock_recovered(scope: paths.Scope, home: Path) -> None:
    resolve(scope)
    previous = shutil.copytree(scope.skills, home / "previous")
    (home / "src" / "tdd" / "SKILL.md").write_text("changed\n")
    resolve(scope)
    # The lock written, the previous copies not yet removed.
    previous.rename(scope.skills.with_name("skills.old"))

    resolve(scope)

    assert copy_of(scope).read_text() == "changed\n"
    assert not scope.skills.with_name("skills.old").exists()


def test_killed_after_lock_adding_only_recovered(
    scope: paths.Scope, home: Path
) -> None:
    resolve(scope)
    previous = shutil.copytree(scope.skills, home / "previous")
    skill(home / "src" / "notes")
    write_config('entries = ["own/tdd", "own/notes"]\n[sources.own]\npath = "~/src"\n')
    resolve(scope)
    previous.rename(scope.skills.with_name("skills.old"))

    resolve(scope)

    assert sorted(p.name for p in scope.skills.iterdir()) == ["notes", "tdd"]
    assert not scope.skills.with_name("skills.old").exists()


ATTRIBUTES = "/.apm/skills/** -text\n/patches/** -text\n"


def test_gitattributes_written_if_missing(scope: paths.Scope) -> None:
    resolve(scope)

    assert (scope.package / ".gitattributes").read_text() == ATTRIBUTES


def test_own_gitattributes_kept(scope: paths.Scope) -> None:
    (scope.package / ".gitattributes").write_bytes(b"* -text\r\n")

    resolve(scope)

    assert (scope.package / ".gitattributes").read_bytes() == b"* -text\r\n"


def test_into_writes_no_gitattributes(scope: paths.Scope, tmp_path: Path) -> None:
    into = tmp_path / "into"

    resolve(
        scope,
        skills=into / ".apm" / "skills",
        lock_file=into / "skill-graft.lock",
        checked=True,
    )

    assert (into / ".apm" / "skills" / "tdd").is_dir()
    assert not (scope.package / ".gitattributes").exists()
    assert not (into / ".gitattributes").exists()
    assert not scope.skills.exists()


def test_first_resolve_lock_write_fails_leaves_no_copies(
    scope: paths.Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lock, "write", failing(OSError("disk full")))

    with pytest.raises(OSError):
        resolve(scope)

    held = {str(p.relative_to(scope.package)) for p in scope.package.rglob("*")}
    assert held == {"skill-graft.toml", ".apm"}


def test_checked_skips_the_check(scope: paths.Scope) -> None:
    resolve(scope)
    copy_of(scope).write_text("edited\n")

    resolve(scope, write=False, checked=True)
