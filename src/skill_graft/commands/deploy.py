"""Vendors the hull into the package, writes the lock, and has APM deploy it."""

import contextlib
import shutil
import tomllib
from pathlib import Path

from skill_graft.commands import explain, transaction
from skill_graft.infra import apm, paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError, notice
from skill_graft.pipeline import config, lock


def deploy(
    scope: paths.Scope, warnings: list[str], given: Path | None, no_apm_install: bool
) -> None:
    """Vendors the hull and writes the lock, then runs APM; `given` (`--into`)
    mirrors the package's layout in another folder instead, and runs no APM."""
    cache = Cache.default()
    if given is not None:
        notice(f"into: {given.absolute()}")
        transaction.check_into(given)
    into = None if given is None else given.resolve()
    skills = scope.skills if into is None else into / ".apm" / "skills"
    lock_file = None if into is None else into / "skill-graft.lock"
    # Annotated: mypy then refuses mutmut's `None`, which would act as `False`.
    started: bool = False
    changed: list[str] = []
    try:
        loaded = transaction.load(scope, warnings)
        if given is None:  # before any source is read
            transaction.check_reference_prefix(
                scope, loaded, apm_install=not no_apm_install
            )
        else:
            transaction.check_into_sources(given, loaded)
        recorded = lock.load(scope.lock_file)  # the package's, for `--into` too
        path_aliases = config.path_aliases(loaded)

        def verify(text: str) -> None:
            """Refuses a hull other than the one the package's lock records."""
            found, refusal = lock.drift(tomllib.loads(text), recorded, path_aliases)
            if refusal is not None:
                raise SkillGraftError(
                    f"{refusal}; run `skill-graft resolve` to accept it, then deploy"
                )
            changed.extend(found)

        with transaction.resolving(
            scope,
            loaded,
            warnings,
            cache,
            lock_file=lock_file,
            skills=skills,
        ) as resolution:
            resolved = resolution.hull
            resolution.verify = verify
            started = True  # from here on `into` may hold our writes
    except BaseException:
        # After the work folder is gone, which a TMPDIR may put in `into`.
        if into is not None and started:
            _undo_into(into)
        raise
    if into is None:  # its hint, `resolve`, would rewrite the package's lock
        # Once the lock is written: never a change rolled back. Not `--into`'s,
        # which deploys nothing and leaves the package's lock as it is.
        for skill in changed:
            notice(
                f"{skill} changed in its path source since skill-graft.lock:"
                " deployed as is"
            )
        # Once nothing before APM can fail.
        explain.announce_suggestions(resolved)
        if not no_apm_install:
            apm.install(scope)


def _undo_into(into: Path) -> None:
    """Removes what a failed `deploy --into` wrote in `into`, and nothing else there.

    Never raises: the deploy's own error is the one to report.
    """
    folder = into / ".apm"
    for name in (
        "skills.new",
        "skills.old",
        "skills.trash",
        "skills",
    ):  # `.new` stays on Ctrl-C
        shutil.rmtree(folder / name, ignore_errors=True)
    with contextlib.suppress(OSError):
        (into / "skill-graft.lock").unlink()
    with contextlib.suppress(OSError):  # kept if another process wrote into it
        folder.rmdir()
