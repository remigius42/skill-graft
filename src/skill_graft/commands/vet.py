"""`vet`: each hull skill's flags, as deployed, writing nothing. Never a verdict."""

from dataclasses import replace

from skill_graft.commands import transaction
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import notice
from skill_graft.pipeline import compute, deployed, hull, rename
from skill_graft.pipeline import vet as patterns


def vet(scope: paths.Scope, warnings: list[str], skills: list[str]) -> None:
    """Prints a line per flag of each skill vetted, then how many, on stderr.

    Without `skills`, every hull skill is vetted; with them, those skill IDs, and
    for each outside the hull every skill its `add` would bring in. Each is
    scanned as it would deploy, patches and renames applied; the lines name its
    files, never the text they hold. Writes nothing, the config included.
    """
    loaded = transaction.load(scope, warnings)
    cache = Cache.default()
    given = [
        compute.known(scope, loaded, cache, "vet", text)
        for text in dict.fromkeys(skills)
    ]
    added = [skill for skill in given if skill not in loaded.entries]
    widened = replace(loaded, entries=[*loaded.entries, *added])
    lines = []
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
    print("".join(f"{line}\n" for line in lines), end="")
    notice(
        f"{len(lines)} flag{'s' * (len(lines) != 1)} in {count} "
        f"skill{'s' * (count != 1)}: a flag is not a fault, and no flag is not a "
        "pass; read each line flagged, and the rest"
    )


def _line(skill: str, flag: patterns.Flag) -> str:
    """`flag`'s line: no text the skill holds but its file's name, as ASCII."""
    ids = ",".join(patterns.OWASP[flag.category])
    return (
        f"{skill} {_ascii(flag.file)}:{flag.line} {flag.category} {ids} {flag.pattern}"
    )


def _ascii(name: str) -> str:
    """`name` with each character outside printable ASCII, or a space, as `?`."""
    return "".join(c if "!" <= c <= "~" else "?" for c in name)
