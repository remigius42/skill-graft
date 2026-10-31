"""Resolves the hull and writes the lock and the vendored copies: the one place every
command that writes the lock does it; and loads the config, for every command,
writing or not."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skill_graft.infra import files, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, notice
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


def check_copies(skills: Path, locked: dict[str, Any] | None) -> None:
    """Refuses copies in `skills`, as a run killed mid-swap would leave it, that
    the loaded lock `locked` does not record; and any copies at all if there is
    no lock to check them against."""
    folder = vendor.pending(skills, _keep_old(locked))
    if locked is None or lock.recorded(locked) is None:
        if folder.exists() and any(folder.iterdir()):
            raise SkillGraftError(
                f"skill-graft.lock is missing or unreadable, so {skills} cannot be"
                f" checked: delete {skills}, then run `skill-graft resolve`"
            )
        return
    if problems := lock.copy_problems(folder, locked):
        lines = "".join(f"\n  {problem}" for problem in problems)
        raise SkillGraftError(
            f"vendored copies not as skill-graft.lock records them:{lines}\n"
            "move an edit into a patch, or delete the folder to vendor it again"
        )


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
    checked: bool = False,
) -> Generator[Resolution]:
    """The hull, every source at its ref but those `refs` names; after the block,
    the lock rendered and verified while the patched copies exist and, unless
    `write` is false, the copies staged; then the caller's writes run in order, the
    package's `.gitattributes` written if missing, the copies swapped into `skills`
    and the lock written. On any failure, the swap is undone and each file
    written restored, in reverse, to its bytes right before its write.

    First checks the copies in `skills` against the lock, unless `checked`.
    Adds the hull's warnings to `warnings` at once, so a later failure keeps them.
    """
    skills = skills or scope.skills
    lock_file = lock_file or scope.lock_file
    locked = lock.load(lock_file)
    if not checked:
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
        notice(str(error))


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
