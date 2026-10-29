"""What runs after a command: pruning the cache of what it has not used."""

import time

from skill_graft.infra import cache, paths


def prune() -> None:
    """Removes the exports, and leftovers, the cache has not used for 30 days."""
    cache.prune(paths.cache(), time.time())
