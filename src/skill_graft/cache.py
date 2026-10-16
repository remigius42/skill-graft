"""The cache of git sources: one bare repository per URL, one export per commit."""

import hashlib
import re
import shutil
from pathlib import Path

from skill_graft import git
from skill_graft.errors import SkillGraftError

# Characters a cache folder name keeps; others become `_`.
UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def key(url: str) -> str:
    """`<last URL segment>-<hash>`: readable, and distinct per URL."""
    segment = re.split(r"[/:]", url.rstrip("/"))[-1].removesuffix(".git")
    name = UNSAFE.sub("_", segment) or "repo"
    return f"{name}-{hashlib.sha256(url.encode()).hexdigest()[:12]}"


class Cache:
    """The cache under `root`, fetching each URL at most once in its lifetime."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._fetched: set[str] = set()

    def repository(self, url: str) -> Path:
        return self.root / "repos" / f"{key(url)}.git"

    def fetch(self, alias: str, url: str) -> None:
        """Brings every branch of `url` into its repository, cloning it first."""
        if url in self._fetched:
            return
        context = f"source {alias!r} ({url})"
        repo = self.repository(url)
        if repo.exists():
            git.run(
                *git.FSCK,
                "fetch",
                "-q",
                "--prune",
                "--no-tags",
                "origin",
                "+refs/heads/*:refs/heads/*",
                repo=repo,
                context=context,
            )
        else:
            self._clone(url, repo, context)
        self._fetched.add(url)

    def has_commit(self, url: str, sha: str) -> bool:
        repo = self.repository(url)
        if not repo.exists():
            return False
        try:
            git.run("cat-file", "-e", f"{sha}^{{commit}}", repo=repo, context=url)
        except SkillGraftError:
            return False
        return True

    @staticmethod
    def _clone(url: str, repo: Path, context: str) -> None:
        """Clones into a temporary name, so a killed clone never looks complete.

        Clone, unlike `init`, takes the remote's hash format, SHA-1 or SHA-256.
        """
        tmp = repo.with_name(repo.name + ".tmp")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.parent.mkdir(parents=True, exist_ok=True)
        git.run(
            *git.FSCK,
            "clone",
            "-q",
            "--bare",
            "--no-tags",
            "--",
            url,
            str(tmp),
            context=context,
        )
        tmp.rename(repo)
