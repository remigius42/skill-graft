"""Writes the entries into the package's `.apm/skills/`."""

import shutil
from pathlib import Path

from skill_graft import files, paths, rename
from skill_graft.errors import SkillGraftError
from skill_graft.hull import Hull


def vendor(hull: Hull, skills: Path | None = None) -> None:
    """Replaces `skills` (default: the package's `.apm/skills/`) with one copy per
    hull skill, swapped in when complete.

    Each copy is named by its deployed name and holds the rewritten bytes. The
    hull is resolved and checked before, so a failure writes nothing beyond
    undoing a run killed mid-swap.
    """
    skills = paths.skills() if skills is None else skills
    new = skills.with_name("skills.new")
    old = skills.with_name("skills.old")
    rewrites = rename.rewrites(hull)  # may fail: before anything is written
    _recover(skills, new, old)
    new.mkdir(parents=True)
    for skill, folder in hull.skills.items():
        written = rewrites.get(skill, {})  # by path relative to `folder`

        def copy(source: str, target: str) -> str:
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
    if skills.exists():
        skills.rename(old)
    new.rename(skills)
    if old.exists():
        shutil.rmtree(old)


def _recover(skills: Path, new: Path, old: Path) -> None:
    """Undoes a run killed mid-swap: `skills.old/` is then the previous build."""
    if old.exists() and not skills.exists():
        old.rename(skills)
    for stale in (new, old):
        if stale.exists():
            try:
                shutil.rmtree(stale)
            except OSError as error:
                raise SkillGraftError(f"cannot delete stale {stale}: {error}") from None
