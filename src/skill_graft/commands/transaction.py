"""Resolves the hull and writes the lock and the vendored copies: the one place every
command that writes the lock does it; and loads the config, for every command,
writing or not."""

import os
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skill_graft.infra import files, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, lines_of, notice
from skill_graft.pipeline import compute, config, lock, vendor
from skill_graft.pipeline.config import SkillId
from skill_graft.pipeline.hull import Hull

# Keeps git from converting the committed copies' and patches' line endings.
ATTRIBUTES = "/.apm/skills/** -text\n/patches/** -text\n"


@dataclass
class Resolution:
    """The hull; the hashes the lock records, `None` for the patched copies'; the
    caller's writes, each a file and the call that replaces it, run before the
    lock; a check of the lock's text before anything is vendored; and, after the
    block, the lock's text, written or not."""

    hull: Hull
    hashes: dict[SkillId, str] | None = None
    writes: list[tuple[Path, Callable[[], None]]] = field(default_factory=list)
    verify: Callable[[str], None] | None = None
    lock_text: str = ""


def load(scope: paths.Scope, warnings: list[str]) -> config.Config:
    """The config, its warnings added to `warnings`."""
    loaded = config.load(scope)
    warnings.extend(loaded.warnings)
    return loaded


def _keep_old(locked: dict[str, Any] | None) -> Callable[[Path], bool]:
    """Whether a `skills.old` holds exactly the lock's copies, none missing."""

    def keep(old: Path) -> bool:
        if locked is None or lock.recorded(locked) is None:
            return False
        names = {p.name for p in old.iterdir()}
        return names == lock.deployed_names(locked) and not lock.copy_problems(
            old, locked
        )

    return keep


def pending(skills: Path, locked: dict[str, Any] | None) -> Path:
    """The folder holding the copies of `skills`, as a run killed mid-swap would
    leave it: the one the next run recovers, the loaded lock `locked` deciding."""
    return vendor.pending(skills, _keep_old(locked))


def check_copies(skills: Path, locked: dict[str, Any] | None) -> None:
    """Refuses copies in `skills`, as a run killed mid-swap would leave it, that
    the loaded lock `locked` does not record; and any copies at all if there is
    no lock to check them against."""
    folder = pending(skills, locked)
    if locked is None or lock.recorded(locked) is None:
        if folder.exists() and any(folder.iterdir()):
            raise SkillGraftError(
                "skill-graft.lock is missing, unreadable or of another version, so"
                f" {folder} cannot be checked: delete {folder}, then run"
                " `skill-graft resolve`"
            )
        return
    if problems := lock.copy_problems(folder, locked):
        raise SkillGraftError(
            "vendored copies not as skill-graft.lock records them:",
            *(f"  {problem}" for problem in problems),
            "move an edit into a patch, or delete the folder to vendor it again",
        )


def check_into(into: Path) -> None:
    """Refuses an `--into` folder `deploy` or `vet` could not use without harm:
    anything but an existing, empty folder, or one in a package or in or around
    the cache."""
    if not into.exists():
        raise SkillGraftError(f"--into {into}: no such folder")
    if not into.is_dir():
        raise SkillGraftError(f"--into {into}: not a folder")
    if any(into.iterdir()):
        raise SkillGraftError(f"--into {into}: not empty")
    resolved = paths.folded(into.resolve())
    # As given too, but without `..`: a path only passing through a package is fine.
    given = paths.folded(Path(os.path.normpath(into.absolute())))
    if any(paths.in_package(p) for p in (given, resolved)):
        raise SkillGraftError(f"--into {into}: inside a package (.apm/skill-graft)")
    if paths.overlap(resolved, paths.folded(cache := paths.cache().resolve())):
        raise SkillGraftError(f"--into {into}: overlaps the cache {cache}")


def check_into_sources(into: Path, loaded: config.Config) -> None:
    """Refuses an `--into` folder inside a path source, compared resolved."""
    folded = paths.folded(into.resolve())
    for alias, source in sorted(loaded.sources.items()):
        if isinstance(source, config.PathSource) and folded.is_relative_to(
            paths.folded(source.folder)
        ):
            raise SkillGraftError(f"--into {into}: inside source {alias!r}")


def _machine_specific(
    scope: paths.Scope, loaded: config.Config, write: bool
) -> list[str]:
    """A warning per path source a project's lock records absolute; for a dry
    run, would record."""
    if scope.user:
        return []
    records = "records" if write else "would record"
    return [
        f"source {alias!r}: skill-graft.lock {records} {source.folder} absolute, so other"
        " machines need it at the same place; a path inside the project, or ~/"
        " without .., reads the same on every machine"
        for alias, source in loaded.sources.items()
        if isinstance(source, config.PathSource)
        and lock.portable_path(scope, source) is None
    ]


@contextmanager
def resolving(
    scope: paths.Scope,
    loaded: config.Config,
    warnings: list[str],
    cache: Cache,
    refs: dict[str, str] | None = None,
    lock_file: Path | None = None,
    write: bool = True,
    skills: Path | None = None,
) -> Generator[Resolution]:
    """The hull, every source at its ref but those `refs` names; after the block,
    the lock rendered and verified while the patched copies exist and, unless
    `write` is false, the copies staged; then the caller's writes run in order, the
    package's `.gitattributes` written if missing, the copies swapped into `skills`
    and the lock written. On any failure, the swap is undone and each file
    written restored, in reverse, to its bytes right before its write.

    First checks the copies in `skills` against the lock.
    Adds the hull's warnings to `warnings` at once, so a later failure keeps them,
    and, for the package's own lock, one per path source it records absolute.
    """
    if lock_file is None:  # the lock a project commits; `deploy --into` gives its own
        warnings.extend(_machine_specific(scope, loaded, write))
    skills = skills or scope.skills
    lock_file = lock_file or scope.lock_file
    locked = lock.load(lock_file)
    check_copies(skills, locked)
    with compute.compute_hull(scope, loaded, cache, refs) as hull:
        warnings.extend(hull.warnings)
        resolution = Resolution(hull)
        yield resolution
        resolution.lock_text = lock.render(
            scope, loaded, refs or {}, hull, resolution.hashes
        )
        if resolution.verify is not None:
            resolution.verify(resolution.lock_text)
        if write:
            vendor.recover(skills, _keep_old(locked))
            vendor.stage(hull, skills)
    if not write:
        return
    writes = list(resolution.writes)
    attributes = scope.package / ".gitattributes"
    if skills == scope.skills and not attributes.exists():
        writes.append(
            (attributes, lambda: files.atomic_write(attributes, ATTRIBUTES.encode()))
        )
    found: list[tuple[Path, bytes | None]] = []
    try:
        for file, replace in writes:
            # Read right before: a restore puts back what this write replaced.
            found.append((file, file.read_bytes() if file.exists() else None))
            replace()
        vendor.swap(skills)
        lock.write(resolution.lock_text, lock_file)
    except BaseException:
        try:
            vendor.swap_back(skills)
        except OSError as error:
            notice(f"could not restore {skills}: {error}")
        for file, data in reversed(found):
            _restore(file, data)
        raise
    try:  # once the lock is written, nothing undoes it; the next run recovers
        vendor.clear_old(skills)
    except (SkillGraftError, OSError) as error:
        for line in lines_of(error):
            notice(line)


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
