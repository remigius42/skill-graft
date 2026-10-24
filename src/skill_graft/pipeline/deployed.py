"""A skill's files as deployed, compared: the summary and the Deployed diff. No git."""

import os
import stat
from pathlib import Path

from skill_graft.infra import files

# Each file of a skill as deployed, by path relative to it: its bytes, executable bit.
View = dict[str, tuple[bytes, bool]]


def deployed_files(folder: Path, overrides: dict[Path, bytes]) -> View:
    """Each file of `folder` as vendored, sorted by its path's bytes.

    Symlinks are followed, as the copy does; `.git` is skipped, as it is not copied.
    A file in `overrides`, by path relative to `folder`, has its bytes.
    """
    view = {}
    for file in sorted(
        (f for f in files.skill_entries(folder) if not f.is_dir()),
        key=lambda f: os.fsencode(f.relative_to(folder).as_posix()),
    ):
        relative = file.relative_to(folder)
        content = overrides.get(relative)
        if content is None:
            content = file.read_bytes()
        view[relative.as_posix()] = (content, bool(file.stat().st_mode & stat.S_IXUSR))
    return view
