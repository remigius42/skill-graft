"""Runs `git`. The user's git config applies, and git and ssh prompt as usual."""

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
    command = ["git", *(["--git-dir", str(repo)] if repo else []), *args]
    env = {k: v for k, v in os.environ.items() if k not in REDIRECTS}
    try:
        result = subprocess.run(command, capture_output=True, input=input, env=env)
    except FileNotFoundError:
        raise SkillGraftError("git is not installed: no `git` on PATH") from None
    except OSError as error:
        raise SkillGraftError(f"cannot run `git`: {error}") from None
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        raise SkillGraftError(f"{context}: `git {args[0]}` failed: {stderr}")
    return result.stdout
