"""The `git-sources` cache: where it lives and how URLs name repositories."""

import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest
from conftest import Upstream

from skill_graft.infra import cache, git, paths
from skill_graft.infra.errors import SkillGraftError


def test_default_location(home: Path) -> None:
    assert paths.cache() == home / ".cache" / "skill-graft"


def test_xdg_cache_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))

    assert paths.cache() == tmp_path / "xdg" / "skill-graft"


def test_relative_xdg_cache_home_is_ignored(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "rel")

    assert paths.cache() == home / ".cache" / "skill-graft"


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("https://github.com/mattpocock/skills.git", "skills"),
        ("https://github.com/mattpocock/skills/", "skills"),
        ("git@github.com:me/my skills.git", "my_skills"),
        ("/srv/skills", "skills"),
        ("https://example.com/", "example.com"),
        ("file:///", "repo"),
    ],
)
def test_key_is_readable(url: str, name: str) -> None:
    key = cache.key(url)

    assert key.rsplit("-", 1)[0] == name
    assert len(key.rsplit("-", 1)[1]) == 12


def test_key_is_distinct_per_url() -> None:
    assert cache.key("/a/skills") != cache.key("/b/skills")
    assert cache.key("/a/skills") == cache.key("/a/skills")


def test_fetch_clones_into_the_cache(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache.default()

    git_cache.fetch("mp", upstream.url)

    assert git_cache.has_commit(upstream.url, sha)
    assert (paths.cache() / "repos" / f"{cache.key(upstream.url)}.git").is_dir()


def test_fetch_once_per_url_per_command(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache.default()
    git_cache.fetch("a", upstream.url)
    newer = upstream.commit({"b/SKILL.md": "# b\n"})

    git_cache.fetch("b", upstream.url)

    assert not git_cache.has_commit(upstream.url, newer)
    later = cache.Cache.default()
    later.fetch("a", upstream.url)
    assert later.has_commit(upstream.url, newer)


def unlocked(folder: Path) -> list[str]:
    """The names in `folder`, if any, but lock files, which stay, as `flock` needs."""
    if not folder.exists():
        return []
    return sorted(p.name for p in folder.iterdir() if p.suffix != ".lock")


def leftover_of(final: Path) -> Path:
    """A killed run's temporary folder for `final`: the name the cache gives it."""
    folder = cache._temporary(final)
    assert folder.parent == final.parent and folder.name.startswith(f"{final.name}.")
    return folder


def test_interrupted_clone_does_not_block(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    leftover = leftover_of(paths.cache() / "repos" / f"{cache.key(upstream.url)}.git")
    (leftover / "junk").write_text("half a clone")
    git_cache = cache.Cache.default()

    git_cache.fetch("mp", upstream.url)

    assert git_cache.has_commit(upstream.url, sha)
    assert (leftover / "junk").exists()  # perhaps another run's clone in progress


def test_fetch_waits_for_another_run(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache.default()
    fetching = threading.Thread(target=git_cache.fetch, args=("mp", upstream.url))

    with cache.lock(git_cache.repository(upstream.url)):  # the other run
        fetching.start()
        fetching.join(0.5)
        assert fetching.is_alive()
    fetching.join(10)

    assert not fetching.is_alive() and git_cache.has_commit(upstream.url, sha)


def test_another_run_cloning_the_same_url(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    first, second = cache.Cache.default(), cache.Cache.default()
    first.fetch("mp", upstream.url)
    repo = first.repository(upstream.url)
    # As if `second` started cloning before `first` finished.
    second._clone(upstream.url, repo, "mp")

    assert second.has_commit(upstream.url, sha)
    assert unlocked(repo.parent) == [repo.name]


def test_sha256_remote(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up", sha256=True)
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache.default()

    git_cache.fetch("mp", upstream.url)

    assert git_cache.has_commit(upstream.url, sha)


def test_git_dir_from_a_hook_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    other = Upstream(tmp_path / "other")
    monkeypatch.setenv("GIT_DIR", str(other.path / ".git"))
    monkeypatch.setenv("GIT_OBJECT_DIRECTORY", str(other.path / ".git" / "objects"))

    cache.Cache.default().fetch("mp", upstream.url)

    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_OBJECT_DIRECTORY")
    assert cache.Cache.default().has_commit(upstream.url, sha)
    with pytest.raises(subprocess.CalledProcessError):
        other.git("cat-file", "-e", sha)


def test_unreachable_remote(tmp_path: Path) -> None:
    url = str(tmp_path / "nowhere")

    with pytest.raises(SkillGraftError) as error:
        cache.Cache.default().fetch("mp", url)

    assert "'mp'" in str(error.value) and url in str(error.value)
    assert "`git clone` failed" in str(error.value)
    assert unlocked(paths.cache() / "repos") == []


def test_git_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with pytest.raises(SkillGraftError, match="git is not installed"):
        cache.Cache.default().fetch("mp", "/srv/skills")


def test_checkout_on_a_fresh_machine(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n", "tdd/refs/x.md": "x\n"})

    tree = cache.Cache.default().checkout("mp", upstream.url, sha)

    assert (tree / "tdd" / "SKILL.md").read_text() == "# tdd\n"
    assert (tree / "tdd" / "refs" / "x.md").read_text() == "x\n"
    assert not (tree / ".git").exists()
    assert tree.is_relative_to(paths.cache())


def test_checkout_reads_the_ref_without_the_remote(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    old = upstream.commit({"tdd/SKILL.md": "old\n"})
    cache.Cache.default().fetch("mp", upstream.url)
    upstream.commit({"tdd/SKILL.md": "new\n"})
    upstream.path.rename(tmp_path / "gone")

    tree = cache.Cache.default().checkout("mp", upstream.url, old)

    assert (tree / "tdd" / "SKILL.md").read_text() == "old\n"


def test_checkout_after_the_cache_was_deleted(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    cache.Cache.default().checkout("mp", upstream.url, sha)
    shutil.rmtree(paths.cache())

    tree = cache.Cache.default().checkout("mp", upstream.url, sha)

    assert (tree / "tdd" / "SKILL.md").read_text() == "# tdd\n"


def test_ref_gone_upstream(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    missing = "c" * 40

    with pytest.raises(SkillGraftError) as error:
        cache.Cache.default().checkout("mp", upstream.url, missing)

    assert "'mp'" in str(error.value) and missing in str(error.value)


def test_interrupted_checkout_is_redone(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n", "tdd/b.md": "b\n"})
    partial = leftover_of(paths.cache() / "trees" / cache.key(upstream.url) / sha)
    (partial / "tdd").mkdir()
    (partial / "tdd" / "SKILL.md").write_text("# tdd\n")

    tree = cache.Cache.default().checkout("mp", upstream.url, sha)

    assert (tree / "tdd" / "b.md").read_text() == "b\n"
    # It may be another run's work in progress, so it is left alone.
    assert (partial / "tdd" / "SKILL.md").exists()


def test_another_run_exporting_the_same_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    tree = paths.cache() / "trees" / cache.key(upstream.url) / sha
    export = cache._export

    def racing(repo: Path, records: list[bytes], folder: Path, context: str) -> None:
        export(repo, records, folder, context)
        export(repo, records, tree, context)  # the other run renames first

    monkeypatch.setattr(cache, "_export", racing)

    result = cache.Cache.default().checkout("mp", upstream.url, sha)

    assert result == tree and (tree / "tdd" / "SKILL.md").exists()
    assert sorted(p.name for p in tree.parent.iterdir()) == [sha]


def test_checkout_ignores_attributes_and_filters(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {".gitattributes": "* text eol=crlf\n*.md filter=f\n", "a/SKILL.md": "a\nb\n"}
    )
    Path(os.environ["GIT_CONFIG_GLOBAL"]).write_text(
        '[filter "f"]\n\tsmudge = tr a X\n'
    )

    tree = cache.Cache.default().checkout("mp", upstream.url, sha)

    assert (tree / "a" / "SKILL.md").read_bytes() == b"a\nb\n"


@pytest.mark.parametrize("name", ["..", ".GIT", "GIT~1"])
def test_hostile_tree_path_is_refused(tmp_path: Path, name: str) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({})
    blob = subprocess.run(
        ["git", "-C", upstream.url, "hash-object", "-w", "--stdin"],
        input="x\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    def mktree(entry: str) -> str:
        return subprocess.run(
            ["git", "-C", upstream.url, "mktree"],
            input=entry,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    inner = mktree(f"100644 blob {blob}\tconfig\n")
    root = mktree(f"040000 tree {inner}\t{name}\n")
    sha = upstream.git("commit-tree", root, "-m", "evil")
    upstream.git("update-ref", "refs/heads/main", sha)

    # git's fsck refuses it on clone; the export's own check is the fallback.
    with pytest.raises(SkillGraftError):
        cache.Cache.default().checkout("mp", upstream.url, sha)
    assert unlocked(paths.cache() / "trees" / cache.key(upstream.url)) == []


def write_object(upstream: Upstream, kind: str, data: bytes) -> str:
    """Writes a raw object, unchecked, as a hostile upstream could."""
    return (
        subprocess.run(
            [
                "git",
                "-C",
                upstream.url,
                "hash-object",
                "-w",
                "--literally",
                "-t",
                kind,
                "--stdin",
            ],
            input=data,
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )


def tree_entry(mode: str, name: str, oid: str) -> bytes:
    return f"{mode} {name}".encode() + b"\0" + bytes.fromhex(oid)


def test_file_under_a_symlinked_folder_is_refused(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({})
    outside = tmp_path / "outside"
    outside.mkdir()
    link = write_object(upstream, "blob", str(outside).encode())
    blob = write_object(upstream, "blob", b"pwned\n")
    inner = write_object(upstream, "tree", tree_entry("100644", "x", blob))
    # Two entries named `a`: a symlink out, then a folder holding `x`.
    root = write_object(
        upstream,
        "tree",
        tree_entry("120000", "a", link) + tree_entry("40000", "a", inner),
    )
    sha = upstream.git("commit-tree", root, "-m", "evil")
    upstream.git("update-ref", "refs/heads/main", sha)

    with pytest.raises(SkillGraftError):
        cache.Cache.default().checkout("mp", upstream.url, sha)
    assert not (outside / "x").exists()


def test_symlink_under_a_symlinked_folder_is_refused(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({})
    outside = tmp_path / "outside"
    outside.mkdir()
    out = write_object(upstream, "blob", str(outside).encode())
    deep = write_object(upstream, "tree", tree_entry("120000", "c", out))
    middle = write_object(upstream, "tree", tree_entry("40000", "b", deep))
    root = write_object(
        upstream,
        "tree",
        tree_entry("120000", "a", out) + tree_entry("40000", "a", middle),
    )
    sha = upstream.git("commit-tree", root, "-m", "evil")
    upstream.git("update-ref", "refs/heads/main", sha)

    with pytest.raises(SkillGraftError):
        cache.Cache.default().checkout("mp", upstream.url, sha)
    assert list(outside.iterdir()) == []


def test_missing_object_is_reported(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"a/SKILL.md": "# a\n"})
    git_cache = cache.Cache.default()
    git_cache.fetch("mp", upstream.url)
    repo = git_cache.repository(upstream.url)
    # Unpack the clone's pack into loose objects, so one can be deleted.
    for pack in (repo / "objects" / "pack").glob("*.pack"):
        moved = pack.rename(tmp_path / pack.name)
        pack.with_suffix(".idx").unlink()
        with moved.open("rb") as stdin:
            subprocess.run(
                ["git", "--git-dir", str(repo), "unpack-objects", "-q"],
                stdin=stdin,
                check=True,
            )
    blob = upstream.git("rev-parse", f"{sha}:a/SKILL.md")
    (repo / "objects" / blob[:2] / blob[2:]).unlink()
    upstream.path.rename(tmp_path / "gone")

    with pytest.raises(SkillGraftError) as error:
        git_cache.checkout("mp", upstream.url, sha)

    assert "'mp'" in str(error.value) and upstream.url in str(error.value)
    assert "delete" not in str(error.value)


def files_in(tree: Path) -> set[str]:
    """Every file and symlink in `tree`, as paths relative to it."""
    return {
        str(p.relative_to(tree))
        for p in tree.rglob("*")
        if p.is_symlink() or not p.is_dir()
    }


def test_subdirectory_export_holds_only_it(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {"x/a/SKILL.md": "a\n", "x/b.md": "b\n", "y/c.md": "c\n", "top.md": "t\n"}
    )

    tree = cache.Cache.default().checkout("mp", upstream.url, sha, "x")

    assert files_in(tree) == {"x/a/SKILL.md", "x/b.md"}
    assert tree.name != sha and tree.name.startswith(f"{sha}-")


def test_subdirectory_through_a_symlink_or_a_file(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    (upstream.path / "a").mkdir()
    (upstream.path / "a" / "b").symlink_to("elsewhere")
    sha = upstream.commit({"a/sib.md": "s\n", "elsewhere/c/x.md": "x\n"})
    git_cache = cache.Cache.default()

    linked = git_cache.checkout("mp", upstream.url, sha, "a/b/c")

    assert files_in(linked) == {"a/b"}
    assert os.readlink(linked / "a" / "b") == "elsewhere"

    (upstream.path / "a" / "b").unlink()
    sha = upstream.commit({"a/b": "a file\n"})
    filed = cache.Cache.default().checkout("mp", upstream.url, sha, "a/b/c")

    assert files_in(filed) == {"a/b"}
    assert (filed / "a" / "b").read_text() == "a file\n"


def test_subdirectory_is_a_literal_name(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"s*/a.md": "a\n", "sx/b.md": "b\n", "PStack/c.md": "c\n"})
    git_cache = cache.Cache.default()
    git_cache.fetch("mp", upstream.url)
    # As a clone on a case-insensitive file system records it.
    upstream.git(
        "--git-dir",
        str(git_cache.repository(upstream.url)),
        "config",
        "core.ignorecase",
        "true",
    )

    tree = git_cache.checkout("mp", upstream.url, sha, "s*")
    other_case = git_cache.checkout("mp", upstream.url, sha, "pstack")

    assert files_in(tree) == {"s*/a.md"}
    assert files_in(other_case) == set()


def blobless(upstream: Upstream) -> Path:
    """Clones `upstream` into the cache as a partial clone: commits and trees only."""
    repo = cache.Cache.default().repository(upstream.url)
    repo.parent.mkdir(parents=True, exist_ok=True)
    upstream.git(
        "clone",
        "-q",
        "--bare",
        "--no-local",
        "--filter=blob:none",
        upstream.url,
        str(repo),
    )
    return repo


def missing_blobs(repo: Path) -> set[str]:
    """The objects `repo` lacks, of every commit any ref reaches."""
    out = subprocess.run(
        ["git", "--git-dir", str(repo), "rev-list", "--objects", "--all"]
        + ["--missing=print"],
        capture_output=True,
        text=True,
        check=True,
        env=os.environ | {"GIT_NO_LAZY_FETCH": "1"},
    ).stdout
    return {line[1:] for line in out.splitlines() if line.startswith("?")}


def recorded(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Every `git.run` call's arguments, from now on."""
    calls: list[tuple[str, ...]] = []
    run = git.run

    def recording(*args: str, **kwargs: Any) -> bytes:
        calls.append(args)
        return run(*args, **kwargs)

    monkeypatch.setattr(git, "run", recording)
    return calls


def blob_fetches(calls: list[tuple[str, ...]]) -> list[tuple[str, ...]]:
    return [call for call in calls if "fetch" in call and "--stdin" in call]


def test_subdirectory_blobs_fetched_in_one_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({f"x/{i}.md": f"{i}\n" for i in range(20)} | {"y.md": "y\n"})
    blobless(upstream)
    calls = recorded(monkeypatch)

    tree = cache.Cache.default().checkout("mp", upstream.url, sha, "x")

    assert len(files_in(tree)) == 20
    (fetch,) = blob_fetches(calls)
    assert "fetch.negotiationAlgorithm=noop" in fetch
    assert not [call for call in calls if "--batch-check" in call]


@pytest.mark.parametrize(
    ("subdirectory", "exported"),
    [
        ("x", {"x/a.md"}),  # a folder
        ("f/g", {"f"}),  # through a file
        ("l/g", {"l"}),  # through a symlink
        ("f", {"f"}),  # a file itself
    ],
)
def test_export_at_a_commit_not_touching_it(
    tmp_path: Path, subdirectory: str, exported: set[str]
) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.path.mkdir(exist_ok=True)
    (upstream.path / "l").symlink_to("x")
    upstream.commit({"x/a.md": "a\n", "f": "f\n", "y.md": "1\n"})
    sha = upstream.commit({"y.md": "2\n"})  # git lists no object of `x` by pathspec
    blobless(upstream)

    tree = cache.Cache.default().checkout("mp", upstream.url, sha, subdirectory)

    assert files_in(tree) == exported


def test_symlinked_prefix_fetched_in_the_same_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = Upstream(tmp_path / "up")
    (upstream.path / "a").mkdir()
    (upstream.path / "a" / "b").symlink_to("elsewhere")
    sha = upstream.commit({"elsewhere/c/x.md": "x\n"})
    blobless(upstream)
    calls = recorded(monkeypatch)

    tree = cache.Cache.default().checkout("mp", upstream.url, sha, "a/b/c")

    assert os.readlink(tree / "a" / "b") == "elsewhere"
    assert len(blob_fetches(calls)) == 1


def test_one_subdirectory_of_a_monorepo(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"x/f.md": "old\n", "big.bin": "big\n"})
    sha = upstream.commit({"x/f.md": "new\n"})
    repo = blobless(upstream)

    cache.Cache.default().checkout("mp", upstream.url, sha, "x")

    assert missing_blobs(repo) == {
        upstream.git("rev-parse", f"{sha}:big.bin"),
        upstream.git("rev-parse", f"{sha}~:x/f.md"),
    }


def test_commit_cached_files_not(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"x/f.md": "x\n"})
    blobless(upstream)
    upstream.path.rename(tmp_path / "gone")

    with pytest.raises(SkillGraftError) as error:
        cache.Cache.default().checkout("mp", upstream.url, sha, "x")

    assert "'mp'" in str(error.value) and upstream.url in str(error.value)


def test_pruned_export_read_offline(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"x/f.md": "x\n"})
    blobless(upstream)
    tree = cache.Cache.default().checkout("mp", upstream.url, sha, "x")
    shutil.rmtree(tree)
    upstream.path.rename(tmp_path / "gone")

    again = cache.Cache.default().checkout("mp", upstream.url, sha, "x")

    assert (again / "x" / "f.md").read_text() == "x\n"


def test_checkout_keeps_modes_and_skips_submodules(tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    script = upstream.path / "a" / "run.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    (upstream.path / "a" / "b.md").write_text("b\n")
    (upstream.path / "a" / "link.md").symlink_to("b.md")
    upstream.git("add", "-A")
    upstream.git("update-index", "--add", "--cacheinfo", f"160000,{'d' * 40},a/sub")
    sha = upstream.commit({})

    tree = cache.Cache.default().checkout("mp", upstream.url, sha)

    assert os.access(tree / "a" / "run.sh", os.X_OK)
    assert not os.access(tree / "a" / "b.md", os.X_OK)
    assert os.readlink(tree / "a" / "link.md") == "b.md"
    assert not (tree / "a" / "sub").exists()
