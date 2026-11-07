"""The review every command that writes the lock offers: the Hull diff it prints and
the Deployed diff file `--diff-file` writes."""

import os
import shlex
import stat
import tempfile
from collections.abc import Callable, Generator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_graft.commands import explain, transaction
from skill_graft.infra import files, paths, text
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import config, deployed, lock, rename
from skill_graft.pipeline.config import Config, GitSource, SkillId
from skill_graft.pipeline.hull import Hull, PatchError

# The Deployed diff's first line, the same in every file: one starting with it, or
# with the line 0.3.0 wrote, is one skill-graft wrote.
FIRST = (
    "# skill-graft Deployed diff: each Skill's text as deployed, Patches and Renames"
    " applied,\n"
)
FIRST_0_3 = (
    "# skill-graft Deployed diff: each Skill's text as `build` deploys it, Patches and"
    " Renames applied,\n"
)
_FIRSTS = (FIRST.encode(), FIRST_0_3.encode())
# The bytes `check_target` reads: enough for either first line.
_FIRST_LENGTH = max(map(len, _FIRSTS))


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
            skill = SkillId(*config.split_id(item["id"]))
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
    """Where to write `--diff-file`'s file: its folders resolved, its last part kept.

    Refuses a name no harness would leave alone, a place inside a package or a
    skill, and anything but a new file or a Deployed diff it wrote, which `clear`
    removes.
    """
    if not file.name.endswith(".diff"):
        raise SkillGraftError(
            f"--diff-file {file}: name a file ending in .diff, which no agent loads"
        )
    target = file.parent.resolve() / file.name
    # As given too, but without `..`: a harness walking a package or a skill
    # follows a link inside it, so one named `.apm` or in a skill's folder leads there.
    given = Path(os.path.normpath(file.absolute()))
    for folder in [*given.parents, *target.parents]:
        if paths.folded(folder).name == ".apm":
            raise SkillGraftError(
                f"--diff-file {file}: inside {folder}, a folder named .apm"
            )
        if (folder / "SKILL.md").exists():
            raise SkillGraftError(
                f"--diff-file {file}: inside {folder}, a skill's folder holding a "
                "SKILL.md"
            )
    if not target.parent.is_dir():  # before any fetch, not at the last write
        raise SkillGraftError(f"--diff-file {file}: no such folder {target.parent}")
    try:
        mode = target.lstat().st_mode
    except FileNotFoundError:
        return target
    if not stat.S_ISREG(mode):
        raise SkillGraftError(f"--diff-file {file}: not a regular file")
    with open(target, "rb") as written:
        start = (
            # Equivalent mutants: reading the whole file starts the same.
            written.read(_FIRST_LENGTH)  # pragma: no mutate
        )
        if not start.startswith(_FIRSTS):
            raise SkillGraftError(
                f"--diff-file {file}: not a Deployed diff skill-graft wrote; left as "
                "it is"
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
    # Each line with the next one's skill, the last with none.
    for (skill, line), after in zip(
        error.hidden, [*(s for s, _ in error.hidden[1:]), None]
    ):
        hidden.append((skill, line))
        if skill in gone and after != skill:  # its last line
            hidden.append((skill, fetch))
    return PatchError(error.failures, error.other, hints, hidden)


def print_diff(
    before: Before | str, hull: Hull, new: dict[SkillId, str]
) -> dict[SkillId, tuple[deployed.View, deployed.View]]:
    """`+`, `-` or `~` per skill added, removed or changed, by skill ID; under each
    `+` and `~`, its files that differ. Those skills, as deployed then and now."""
    if isinstance(before, str):
        print(f"no previous hull to compare ({text.show(before)})")
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
            f"# no previous hull to compare ({text.show(before)}): "
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
    # Quoted: the lock's, which nothing checks; none recorded, none shown.
    refs = f"{deployed.quote(old)} -> {new}" if old is not None and old != new else new
    folders = [deployed.quote(before.upstream(skill))] if before is not None else []
    folders.append(
        deployed.quote(
            hull.upstream[skill].relative_to(hull.roots[skill.alias]).as_posix()
        )
    )
    shown = " -> ".join(folders) if len(set(folders)) > 1 else folders[-1]
    return f"# source {skill.alias}: {refs}; upstream folder {shown}\n"


def dry_cache(stack: ExitStack) -> Cache:
    """A dry run's cache: a temporary folder, its `root`, that `stack` removes,
    layered over the real cache."""
    root = stack.enter_context(tempfile.TemporaryDirectory(prefix="skill-graft-"))
    return Cache(Path(root), Cache.default())


class Run:
    """One run of a command that writes the lock: its cache, a dry run's
    `dry_cache`; `--diff-file`'s file, refused if bad before
    anything else; and the lines a dry run prints last."""

    # The Deployed diff, built before any write: set by `stage`, read by `finish`.
    text: str

    def __init__(
        self,
        stack: ExitStack,
        command: list[str],
        dry_run: bool,
        diff: Path | None,
        written: str,
    ) -> None:
        self.target = None if diff is None else check_target(diff)
        self.stack = stack
        self.command = " ".join(shlex.quote(arg) for arg in command)
        self.dry_run = dry_run
        self.written = written
        self.cache = dry_cache(stack) if dry_run else Cache.default()
        self.shown: dict[SkillId, tuple[deployed.View, deployed.View]] = {}
        self.changed = False  # whether the Hull diff marks a skill `+` or `~`
        # Whether the writes went through: a later failure keeps the Deployed diff.
        self.committed = False

    def proceed(self) -> None:
        """Past the command's no-op check: removes an earlier Deployed diff, so a
        failing run leaves none; registers a dry run's last lines, the hint first,
        printed even on a failure."""
        if self.target is not None:
            clear(self.target)
        if not self.dry_run:
            return
        self.stack.callback(print, f"dry run: {self.written} not written")
        self.stack.callback(self._hint)

    def _hint(self) -> None:
        if self.changed and self.target is None:
            print(f"review: skill-graft {self.command} --dry-run --diff-file <file>")


@contextmanager
def running(
    command: list[str], dry_run: bool, diff: Path | None, written: str
) -> Generator[Run]:
    """The run of `command`, whose dry run writes none of `written`; on any
    failure, no Deployed diff left; a failing patch named, in a dry run, with how
    to keep what it fetched."""
    with ExitStack() as stack:
        run = Run(stack, command, dry_run, diff, written)
        try:
            try:
                yield run
            except PatchError as error:
                if not run.dry_run:
                    raise
                keep = (
                    f"run `skill-graft {run.command}` without `--dry-run` "
                    "to keep what it fetched"
                )
                raise fetch_hint(error, run.cache.root, keep) from None
        except BaseException:
            if run.target is not None and not run.committed:
                clear(run.target)
            raise


def stage(
    run: Run,
    scope: paths.Scope,
    loaded: Config,
    resolution: transaction.Resolution,
    head: str,
) -> None:
    """Inside `resolving`, while the patched copies exist: with `--dry-run` or
    `--diff-file`, prints the Hull diff of the copies against the hull and builds the
    Deployed diff under `head`; in a real run, its write comes first of the
    caller's, so a later failure undoes it."""
    target = run.target
    if not run.dry_run and target is None:
        return
    hull = resolution.hull
    hashes = resolution.hashes = lock.skill_hashes(hull)
    before = vendored(scope.skills, lock.load(scope.lock_file))
    run.shown = print_diff(before, hull, hashes)
    if target is None:
        return
    run.text = deployed_diff(head, loaded, {}, before, hull, hashes, run.shown, [])
    if not run.dry_run:
        resolution.writes.append(
            (target, lambda: files.atomic_write(target, run.text.encode()))
        )


def finish(run: Run) -> None:
    """After the writes: a dry run's Deployed diff, written last."""
    run.changed = bool(run.shown)
    if run.dry_run and run.target is not None:
        files.atomic_write(run.target, run.text.encode())
