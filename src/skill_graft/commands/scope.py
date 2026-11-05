"""The scope a command acts on, built in one place."""

import os
from pathlib import Path

from skill_graft.infra import paths
from skill_graft.infra.errors import SkillGraftError, notice

# Commands that write: they name the package they act on before anything else.
WRITERS = ("resolve", "deploy", "update", "add", "remove", "rename", "bind", "unbind")
# And `vet`, whose first line the graft-vet skill reads: the package, for `[check]`.
NAMERS = (*WRITERS, "vet")


def of(command: str, project: bool) -> paths.Scope:
    """The scope `command` acts on: the home folder for `init`, the working folder
    for `init --project`, else the package `discover` finds. Only these read the
    working folder, so plain `init` works in a deleted one."""
    if command != "init":
        root = paths.discover(_working_folder())
    elif project:
        root = _working_folder()
    else:
        root = Path.home()
    current = paths.Scope(root)
    if command in NAMERS:  # init names it once its own checks pass
        notice(f"package: {current.package.absolute()}")
    return current


def _working_folder() -> Path:
    try:
        return Path.cwd()
    except FileNotFoundError:
        # The shell's PWD still names the deleted folder.
        folder = f" {os.environ['PWD']}" if os.environ.get("PWD") else ""
        raise SkillGraftError(f"the working folder{folder} no longer exists") from None
