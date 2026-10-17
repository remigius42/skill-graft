"""Applies a skill's patches to a copy of its folder, before its references are read."""

import re
import stat
from pathlib import Path

from skill_graft import discovery, files, git
from skill_graft.config import Config, PatchFile, SkillId
from skill_graft.errors import SkillGraftError

# A hunk's header in a `.rej` file, without the section heading after it.
HUNK = re.compile(rb"^(@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@)", re.MULTILINE)


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


class PatchError(SkillGraftError):
    """The patches of one or more skills did not apply; then perhaps another error.

    `failures` holds each failing skill, its upstream folder and what failed.
    """

    def __init__(
        self, failures: list[tuple[SkillId, Path, list[str]]], other: str = ""
    ) -> None:
        lines = ["patches do not apply:"]
        for skill, upstream, failed in failures:
            lines += [f"  {skill}: {line}" for line in failed]
            lines.append(f"  {skill}: redo it against {upstream}")
        super().__init__("\n".join(lines + ([other] if other else [])))
        self.failures = failures


def apply(skill: SkillId, upstream: Path, patches: list[PatchFile], work: Path) -> Path:
    """A copy of `upstream` under `work`, `patches` applied in order; returns it.

    The copy keeps the upstream folder's name, so a skill without `name:` keeps its
    name. Raises `PatchFailed` at the first patch that does not apply.
    """
    copy = work / skill.alias / skill.name / upstream.name
    files.copy_skill(upstream, copy)
    for path in [copy, *files.skill_entries(copy)]:  # git rewrites read-only ones
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    home = work / "home"  # an empty stand-in for the user's, so git reads no config
    home.mkdir(exist_ok=True)
    name = discovery.read_name(upstream)
    for i, patch in enumerate(patches):
        before = _rejects(copy)
        ok, stderr = git.apply(copy, patch.data, home)
        failures = [] if ok else _failures(patch.path, copy, before, stderr)
        if not failures:
            failures = _check(patch.path, copy, name)
        if failures:
            raise PatchFailed(
                failures + [f"{later.path}: not tried" for later in patches[i + 1 :]]
            )
    return copy


def _check(path: str, copy: Path, name: str) -> list[str]:
    """What is wrong with the patched copy: the skill must stay the same skill."""
    try:
        files.check_files(copy)
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
    """The error's message, paths in the copy given relative to the skill."""
    return str(error).replace(f"{copy}/", "")


def _rejects(folder: Path) -> dict[Path, bytes]:
    """Each `.rej` file in `folder` and its bytes."""
    return {rej: rej.read_bytes() for rej in folder.rglob("*.rej")}


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
