"""Runs `git`. The user's git config applies, and git and ssh prompt as usual,
except for `apply`, which reads no config at all."""

import os
import subprocess
from pathlib import Path

from skill_graft.errors import SkillGraftError

# Variables that point git at another repository, as a git hook running
# skill-graft would set them: skill-graft names its repositories itself.
REDIRECTS = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_WORK_TREE",
)

# Rejects malformed trees, such as paths holding `..` or `.git`, as they arrive.
FSCK = ["-c", "transfer.fsckObjects=true"]


def run(
    *args: str,
    repo: Path | None = None,
    context: str,
    input: bytes | None = None,
) -> bytes:
    """Runs `git [--git-dir repo] args`; a failure names `context` and git's error."""
    result = call(*(["--git-dir", str(repo)] if repo else []), *args, input=input)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        raise SkillGraftError(f"{context}: `git {_subcommand(args)}` failed: {stderr}")
    return result.stdout


def call(
    *args: str,
    input: bytes | None = None,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    no_config: bool = False,
    missing: str = "git is not installed: no `git` on PATH",
) -> "subprocess.CompletedProcess[bytes]":
    """Runs `git args` without the variables in REDIRECTS, `env` on top.

    With `no_config`, also without the `GIT_CONFIG*` ones, which pass config in.
    Raises `missing` if there is no git; any exit code is the caller's to check.
    """
    base = {
        k: v
        for k, v in os.environ.items()
        if k not in REDIRECTS and not (no_config and k.startswith("GIT_CONFIG"))
    }
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            input=input,
            cwd=cwd,
            env=base | (env or {}),
        )
    except FileNotFoundError:
        raise SkillGraftError(missing) from None
    except OSError as error:
        raise SkillGraftError(f"cannot run `git`: {error}") from None


def apply(folder: Path, patch: bytes, home: Path) -> tuple[bool, str]:
    """Applies `patch` in `folder` as `git apply -p1 --reject`; whether it all applied.

    No git config is read: not the user's (`home` is an empty folder standing in
    for theirs), the system's or any passed in the environment; and no repository
    above `folder` is looked for. A hunk that fails leaves a `.rej` file.
    """
    result = call(
        "apply",
        "-p1",
        "--reject",
        "--whitespace=nowarn",
        "-",
        input=patch,
        cwd=folder,
        env={
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CEILING_DIRECTORIES": str(folder.parent),
        },
        no_config=True,
        missing="[patches] needs git: no `git` on PATH",
    )
    return result.returncode == 0, result.stderr.decode(errors="replace").strip()


def _subcommand(args: tuple[str, ...]) -> str:
    """The subcommand in `args`, past any leading `-c name=value` pairs."""
    at = 0
    while args[at : at + 1] == ("-c",):
        at += 2
    return args[at]
