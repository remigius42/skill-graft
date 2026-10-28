"""Vendors the hull into the package, writes the lock, and has APM deploy it."""

import contextlib
import os
import shutil
from pathlib import Path

from skill_graft.commands import explain, resolve
from skill_graft.infra import apm, paths
from skill_graft.infra.errors import SkillGraftError, notice
from skill_graft.pipeline import config, lock, vendor


def build(
    scope: paths.Scope, warnings: list[str], given: Path | None, no_install: bool
) -> None:
    """Vendors the hull and writes the lock, then runs APM; `given` (`--into`)
    mirrors the package's layout in another folder instead, and runs no APM."""
    if given is not None:
        notice(f"into: {given.absolute()}")
        _check_into(given)
    into = None if given is None else given.resolve()
    skills = scope.skills if into is None else into / ".apm" / "skills"
    lock_file = None if into is None else into / "skill-graft.lock"
    started = False
    try:
        loaded = resolve.load(warnings)
        if given is not None:
            _check_into_sources(given, loaded)
        with resolve.resolving(
            scope, loaded, warnings, lock_file=lock_file
        ) as resolution:
            resolved = resolution.hull
            started = True  # from here on `into` may hold our writes
            vendor.vendor(resolved, skills)
            # Hashes the vendored copies, so the lock holds what was vendored.
            resolution.hashes = {
                s: lock.folder_hash(skills / resolved.deployed[s])
                for s in resolved.skills
            }
    except BaseException:
        # After the work folder is gone, which a TMPDIR may put in `into`.
        if into is not None and started:
            _undo_into(into)
        raise
    if into is None:  # its hint, `resolve`, would rewrite the package's lock
        # Once nothing before APM can fail.
        explain.announce_suggestions(resolved)
        if not no_install:
            apm.install()


def _check_into(into: Path) -> None:
    """Refuses an `--into` folder `build` could not use without harm: anything but an
    existing, empty folder, or one in a package or in or around the cache."""
    if not into.exists():
        raise SkillGraftError(f"--into {into}: no such folder")
    if not into.is_dir():
        raise SkillGraftError(f"--into {into}: not a folder")
    if any(into.iterdir()):
        raise SkillGraftError(f"--into {into}: not empty")
    resolved = paths.folded(into.resolve())
    # As given too, but without `..`: a path only passing through a package is fine.
    given = paths.folded(Path(os.path.normpath(into.absolute())))
    if any(paths.in_package(p) for p in (given, resolved)):
        raise SkillGraftError(f"--into {into}: inside a package (.apm/skill-graft)")
    if paths.overlap(resolved, paths.folded(cache := paths.cache().resolve())):
        raise SkillGraftError(f"--into {into}: overlaps the cache {cache}")


def _check_into_sources(into: Path, loaded: config.Config) -> None:
    """Refuses an `--into` folder inside a path source, compared resolved."""
    folded = paths.folded(into.resolve())
    for alias, source in sorted(loaded.sources.items()):
        if isinstance(source, config.PathSource) and folded.is_relative_to(
            paths.folded(source.folder)
        ):
            raise SkillGraftError(f"--into {into}: inside source {alias!r}")


def _undo_into(into: Path) -> None:
    """Removes what a failed `build --into` wrote in `into`, and nothing else there.

    Never raises: the build's own error is the one to report.
    """
    folder = into / ".apm"
    for name in ("skills.new", "skills.old", "skills"):  # `.new` stays on Ctrl-C
        shutil.rmtree(folder / name, ignore_errors=True)
    with contextlib.suppress(OSError):
        (into / "skill-graft.lock").unlink(missing_ok=True)
    with contextlib.suppress(OSError):  # kept if another process wrote into it
        folder.rmdir()
