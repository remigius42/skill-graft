"""Writes files atomically."""

import os
import shutil
import tempfile
from pathlib import Path


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
