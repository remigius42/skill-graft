"""Writes the entries into the package's `.apm/skills/`."""

import shutil
from pathlib import Path

from skill_graft import paths
from skill_graft.config import SkillId
from skill_graft.errors import SkillGraftError


def vendor(resolved: dict[SkillId, Path]) -> None:
    """Replaces `.apm/skills/` with one copy per entry, swapped in when complete.

    The entries are resolved and checked before, so a failure writes nothing
    beyond undoing a run killed mid-swap.
    """
    skills = paths.skills()
    new = skills.with_name("skills.new")
    old = skills.with_name("skills.old")
    _recover(skills, new, old)
    new.mkdir(parents=True)
    for entry, folder in resolved.items():
        try:
            shutil.copytree(
                folder, new / entry.name, ignore=shutil.ignore_patterns(".git")
            )
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
