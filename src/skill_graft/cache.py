"""The cache of git sources: one bare repository per URL, one export per commit."""

import fcntl
import hashlib
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
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
    """The cache under `root`, fetching each URL at most once in its lifetime.

    With a `reference`, it reads what that cache holds but writes only under its
    own `root`: what `update --dry-run` needs to leave the real cache untouched.
    """

    def __init__(self, root: Path, reference: "Cache | None" = None) -> None:
        self.root = root
        self.reference = reference
        self._fetched: set[str] = set()

    def repository(self, url: str) -> Path:
        return self.root / "repos" / f"{key(url)}.git"

    def fetch(self, alias: str, url: str) -> None:
        """Brings every branch of `url` into its repository, cloning it first."""
        if url in self._fetched:
            return
        context = f"source {alias!r} ({url})"
        repo = self.repository(url)
        with lock(repo):
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

    def checkout(self, alias: str, url: str, ref: str) -> Path:
        """The tree of commit `ref`, as committed; fetches only if `ref` is missing."""
        tree = self._tree(url, ref)
        if tree.exists():  # renamed into place only once complete
            return tree
        if self.reference and (shared := self.reference._tree(url, ref)).exists():
            return shared
        repo = self._repository_with(url, ref)
        if repo is None:
            self.fetch(alias, url)
            repo = self._repository_with(url, ref)
            if repo is None:
                raise SkillGraftError(
                    f"source {alias!r}: ref {ref} is on no branch of {url}"
                )
        context = f"source {alias!r} ({url})"
        _build(tree, lambda tmp: _export(repo, ref, tmp, context))
        return tree

    def has_commit(self, url: str, sha: str) -> bool:
        return self._repository_with(url, sha) is not None

    def _tree(self, url: str, ref: str) -> Path:
        return self.root / "trees" / key(url) / ref

    def _repository_with(self, url: str, sha: str) -> Path | None:
        """This cache's repository for `url` if it has commit `sha`, else the reference's."""
        repo = self.repository(url)
        if repo.exists() and _has_commit(repo, sha):
            return repo
        return self.reference._repository_with(url, sha) if self.reference else None

    def _clone(self, url: str, repo: Path, context: str) -> None:
        """Clones into a temporary name, so a killed clone never looks complete.

        Clone, unlike `init`, takes the remote's hash format, SHA-1 or SHA-256.
        Objects the reference cache already has are borrowed, not downloaded.
        `--no-local` sends a local path through git's transport too, so that
        fsck checks its objects, as it does a remote's.
        """
        borrow = (
            ["--reference-if-able", str(self.reference.repository(url))]
            if self.reference
            else []
        )
        _build(
            repo,
            lambda tmp: git.run(
                *git.FSCK,
                "clone",
                "-q",
                "--bare",
                "--no-local",
                "--no-tags",
                *borrow,
                "--",
                url,
                str(tmp),
                context=context,
            ),
        )


@contextmanager
def lock(repo: Path) -> Iterator[None]:
    """Holds `repo`'s lock, waiting for any other run that holds it.

    Two fetches into one repository would fail on git's own ref locks.
    """
    repo.parent.mkdir(parents=True, exist_ok=True)
    with open(repo.with_name(f"{repo.name}.lock"), "a") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        yield


def _build(final: Path, make: Callable[[Path], object]) -> None:
    """Has `make` fill a temporary folder, then puts it at `final`.

    A failure removes the temporary folder; only a killed run leaves one.
    """
    tmp = _temporary(final)
    try:
        make(tmp)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    _place(tmp, final)


def _temporary(final: Path) -> Path:
    """A new empty folder beside `final`, unique to this run.

    A fixed name could be another run's work in progress; a killed run's
    leftover is only garbage, never mistaken for `final`.
    """
    final.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(prefix=f"{final.name}.", suffix=".tmp", dir=final.parent)
    )


def _place(tmp: Path, final: Path) -> None:
    """Renames `tmp` to `final`, or drops it if another run got there first."""
    try:
        tmp.rename(final)
    except OSError:
        if not final.exists():
            raise
        shutil.rmtree(tmp)


def _has_commit(repo: Path, sha: str) -> bool:
    try:
        git.run("cat-file", "-e", f"{sha}^{{commit}}", repo=repo, context=str(repo))
    except SkillGraftError:
        return False
    return True


def _export(repo: Path, ref: str, folder: Path, context: str) -> None:
    """Writes the tree of `ref` into `folder`, byte for byte as committed.

    Unlike a checkout, no `.gitattributes` conversion or filter driver applies,
    and unlike `git archive`, `export-ignore` files are kept. Submodules are
    skipped.
    """
    listing = git.run(
        "ls-tree", "-r", "-z", "--full-tree", ref, repo=repo, context=context
    )
    entries = []
    for record in listing.split(b"\0"):
        if not record:
            continue
        meta, name = record.split(b"\t", 1)
        mode, kind, oid = meta.split(b" ")
        if kind == b"blob":
            entries.append((mode, oid, _safe(os.fsdecode(name), context)))
    blobs = _read_blobs(repo, [oid for _, oid, _ in entries], context)
    written = list(zip(entries, blobs, strict=True))
    # Symlinks last, so no file is written through one; and every write must
    # land in a new path whose real parent is inside `folder`, which a tree with
    # duplicate names (or names equal but for case) would otherwise defeat.
    written.sort(key=lambda item: item[0][0] == b"120000")
    root = folder.resolve()
    for (mode, _, path), content in written:
        target = folder / path
        if not target.parent.resolve().is_relative_to(root) or os.path.lexists(target):
            raise SkillGraftError(f"{context}: refusing the tree path {path!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == b"120000":
            target.symlink_to(os.fsdecode(content))
        else:
            target.write_bytes(content)
            if mode == b"100755":
                target.chmod(target.stat().st_mode | 0o111)


def _safe(path: str, context: str) -> str:
    """A tree path, refused if it could leave the folder or write into `.git`.

    git's fsck already refuses these on clone and fetch; this is a second guard.
    """
    parts = path.split("/")
    if any(part in ("", ".", "..") or part.lower() == ".git" for part in parts):
        raise SkillGraftError(f"{context}: refusing the tree path {path!r}")
    return path


def _read_blobs(repo: Path, oids: list[bytes], context: str) -> list[bytes]:
    """The contents of `oids`, read by one `git cat-file --batch`."""
    if not oids:
        return []
    output = git.run(
        "cat-file",
        "--batch",
        repo=repo,
        context=context,
        input=b"\n".join(oids) + b"\n",
    )
    blobs, at = [], 0
    for oid in oids:
        header_end = output.index(b"\n", at)
        header = output[at:header_end].split(b" ")
        if len(header) != 3:  # `<oid> missing`, or worse
            raise SkillGraftError(
                f"{context}: object {oid.decode()} is missing from {repo}; "
                "delete that folder and run again"
            )
        size = int(header[2])
        start = header_end + 1
        blobs.append(output[start : start + size])
        at = start + size + 1  # the newline after each object
    return blobs
