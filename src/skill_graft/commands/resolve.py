"""The `resolve` command: resolves the hull and writes the lock."""

from skill_graft.commands import explain, transaction
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache


def resolve(scope: paths.Scope, warnings: list[str]) -> None:
    """Resolves the hull, writes the lock, and prints the tree and suggestions."""
    cache = Cache.default()
    with transaction.resolving(
        scope, transaction.load(scope, warnings), warnings, cache
    ) as resolution:
        pass
    explain.show(resolution.hull)
