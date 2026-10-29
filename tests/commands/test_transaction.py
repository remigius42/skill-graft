"""The one place that resolves the hull and writes the lock."""

from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import skill, write_config

from skill_graft.commands import transaction
from skill_graft.infra import files, paths
from skill_graft.infra.cache import Cache
from skill_graft.pipeline import config, lock
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
        scope, config.load(scope), [], Cache.default(), lock_file=other
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
