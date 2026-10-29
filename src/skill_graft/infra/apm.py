"""Runs APM. skill-graft never writes APM's `apm.yml`; APM does (ADR 0003)."""

import re
import shlex
import shutil
import subprocess
from pathlib import Path

from skill_graft.infra import paths
from skill_graft.infra.errors import SkillGraftError

# A YAML comment in `apm.yml`: `#` after whitespace, to the end of the line.
COMMENT = re.compile(r"\s+#.*$")

MISSING = "APM is not installed: no `apm` on PATH"


def _command(scope: paths.Scope) -> list[str]:
    """`apm install -g <absolute path>` in user scope; in project scope
    `apm install ./.apm/skill-graft`, run in the project root."""
    if not scope.user:
        return ["apm", "install", "./.apm/skill-graft"]
    return ["apm", "install", "-g", str(scope.package.absolute())]


def command_line(scope: paths.Scope) -> str:
    """The scope's `apm install` command, shell-quoted, for a hint."""
    return shlex.join(_command(scope))


def require() -> None:
    """Fails unless `apm` is on `PATH`."""
    if shutil.which("apm") is None:
        raise SkillGraftError(MISSING)


def install(scope: paths.Scope) -> None:
    """Registers and deploys the package."""
    command = _command(scope)
    try:
        result = subprocess.run(command, cwd=scope.root, check=False)
    except FileNotFoundError:
        raise SkillGraftError(MISSING) from None
    except OSError as error:
        raise SkillGraftError(f"cannot run `apm`: {error}") from None
    if result.returncode != 0:
        raise SkillGraftError(
            f"`{shlex.join(command)}` failed with exit code {result.returncode}"
        )
    if not registered(scope):
        raise SkillGraftError(
            f"{scope.manifest} does not list {scope.package.absolute()}: "
            "APM did not register the package"
        )


def registered(scope: paths.Scope) -> bool:
    """Whether a list item in the scope's `apm.yml`, `- x` or `- path: x`, names the
    package; a relative `x` is relative to the manifest's folder.

    A line scan, not a YAML parse: the runtime dependencies include no YAML library.
    """
    manifest = scope.manifest
    if not manifest.exists():
        return False
    package = scope.package.resolve()
    try:
        text = manifest.read_bytes().decode()
    except UnicodeDecodeError as error:
        raise SkillGraftError(f"{manifest}: {error}") from None
    for line in text.splitlines():
        item = line.strip()
        if not item.startswith("- "):
            continue
        value = item.removeprefix("- ").strip().removeprefix("path:")
        value = COMMENT.sub("", value).strip().strip("\"'")
        if value and (manifest.parent / Path(value).expanduser()).resolve() == package:
            return True
    return False
