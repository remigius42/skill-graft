"""`vet`: each hull skill's flags, as deployed, writing nothing. Never a verdict."""

import os

from skill_graft.commands import transaction
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import notice
from skill_graft.pipeline import compute, deployed, rename
from skill_graft.pipeline import vet as patterns


def vet(scope: paths.Scope, warnings: list[str]) -> None:
    """Prints a line per flag of each hull skill, then how many, on stderr.

    Each skill is scanned as it would deploy, patches and renames applied; the
    lines name its files, never the text they hold.
    """
    loaded = transaction.load(scope, warnings)
    lines = []
    with compute.compute_hull(scope, loaded, Cache.default()) as hull:
        warnings.extend(hull.warnings)
        rewrites = rename.rewrites(hull)
        for skill, folder in hull.skills.items():  # in hull order
            view = deployed.deployed_files(folder, rewrites.get(skill, {}))
            flags = sorted(
                set(patterns.scan(view)),
                key=lambda f: (os.fsencode(f.file), f.line, f.pattern),
            )
            lines += [
                " ".join(
                    [
                        str(skill),
                        f"{_ascii(flag.file)}:{flag.line}",
                        flag.category,
                        ",".join(patterns.OWASP[flag.category]),
                        flag.pattern,
                    ]
                )
                for flag in flags
            ]
        count = len(hull.skills)
    print("".join(f"{line}\n" for line in lines), end="")
    notice(
        f"{len(lines)} flag{'s' * (len(lines) != 1)} in {count} "
        f"skill{'s' * (count != 1)}: a flag is not a fault, and no flag is not a "
        "pass; read each line flagged, and the rest"
    )


def _ascii(name: str) -> str:
    """`name` with each character outside printable ASCII, or a space, as `?`."""
    return "".join(c if "!" <= c <= "~" else "?" for c in name)
