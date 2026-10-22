"""Walks, checks and copies a skill as it is vendored, and writes files atomically."""

import os
import shutil
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path

from skill_graft.infra.errors import SkillGraftError


def skill_entries(folder: Path) -> list[Path]:
    """Every file, folder and link under `folder` that vendoring copies.

    Anything named `.git`, file or folder, is left out, as the copy leaves it out.
    Symlinked folders are listed, not entered.
    """
    entries = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(name for name in dirnames if name != ".git")
        entries += [Path(dirpath) / name for name in dirnames]
        entries += [
            Path(dirpath) / name for name in sorted(filenames) if name != ".git"
        ]
    return entries


def copy_skill(
    source: Path,
    target: Path,
    copy_function: Callable[[str, str], object] = shutil.copy2,
) -> None:
    """Copies a skill's folder as it is vendored: `.git` left out, links followed."""
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(".git"),
        copy_function=copy_function,
    )


def check_files(folder: Path) -> None:
    """A skill is its whole folder: a symlink may only lead to a file inside it.

    A link to a folder, even one inside, is refused: it can form a cycle. So is
    a FIFO, socket or device, which reading would block on or never finish.
    """
    root = folder.resolve()
    for link in skill_entries(folder):
        if not link.is_symlink():
            mode = link.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise SkillGraftError(f"{link} is not a regular file")
            continue
        target = Path(os.path.realpath(link))
        if not target.is_relative_to(root):
            raise SkillGraftError(f"{link} points outside the skill, to {target}")
        if not target.exists():
            raise SkillGraftError(f"{link} points to {target}, which is missing")
        if target.is_dir():
            raise SkillGraftError(f"{link} points to a folder; only file links work")
        if not target.is_file():
            raise SkillGraftError(f"{link} points to {target}: not a regular file")


def atomic_write(file: Path, data: bytes) -> None:
    """Replaces `file` with `data` in one step, never leaving it half written.

    Keeps the mode of the file it replaces; a new file gets the umask's.
    """
    with tempfile.NamedTemporaryFile(
        "wb", dir=file.parent, prefix=f".{file.name}.", delete=False
    ) as tmp:
        try:
            tmp.write(data)
            tmp.close()
            if file.exists():
                shutil.copymode(file, tmp.name)
            else:
                umask = os.umask(0)
                os.umask(umask)
                os.chmod(tmp.name, 0o666 & ~umask)
            os.replace(tmp.name, file)
        except BaseException:
            os.unlink(tmp.name)
            raise
