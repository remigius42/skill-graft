"""A skill's files as deployed, compared: the summary and the Deployed diff. No git."""

import os
import stat
from pathlib import Path

from skill_graft.infra import files

# Each file of a skill as deployed, by path relative to it: its bytes, executable bit.
View = dict[str, tuple[bytes, bool]]

# git's letter escapes in a quoted path; any other byte to quote is octal.
_LETTERS = {
    7: "a",
    8: "b",
    9: "t",
    10: "n",
    11: "v",
    12: "f",
    13: "r",
    34: '"',
    92: "\\",
}


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


def quote(path: str, prefix: str = "") -> str:
    """`prefix + path` as git's `core.quotePath` quotes it, a space quoted too, so
    it is printable ASCII and no two names print alike: `"a/x\\n"`, never `a/"x\\n"`."""
    data = os.fsencode(prefix + path)
    if all(0x20 < byte < 0x7F and byte not in _LETTERS for byte in data):
        return prefix + path
    return '"' + "".join(_escape(byte) for byte in data) + '"'


def _escape(byte: int) -> str:
    if byte in _LETTERS:
        return "\\" + _LETTERS[byte]
    if 0x20 <= byte < 0x7F:
        return chr(byte)
    return f"\\{byte:03o}"
