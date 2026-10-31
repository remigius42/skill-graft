"""The `resolve` command: resolves the hull, vendors it and writes the lock."""

from pathlib import Path

from skill_graft.commands import explain, review, transaction
from skill_graft.infra import paths

# What its dry run does not write.
WRITTEN = "skill-graft.lock and .apm/skills/"
# Its header: what `resolve --diff` compares.
HEADER = review.header(
    "the Vendored copies against what `skill-graft.toml` as it stands would vendor"
)


def resolve(
    scope: paths.Scope,
    warnings: list[str],
    dry_run: bool = False,
    diff: Path | None = None,
) -> None:
    """Resolves the hull, vendors it, writes the lock, and prints the tree and
    suggestions. A dry run writes nothing but `diff`'s file, if given."""
    with review.running(["resolve"], dry_run, diff, WRITTEN) as run:
        loaded = transaction.load(scope, warnings)
        run.proceed()  # no no-op to check
        with transaction.resolving(
            scope, loaded, warnings, run.cache, write=not dry_run
        ) as resolution:
            review.stage(run, scope, loaded, resolution, HEADER)
        run.committed = True
        explain.show(resolution.hull)
        review.finish(run)
