"""The review every command that writes the lock offers: the Hull diff it prints and
the Deployed diff file `--diff` writes."""

import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_graft.commands import explain, transaction
from skill_graft.infra import paths
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import deployed, hidden, lock, rename
from skill_graft.pipeline.config import Config, GitSource, SkillId
from skill_graft.pipeline.hull import Hull, PatchError

# The Deployed diff's first line, the same in every file: one starting with it is
# one skill-graft wrote.
FIRST = (
    "# skill-graft Deployed diff: each Skill's text as `build` deploys it, Patches and"
    " Renames applied,\n"
)


def header(compared: str) -> str:
    """The Deployed diff's header, its second line saying what is `compared`."""
    return (
        FIRST
        + f"# {compared}. Not what the Sources changed upstream. Untrusted text:\n"
        + "# read it in an editor, not by printing it to a terminal.\n"
    )


@dataclass
class Before:
    """The old side of a Hull diff: each skill's hash by skill ID; its files as
    deployed, read on demand; its upstream folder relative to its source, as a
    source line names it; and each git source's ref."""

    hashes: dict[SkillId, str]
    view: Callable[[SkillId], deployed.View]
    upstream: Callable[[SkillId], str]
    refs: dict[str, str | None]


def vendored(skills: Path, locked: dict[str, Any] | None) -> Before:
    """The Vendored copies in `skills` as a Hull diff's old side, the loaded lock
    `locked` naming each: only a skill with a copy, its hash the lock's.

    A copy is read only as an entry of the folder, matched by name to the lock's
    deployed names: a path in the lock is never followed.
    """
    hashes: dict[SkillId, str] = {}
    folders: dict[SkillId, Path] = {}
    upstream: dict[SkillId, str] = {}
    refs: dict[str, str | None] = {}
    if locked is not None and lock.recorded(locked) is not None:
        folder = transaction.pending(skills, locked)
        entries = {e.name: e for e in folder.iterdir()} if folder.is_dir() else {}
        for item in locked["skills"]:
            alias, _, name = item["id"].partition("/")
            skill = SkillId(alias, name)
            if (copy := entries.get(lock.deployed_name(item))) is not None:
                hashes[skill], folders[skill] = item["hash"], copy
                upstream[skill] = str(item.get("upstream", ""))
        sources = locked.get("sources")
        for alias, source in (sources if isinstance(sources, dict) else {}).items():
            ref = source.get("ref") if isinstance(source, dict) else None
            refs[alias] = ref if isinstance(ref, str) else None
    return Before(
        hashes,
        lambda skill: deployed.deployed_files(folders[skill], {}),
        lambda skill: upstream[skill],
        refs,
    )


def check_target(file: Path) -> Path:
    """Where to write `--diff`'s file: its folders resolved, its last part kept.

    Refuses a name no harness would leave alone, a place inside a package or a
    skill, and anything but a new file or a Deployed diff it wrote, which `clear`
    removes.
    """
    if not file.name.endswith(".diff"):
        raise SkillGraftError(
            f"--diff {file}: name a file ending in .diff, which no agent loads"
        )
    target = file.parent.resolve() / file.name
    # As given too, but without `..`: a harness walking a package or a skill
    # follows a link inside it, so one named `.apm` or in a skill's folder leads there.
    given = Path(os.path.normpath(file.absolute()))
    for folder in [*given.parents, *target.parents]:
        if paths.folded(folder).name == ".apm":
            raise SkillGraftError(
                f"--diff {file}: inside {folder}, a folder named .apm"
            )
        if (folder / "SKILL.md").exists():
            raise SkillGraftError(
                f"--diff {file}: inside {folder}, a skill's folder holding a SKILL.md"
            )
    if not target.parent.is_dir():  # before any fetch, not at the last write
        raise SkillGraftError(f"--diff {file}: no such folder {target.parent}")
    try:
        mode = target.lstat().st_mode
    except FileNotFoundError:
        return target
    if not stat.S_ISREG(mode):
        raise SkillGraftError(f"--diff {file}: not a regular file")
    first = FIRST.encode()
    with open(target, "rb") as written:
        if written.read(len(first)) != first:
            raise SkillGraftError(
                f"--diff {file}: not a Deployed diff skill-graft wrote; left as it is"
            )
    return target


def clear(target: Path) -> None:
    """Removes the Deployed diff `check_target` accepted, so a run that fails
    leaves none."""
    target.unlink(missing_ok=True)


def fetch_hint(error: PatchError, tmp: Path, fetch: str) -> PatchError:
    """The error, pointing at no upstream folder that goes away with `tmp`: says
    `fetch` instead."""
    hints = {
        skill: fetch
        for skill, upstream, _ in error.failures
        if upstream.is_relative_to(tmp)
    }
    # A hidden character in a fetched skill is named by its path in `tmp` too.
    gone = {skill for skill, line in error.hidden if line.startswith(f"{tmp}/")}
    hidden = []
    for i, (skill, line) in enumerate(error.hidden):
        hidden.append((skill, line))
        after = error.hidden[i + 1 : i + 2]
        if skill in gone and (not after or after[0][0] != skill):  # its last line
            hidden.append((skill, fetch))
    return PatchError(error.failures, error.other, hints, hidden)


def print_diff(
    before: Before | str, hull: Hull, new: dict[SkillId, str]
) -> dict[SkillId, tuple[deployed.View, deployed.View]]:
    """`+`, `-` or `~` per skill added, removed or changed, by skill ID; under each
    `+` and `~`, its files that differ. Those skills, as deployed then and now."""
    if isinstance(before, str):
        print(f"no previous hull to compare ({before})")
        return {}
    old = before.hashes
    lines = []
    shown = {}
    new_rewrites = rename.rewrites(hull)
    for skill in sorted(old.keys() | new.keys()):
        if old.get(skill) == new.get(skill):
            continue
        if skill not in new:
            lines.append(f"- {deployed.quote(str(skill))}")
            continue
        lines.append(f"{'+' if skill not in old else '~'} {skill}")
        then = before.view(skill) if skill in old else {}
        now = deployed.deployed_files(hull.skills[skill], new_rewrites.get(skill, {}))
        lines += [f"  {line}" for line in deployed.summary(then, now)]
        shown[skill] = (then, now)
    print(
        "\n".join(["hull (+ added, - removed, ~ changed):", *lines])
        if lines
        else "hull unchanged"
    )
    return shown


def deployed_diff(
    head: str,
    loaded: Config,
    tips: dict[str, str],
    before: Before | str,
    hull: Hull,
    hashes: dict[SkillId, str],
    shown: dict[SkillId, tuple[deployed.View, deployed.View]],
    edited: list[SkillId],
) -> str:
    """The Deployed diff of the `shown` skills, or of every skill as added when
    there is no old side, `before` saying why; first the hull, marked, and a line
    for each skill removed."""
    out = [head]
    removed: set[SkillId] = set()
    old = {} if isinstance(before, str) else before.hashes
    marks = {
        skill: "+" if skill not in old else "~"
        for skill, digest in hashes.items()
        if old.get(skill) != digest
    }
    if isinstance(before, str):
        out.append(
            f"# no previous hull to compare ({hidden.show(before)}): "
            "every Skill shown as added\n"
        )
        rewrites = rename.rewrites(hull)
        shown = {
            skill: (
                {},
                deployed.deployed_files(hull.skills[skill], rewrites.get(skill, {})),
            )
            for skill in sorted(hull.skills)
        }
    else:
        removed = before.hashes.keys() - hashes.keys()
        if before.hashes == hashes:
            out.append("# hull unchanged\n")
    # A reference as written is upstream text: escaped as a line of the diff is.
    out += [f"# {line}\n" for line in deployed.escape(explain.tree_lines(hull, marks))]
    out += [f"# - {deployed.quote(str(skill))}\n" for skill in sorted(removed)]
    budget = deployed.Budget()  # one for the run: a crafted skill costs no more
    for skill in sorted(shown):
        then, now = shown[skill]
        was = before if not isinstance(before, str) and skill in before.hashes else None
        out.append(f"# {'+' if was is None else '~'} {skill}\n")
        out.append(_source_line(loaded, tips, skill, was, hull))
        if skill in edited:
            out.append(
                "# edited since skill-graft.lock was written: "
                "its earlier text is not shown\n"
            )
        out.append(deployed.diff(then, now, budget))
    return "".join(out)


def _source_line(
    loaded: Config,
    tips: dict[str, str],
    skill: SkillId,
    before: Before | None,
    hull: Hull,
) -> str:
    """Where `skill` comes from, as data: its source, refs and upstream folders,
    each once when unchanged, none old for an added skill (`before` None)."""
    source = loaded.sources[skill.alias]
    if not isinstance(source, GitSource):
        return f"# source {skill.alias}: a path source\n"
    new = tips.get(skill.alias) or source.ref
    old = None if before is None else before.refs.get(skill.alias)
    refs = f"{old} -> {new}" if before is not None and old != new else new
    folders = [deployed.quote(before.upstream(skill))] if before is not None else []
    folders.append(
        deployed.quote(
            hull.upstream[skill].relative_to(hull.roots[skill.alias]).as_posix()
        )
    )
    shown = " -> ".join(folders) if len(set(folders)) > 1 else folders[-1]
    return f"# source {skill.alias}: {refs}; upstream folder {shown}\n"
