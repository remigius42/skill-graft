"""Walks a skill as it is vendored, and writes files atomically."""

import os
import shutil
import tempfile
from pathlib import Path


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
