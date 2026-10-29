"""Applies a skill's patches to a copy of its folder, before its references are read."""

import re
import shutil
import stat
from pathlib import Path

from skill_graft.infra import files, git
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import discovery
from skill_graft.pipeline.config import Config, PatchFile, SkillId

# A hunk's header in a `.rej` file, without the section heading after it.
HUNK = re.compile(rb"^(@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@)", re.MULTILINE)
# The header of a file in a git-format patch, as `git diff` writes it.
GIT_FORMAT = re.compile(rb"^diff --git ", re.MULTILINE)


class PatchFailed(SkillGraftError):
    """A skill's patches did not apply; `lines` says what failed, one per line."""

    def __init__(self, lines: list[str]) -> None:
        super().__init__("\n".join(lines))
        self.lines = lines


def unused(config: Config, skills: dict[SkillId, Path]) -> list[str]:
    """A warning per `[patches]` key naming no hull skill."""
    return [
        f'[patches] "{key}" patches no skill in the hull'
        for key in config.patches
        if key not in skills
    ]


def apply(skill: SkillId, upstream: Path, patches: list[PatchFile], work: Path) -> Path:
    """A copy of `upstream` under `work`, `patches` applied in order; returns it.

    The copy keeps the upstream folder's name, so a skill without `name:` keeps its
    name. Raises `PatchFailed` at the first patch that does not apply, or keeps
    neither `SKILL.md` nor the name; the copy's files are checked after the last.
    """
    copy = work / skill.alias / skill.name / upstream.name
    try:
        files.copy_skill(upstream, copy)
        for path in [copy, *files.skill_entries(copy)]:  # git rewrites read-only ones
            path.chmod(path.stat().st_mode | stat.S_IWUSR)
    except shutil.Error as error:  # one (source, copy, reason) per file it missed
        reasons = "; ".join(f"{source}: {why}" for source, _, why in error.args[0])
        raise SkillGraftError(f"cannot copy {upstream}: {reasons}") from None
    except OSError as error:
        raise SkillGraftError(f"cannot copy {upstream}: {error.strerror}") from None
    # An empty stand-in for the user's home, so git reads no config. No alias
    # starts with a dot, so no copy ever lands in it.
    home = work / ".home"
    home.mkdir(exist_ok=True)
    name = discovery.read_name(upstream)
    for i, patch in enumerate(patches):
        before = _rejects(copy)
        # A git-format patch says itself what it deletes; a plain one cannot.
        filled = [] if GIT_FORMAT.search(patch.data) else _filled(copy)
        ok, stderr = git.apply(copy, patch.data, home)
        if ok:
            _delete_emptied(copy, filled)
        failures = [] if ok else _failures(patch.path, copy, before, stderr)
        if not failures:
            failures = _check_name(patch.path, copy, name)
        if failures:
            raise PatchFailed(
                failures + [f"{later.path}: not tried" for later in patches[i + 1 :]]
            )
    try:  # a series may pass through states that fail, such as a link made first
        files.check_files(copy)
    except SkillGraftError as error:
        paths = ", ".join(patch.path for patch in patches)
        raise PatchFailed([f"{paths}: {_relative(error, copy)}"]) from None
    return copy


def _size(path: Path) -> int | None:
    """The size of `path` if it is a regular file, links not followed; else None."""
    try:
        mode = path.lstat()
    except (FileNotFoundError, NotADirectoryError):  # gone, or its folder is a file
        return None
    return mode.st_size if stat.S_ISREG(mode.st_mode) else None


def _filled(folder: Path) -> list[Path]:
    """Each regular file in `folder` that is not empty."""
    return [entry for entry in files.skill_entries(folder) if _size(entry)]


def _delete_emptied(copy: Path, filled: list[Path]) -> None:
    """Deletes each of `filled` a patch left empty, and each folder above it that
    leaves empty, up to `copy`, as git's own deletion does: `diff -N` writes a
    deleted file as one emptied, and git deletes it only for GNU diff's epoch
    timestamp, which the BSD diff of macOS does not write."""
    for file in filled:
        if _size(file) != 0:
            continue
        file.unlink()
        folder = file.parent
        while folder != copy and not any(folder.iterdir()):
            folder.rmdir()
            folder = folder.parent


def _check_name(path: str, copy: Path, name: str) -> list[str]:
    """What is wrong with the patched copy: the skill must stay the same skill."""
    if (copy / "SKILL.md").is_symlink():  # never followed: it may lead anywhere
        return [f"{path}: makes SKILL.md a link"]
    if not (copy / "SKILL.md").is_file():
        return [
            f"{path}: deletes SKILL.md: a skill needs one; give it a new name with "
            "[rename], never by deleting it"
        ]
    try:
        patched = discovery.read_name(copy)
    except SkillGraftError as error:
        return [f"{path}: {_relative(error, copy)}"]
    if patched != name:
        return [
            f"{path}: changes the skill's name to {patched!r}: "
            f"give it a new deployed name with [rename] instead"
        ]
    return []


def _relative(error: SkillGraftError, copy: Path) -> str:
    """The error's message, paths in the copy given relative to the skill.

    Resolved paths too, which a link's target is named by.
    """
    message = str(error)
    for prefix in {f"{copy}/", f"{copy.resolve()}/"}:
        message = message.replace(prefix, "")
    return message


def _rejects(folder: Path) -> dict[Path, bytes]:
    """Each `.rej` file in `folder` and its bytes.

    A link is never read: one a patch made is checked only after the last patch,
    and git writes no `.rej` through a link.
    """
    return {
        rej: rej.read_bytes()
        for rej in folder.rglob("*.rej")
        if not rej.is_symlink() and rej.is_file()
    }


def _failures(
    path: str, copy: Path, before: dict[Path, bytes], stderr: str
) -> list[str]:
    """One line per hunk a `.rej` git wrote names, else git's message."""
    lines = []
    for rej, data in sorted(_rejects(copy).items()):
        if before.get(rej) == data:
            continue  # shipped upstream, not written by git
        target = rej.relative_to(copy).with_suffix("").as_posix()
        lines += [
            f"{path}: {target}: hunk {header.decode()} does not apply"
            for header in HUNK.findall(data)
        ]
    return lines or [f"{path}: git apply refused it: {'; '.join(stderr.splitlines())}"]
