"""Writes the entries into the package's `.apm/skills/`: staged in `skills.new/`,
swapped in, the previous copies kept in `skills.old/` until the caller clears them."""

import shutil
from collections.abc import Callable
from pathlib import Path

from skill_graft.infra import files
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import rename
from skill_graft.pipeline.hull import Hull


def _new(skills: Path) -> Path:
    return skills.with_name("skills.new")


def _old(skills: Path) -> Path:
    return skills.with_name("skills.old")


def stage(hull: Hull, skills: Path) -> None:
    """Writes `skills.new` beside `skills`, the package's `.apm/skills/` or another,
    with one copy per hull skill.

    Each copy is named by its deployed name and holds the rewritten bytes. The
    hull is resolved and checked before, so a failure leaves no `skills.new`.
    """
    new = _new(skills)
    rewrites = rename.rewrites(hull)  # may fail: before anything is written
    new.mkdir(parents=True)
    for skill, folder in hull.skills.items():
        written = rewrites.get(skill, {})  # by path relative to `folder`

        def copy(
            source: str,
            target: str,
            folder: Path = folder,
            written: dict[Path, bytes] = written,
        ) -> str:
            """Copies a file, or writes its rewritten bytes; then its mode and times.

            Written as the copy is made, before `copytree` sets the folders' modes,
            so a read-only upstream file or folder never blocks a rewrite.
            """
            if (data := written.get(Path(source).relative_to(folder))) is None:
                return str(shutil.copy2(source, target))
            Path(target).write_bytes(data)
            shutil.copystat(source, target)
            return target

        try:
            files.copy_skill(folder, new / hull.deployed[skill], copy)
        except OSError as error:
            # The copy error is the one to report; the next run clears what is left.
            shutil.rmtree(new, ignore_errors=True)
            raise SkillGraftError(f"copying {folder} failed: {error}") from None


def swap(skills: Path) -> None:
    """Moves `skills` aside to `skills.old`, if there is one, and `skills.new` in."""
    if skills.exists():
        skills.rename(_old(skills))
    _new(skills).rename(skills)


def swap_back(skills: Path) -> None:
    """Undoes `swap`, however far it got: `skills` as before it, no `skills.new`."""
    new, old = _new(skills), _old(skills)
    if new.exists():  # not swapped in: `skills` is the previous, or moved aside
        shutil.rmtree(new)
    elif skills.exists():
        shutil.rmtree(skills)
    if old.exists():
        old.rename(skills)


def _trash(skills: Path) -> Path:
    return skills.with_name("skills.trash")


def clear_old(skills: Path) -> None:
    """Deletes the previous copies `swap` kept, renamed to `skills.trash` first: a
    delete that fails or is killed never leaves them for `recover` to take back
    over an edit made since."""
    old, trash = _old(skills), _trash(skills)
    if old.exists():
        try:
            old.rename(trash)
        except OSError as error:
            raise SkillGraftError(f"cannot delete stale {old}: {error}") from None
    _delete(trash)


def pending(skills: Path, keep_old: Callable[[Path], bool]) -> Path:
    """The folder `recover` leaves as `skills`, touching nothing: a lone
    `skills.old`; with both, `skills.old` if `keep_old` says so, else `skills`."""
    old = _old(skills)
    if old.exists() and (not skills.exists() or keep_old(old)):
        return old
    return skills


def recover(skills: Path, keep_old: Callable[[Path], bool]) -> None:
    """Undoes a run killed mid-swap, keeping as `skills` what `pending` names, and
    deletes `skills.new` and `skills.trash`."""
    new, old = _new(skills), _old(skills)
    if pending(skills, keep_old) == old:
        _delete(skills)
        old.rename(skills)
    for stale in (new, old, _trash(skills)):
        _delete(stale)


def _delete(stale: Path) -> None:
    if stale.exists():
        try:
            shutil.rmtree(stale)
        except OSError as error:
            raise SkillGraftError(f"cannot delete stale {stale}: {error}") from None
