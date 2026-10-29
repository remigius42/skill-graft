"""Resolves the hull and writes the lock: the `resolve` command, and the one place
every command that writes the lock does it."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from skill_graft.commands import explain
from skill_graft.infra import files, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import notice
from skill_graft.pipeline import compute, config, lock
from skill_graft.pipeline.config import SkillId
from skill_graft.pipeline.hull import Hull


@dataclass
class Resolution:
    """The hull; the hashes the lock records, `None` for the patched copies'; and
    the caller's writes, each a file and the call that replaces it, run before the
    lock."""

    hull: Hull
    hashes: dict[SkillId, str] | None = None
    writes: list[tuple[Path, Callable[[], None]]] = field(default_factory=list)


def resolve(scope: paths.Scope, warnings: list[str]) -> None:
    """Resolves the hull, writes the lock, and prints the tree and suggestions."""
    with resolving(scope, load(warnings), warnings) as resolution:
        pass
    explain.show(resolution.hull)


def load(warnings: list[str]) -> config.Config:
    """The config, its warnings added to `warnings`."""
    loaded = config.load()
    warnings.extend(loaded.warnings)
    return loaded


@contextmanager
def resolving(
    scope: paths.Scope,
    loaded: config.Config,
    warnings: list[str],
    cache: Cache | None = None,
    refs: dict[str, str] | None = None,
    lock_file: Path | None = None,
    write: bool = True,
) -> Generator[Resolution]:
    """The hull, every source at its ref but those `refs` names; after the block,
    unless `write` is false, the lock rendered while the patched copies exist, the
    caller's writes run in order, then the lock written. On any failure, each file
    written is restored, in reverse, to its bytes right before its write.

    Adds the hull's warnings to `warnings` at once, so a later failure keeps them.
    """
    with compute.compute_hull(loaded, cache, refs) as hull:
        warnings.extend(hull.warnings)
        resolution = Resolution(hull)
        yield resolution
        if not write:
            return
        text = lock.render(loaded, refs or {}, hull, resolution.hashes)
    found: list[tuple[Path, bytes | None]] = []
    try:
        for file, replace in resolution.writes:
            # Read right before: a restore puts back what this write replaced.
            found.append((file, file.read_bytes() if file.exists() else None))
            replace()
        lock.write(text, lock_file or scope.lock_file)
    except BaseException:
        for file, data in reversed(found):
            _restore(file, data)
        raise


def _restore(file: Path, data: bytes | None) -> None:
    """Puts `data` back in `file`, or removes it if it was missing; a failure is
    named, not raised: the error that made it restore is the one to report."""
    try:
        if data is None:
            file.unlink(missing_ok=True)
        else:
            files.atomic_write(file, data)
    except OSError as error:
        notice(f"could not restore {file}: {error}")
