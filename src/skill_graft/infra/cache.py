"""The cache of git sources: one bare repository per URL, one export per commit."""

import fcntl
import hashlib
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from pathlib import Path

from skill_graft.infra import git, paths
from skill_graft.infra.errors import SkillGraftError

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
        self._pinned: set[tuple[str, str]] = set()

    @classmethod
    def default(cls) -> "Cache":
        """The cache every package shares, at `paths.cache()`; one per command."""
        return cls(paths.cache())

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
                    "--recurse-submodules=no",
                    "origin",
                    "+refs/heads/*:refs/heads/*",
                    repo=repo,
                    context=context,
                )
            else:
                self._clone(url, repo, context)
        self._fetched.add(url)

    def checkout(
        self, alias: str, url: str, ref: str, subdirectory: str | None = None
    ) -> Path:
        """The tree of commit `ref`, as committed; fetches only if `ref` is missing.

        With a `subdirectory`, the tree holds only it, and the entries on its path.
        """
        tree = self._tree(url, ref, subdirectory)
        if tree.exists():  # renamed into place only once complete
            self._use(tree, url, ref)
            return tree
        if (
            self.reference
            and (shared := self.reference._tree(url, ref, subdirectory)).exists()
        ):
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
        records, tips = _listing(repo, ref, subdirectory, context)
        # Listed without the lock: an export with its files at hand waits for no
        # other run's clone or fetch.
        missing: list[bytes] | None = _missing(repo, records, tips, context)
        if missing:
            if repo != self.repository(url):
                # The reference's stays as is; the overlay sees the same objects.
                repo = self._overlay(url, repo, context)
            else:
                missing = None  # listed again under the lock: another run may fetch
            with lock(repo):
                self._fill(repo, records, tips, context, missing)
        _build(tree, lambda tmp: _export(repo, records, tmp, context))
        self._use(tree, url, ref)
        return tree

    def _use(self, tree: Path, url: str, sha: str) -> None:
        """Marks export `tree` used now, so `prune` keeps it, and pins `sha`.

        A dry run does neither. Best effort, as reading needs neither: a cache
        the user cannot write, or a prune removing `tree` this moment.
        """
        if self.reference is None:
            with suppress(OSError):
                os.utime(tree)
            self._pin(url, sha)

    def _pin(self, url: str, sha: str) -> None:
        """Keeps commit `sha`, its trees and the files fetched for it, in its
        repository through `fetch --prune` and gc, even once gone upstream.

        Best effort, and under git's own lock on the one ref, not the
        repository's: a missing repository, or one lacking the commit, is
        skipped. Once per commit in this cache's lifetime: one command.
        """
        repo = self.repository(url)
        if (url, sha) in self._pinned or not repo.exists():
            return
        self._pinned.add((url, sha))
        pin = f"refs/skill-graft/{sha}"
        try:
            git.run("rev-parse", "--verify", "-q", pin, repo=repo, context=str(repo))
        except SkillGraftError:  # absent
            try:
                git.run("update-ref", pin, sha, repo=repo, context=str(repo))
            except SkillGraftError:
                pass

    def _fill(
        self,
        repo: Path,
        records: list[bytes],
        tips: list[str],
        context: str,
        missing: list[bytes] | None,
    ) -> None:
        """Fetches the blobs of `records` that `repo` lacks, `missing` if
        already listed.

        A remote refusing them by name has the repository fetched whole, and
        whole from then on, once no blob is missing; any other failure leaves
        it as it was.
        """
        if missing is None:
            missing = _missing(repo, records, tips, context)
        if not missing:
            return
        try:
            _fetch_blobs(repo, missing, context)
        except SkillGraftError as error:
            if not _refused(error):
                raise
            if self.reference is not None:
                # Refetching every branch into a temporary folder would cost a
                # full download on every dry run; `update` converts the real one.
                raise SkillGraftError(
                    f"{context}: the remote refuses files asked by name: "
                    "run `update` without `--dry-run` to fetch them"
                ) from None
            _refetch(repo, context)
            if not _missing(repo, records, tips, context):
                git.run(
                    "config",
                    "--unset",
                    "remote.origin.partialclonefilter",
                    repo=repo,
                    context=context,
                )

    def _overlay(self, url: str, real: Path, context: str) -> Path:
        """A repository of this cache's own over `real`'s objects, to fetch the
        blobs `real` lacks into, leaving `real` untouched.

        Cheaper than a borrowing clone: no ref advertisement or negotiation.
        """

        def make(tmp: Path) -> None:
            object_format = git.run(
                "rev-parse", "--show-object-format", repo=real, context=context
            )
            git.run(
                "init",
                "-q",
                "--bare",
                f"--object-format={object_format.decode().strip()}",
                str(tmp),
                context=context,
            )
            alternates = tmp / "objects" / "info" / "alternates"
            alternates.write_text(f"{(real / 'objects').resolve()}\n")
            promisor = git.run(
                "config",
                "--local",
                "--get-regexp",
                r"^(remote\.origin\.(url|promisor|partialclonefilter)"
                r"|extensions\.partialclone)$",
                repo=real,
                context=context,
            )
            for line in promisor.decode().splitlines():
                name, value = line.split(" ", 1)
                git.run("config", name, value, repo=tmp, context=context)

        overlay = self.repository(url)
        _build(overlay, make)
        return overlay

    def has_commit(self, url: str, sha: str) -> bool:
        return self._repository_with(url, sha) is not None

    def _tree(self, url: str, ref: str, subdirectory: str | None) -> Path:
        """`<sha>`, or `<sha>-<hash>` per subdirectory: each complete for its own."""
        name = ref
        if subdirectory is not None:
            name += f"-{hashlib.sha256(subdirectory.encode()).hexdigest()[:12]}"
        return self.root / "trees" / key(url) / name

    def _repository_with(self, url: str, sha: str) -> Path | None:
        """This cache's repository for `url` if it has commit `sha`, else the
        reference's."""
        repo = self.repository(url)
        if repo.exists() and _has_commit(repo, sha):
            return repo
        return self.reference._repository_with(url, sha) if self.reference else None

    def _clone(self, url: str, repo: Path, context: str) -> None:
        """Clones into a temporary name, so a killed clone never looks complete.

        Clone, unlike `init`, takes the remote's hash format, SHA-1 or SHA-256.
        Objects the reference cache already has are borrowed, not downloaded.
        `--no-local` sends a local path through git's transport too, so that
        fsck checks its objects, as it does a remote's. The clone is blobless,
        and its fetches follow: an export fetches the files it writes. A remote
        without filters gives a whole clone.
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
                "--filter=blob:none",
                "--recurse-submodules=no",
                *borrow,
                "--",
                url,
                str(tmp),
                context=context,
            ),
        )


# An export, or a killed run's leftover, unused for longer is removed.
UNUSED = 30 * 24 * 3600


def prune(root: Path, now: float) -> None:
    """Removes from the cache at `root` each export, and each leftover of a
    killed export or clone, unused for UNUSED seconds before `now`.

    Never a repository, nor a `trees/<key>` folder, which a concurrent export
    may be about to fill. Never fails: an entry another run removed or holds
    is skipped, and an empty or missing cache is nothing to prune.
    """
    for entries in [*_children(root / "trees"), root / "repos"]:
        for entry in _children(entries):
            if entries.name == "repos" and entry.suffix != ".tmp":
                continue
            try:
                if now - entry.lstat().st_mtime <= UNUSED:
                    continue
                doomed = _temporary(entry)
            except OSError:
                continue
            # Renamed first, so no run takes it for complete while it goes; if
            # another run got there first, only the empty `doomed` goes.
            with suppress(OSError):
                entry.rename(doomed)
            shutil.rmtree(doomed, ignore_errors=True)


def _children(folder: Path) -> list[Path]:
    try:
        return list(folder.iterdir())
    except OSError:
        return []


@contextmanager
def lock(repo: Path) -> Generator[None]:
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


def _missing(
    repo: Path, records: list[bytes], tips: list[str], context: str
) -> list[bytes]:
    """The blobs of `records` that `repo` lacks, listed from `tips`.

    `rev-list --missing=print` finds them without fetching, on any git. A tip
    may reach other blobs, such as a prefix's siblings: only those of
    `records` count.
    """
    if not tips:
        return []
    listing = git.run(
        "rev-list",
        "--objects",
        "--missing=print",
        "--no-walk",
        *tips,
        repo=repo,
        context=context,
    )
    wanted = {record.split(b"\t", 1)[0].split(b" ")[2] for record in records}
    return [
        line[1:]
        for line in listing.splitlines()
        if line.startswith(b"?") and line[1:] in wanted
    ]


def _fetch_blobs(repo: Path, missing: list[bytes], context: str) -> None:
    """Fetches the blobs `missing` into `repo`, in one request.

    The want list is blobs: negotiating over every branch, as `noop` skips,
    would only cost round trips.
    """
    git.run(
        *git.FSCK,
        "-c",
        "fetch.negotiationAlgorithm=noop",
        "fetch",
        "-q",
        "--no-tags",
        "--no-write-fetch-head",
        "--recurse-submodules=no",
        "--filter=blob:none",
        "--stdin",
        "origin",
        repo=repo,
        context=context,
        input=b"\n".join(missing) + b"\n",
    )


def _refetch(repo: Path, context: str) -> None:
    """Fetches every branch into `repo` whole, objects it has included."""
    try:
        git.run(
            *git.FSCK,
            "fetch",
            "-q",
            "--refetch",
            "--no-filter",
            "--no-tags",
            "--recurse-submodules=no",
            "origin",
            "+refs/heads/*:refs/heads/*",
            repo=repo,
            context=context,
        )
    except SkillGraftError as error:
        if "unknown option `refetch'" not in str(error):  # as git before 2.36 says
            raise
        raise SkillGraftError(
            f"{context}: the remote refuses files asked by name; "
            "fetching the repository whole needs git 2.36 or later"
        ) from None


# How git refuses an object asked by name: protocol v0 without
# `uploadpack.allowAnySHA1InWant`, and v2. No exit code tells them apart.
REFUSALS = ("unadvertised object", "not our ref")


def _refused(error: SkillGraftError) -> bool:
    return any(refusal in str(error) for refusal in REFUSALS)


def _export(repo: Path, records: list[bytes], folder: Path, context: str) -> None:
    """Writes the tree entries `records` into `folder`, byte for byte as committed.

    Unlike a checkout, no `.gitattributes` conversion or filter driver applies,
    and unlike `git archive`, `export-ignore` files are kept. Submodules are
    skipped.
    """
    entries = []
    for record in records:
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


def _listing(
    repo: Path, ref: str, subdirectory: str | None, context: str
) -> tuple[list[bytes], list[str]]:
    """The `ls-tree` records of `ref`'s tree, or of `subdirectory` and of the
    blobs at its proper prefixes, so a prefix that is a file or symlink is
    exported as such; and the objects to list their missing blobs from.

    Those are trees, which a blobless repository always has, and no pathspec:
    under one, `rev-list --no-walk` lists nothing at a commit not touching it,
    on some git versions. The subdirectory's own tree, or for a blob on the
    path, the folder holding it.

    For a prefix that is a folder git lists its children too: only exact
    paths are kept. A name is matched literally and by case, whatever
    `core.ignorecase` the clone recorded.
    """
    if subdirectory is None:
        return _ls_tree(repo, context, "-r", ref), [ref]
    parts = subdirectory.split("/")
    paths = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
    records = _ls_tree(repo, context, "-r", ref, "--", subdirectory)
    exact = {os.fsencode(path) for path in paths}
    on_path = []  # (kind, oid, name, record) of each entry at exactly a path
    # `-t`: the trees on the way are listed too, not only what is under them.
    for record in _ls_tree(repo, context, "-t", ref, "--", *paths):
        meta, name = record.split(b"\t", 1)
        if name in exact:
            _, kind, raw = meta.split(b" ")
            on_path.append((kind, raw.decode(), name, record))
    trees = {b"": f"{ref}^{{tree}}"}
    trees |= {name: oid for kind, oid, name, _ in on_path if kind == b"tree"}
    tips = []
    own = os.fsencode(subdirectory)
    for kind, oid, name, record in on_path:
        if kind == b"tree" and name == own:
            tips.append(oid)
        elif kind == b"blob":
            tips.append(trees[name.rpartition(b"/")[0]])
            if name != own:  # the subdirectory's own is in `records` already
                records.append(record)
    return records, list(dict.fromkeys(tips))


# Pathspecs name paths literally and by case, whatever the clone recorded:
# a clone on a case-insensitive file system sets `core.ignorecase`.
LITERAL = ["-c", "core.ignorecase=false", "--literal-pathspecs"]


def _ls_tree(repo: Path, context: str, *args: str) -> list[bytes]:
    listing = git.run(
        *LITERAL,
        "ls-tree",
        "-z",
        "--full-tree",
        *args,
        repo=repo,
        context=context,
    )
    return [record for record in listing.split(b"\0") if record]


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
                f"{context}: object {oid.decode()} is missing from {repo}, "
                'and fetching it did not bring it; see "Cache" in the README'
            )
        size = int(header[2])
        start = header_end + 1
        blobs.append(output[start : start + size])
        at = start + size + 1  # the newline after each object
    return blobs
