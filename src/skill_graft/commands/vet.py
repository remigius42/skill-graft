"""`vet`: each hull skill's flags, as deployed, writing nothing but `--into`'s
folder. Never a verdict."""

import shutil
from dataclasses import replace
from pathlib import Path

from skill_graft.commands import transaction
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, notice
from skill_graft.pipeline import compute, deployed, hull, rename
from skill_graft.pipeline import vet as patterns
from skill_graft.pipeline.config import SkillId
from skill_graft.pipeline.deployed import View


def vet(
    scope: paths.Scope,
    warnings: list[str],
    skills: list[str],
    into: Path | None = None,
) -> None:
    """Prints a line per flag of each skill vetted, then how many, on stderr.

    Without `skills`, every hull skill is vetted; with them, those skill IDs, and
    for each outside the hull every skill its `add` would bring in. Each is
    scanned as it would deploy, patches and renames applied; the lines name its
    files, never the text they hold. Writes nothing, the config included, but,
    with `into`, each vetted skill as scanned to `into/<alias>/<name>/`.
    """
    if into is not None:
        transaction.check_into(into)
    loaded = transaction.load(scope, warnings)
    if into is not None:
        transaction.check_into_sources(into, loaded)
    cache = Cache.default()
    given = [
        compute.known(scope, loaded, cache, "vet", text)
        for text in dict.fromkeys(skills)
    ]
    added = [skill for skill in given if skill not in loaded.entries]
    widened = replace(loaded, entries=[*loaded.entries, *added])
    lines = []
    views: dict[SkillId, View] = {}
    with compute.compute_hull(scope, widened, cache) as walked:
        warnings.extend(walked.warnings)
        # Edges do not depend on the entries: what the config's entries reach in
        # the widened hull is the hull without `skills`, in its order, as both
        # walks are breadth-first from the entries.
        before = [*loaded.entries, *hull.reach(walked, loaded.entries)]
        reached = set(before)
        new = [s for s in walked.skills if s not in reached]
        order = before + new
        vetted = {*given, *new} if given else reached
        rewrites = rename.rewrites(walked)
        count = 0
        for skill in order:
            if skill not in vetted:
                continue
            count += 1
            view = deployed.deployed_files(
                walked.skills[skill], rewrites.get(skill, {})
            )
            lines += [_line(str(skill), flag) for flag in patterns.scan(view)]
            if into is not None:  # held only to write: a plain `vet` keeps none
                views[skill] = view
    made = [] if into is None else _write(into, views)
    try:
        print("".join(f"{line}\n" for line in lines), end="")
        notice(
            f"{len(lines)} flag{'s' * (len(lines) != 1)} in {count} "
            f"skill{'s' * (count != 1)}: a flag is not a fault, and no flag is not "
            "a pass; read each line flagged, and the rest"
        )
    except BaseException:  # an error leaves `into` as it was, empty
        _remove(made)
        raise


def _write(into: Path, views: dict[SkillId, View]) -> list[Path]:
    """Each skill's files in `views` to `into/<alias>/<name>/`, executable or not,
    and the alias folders it made; on a failure, removes those, and nothing else.

    Refuses a file another already wrote, as a case-insensitive file system makes
    of `SKILL.md` and `skill.md`: a reader would read other bytes than the scan.
    """
    made: list[Path] = []
    try:
        for skill, view in views.items():
            alias = into / skill.alias
            if not alias.exists():
                alias.mkdir()
                made.append(alias)
            for path, (data, executable) in view.items():
                file = alias / skill.name / path
                if file.exists():
                    raise SkillGraftError(
                        f"vet --into: {skill}: {path} would overwrite another of its"
                        " files, as on a case-insensitive file system"
                    )
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data)
                file.chmod(0o755 if executable else 0o644)
    except BaseException:
        _remove(made)
        raise
    return made


def _remove(folders: list[Path]) -> None:
    for folder in folders:
        shutil.rmtree(folder, ignore_errors=True)


def _line(skill: str, flag: patterns.Flag) -> str:
    """`flag`'s line: no text the skill holds but its file's name, as ASCII."""
    ids = ",".join(patterns.OWASP[flag.category])
    return (
        f"{skill} {_ascii(flag.file)}:{flag.line} {flag.category} {ids} {flag.pattern}"
    )


def _ascii(name: str) -> str:
    """`name` with each character outside printable ASCII, or a space, as `?`."""
    return "".join(c if "!" <= c <= "~" else "?" for c in name)
