"""The `git-sources` spec, through `skill-graft build --no-install`."""

import shutil
import subprocess
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import (
    Upstream,
    build,
    configure,
    deadline,
    seed,
    skill,
    vendored,
    write_config,
)

from skill_graft.cli import main
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache

Capsys: TypeAlias = pytest.CaptureFixture[str]


def package_files(home: Path) -> set[Path]:
    package = home / ".apm" / "skill-graft"
    return {p for p in package.rglob("*") if ".apm" not in p.relative_to(package).parts}


def test_skill_from_git(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {"skills/tdd/SKILL.md": "# tdd\n", "skills/tdd/refs/x.md": "x\n"}
    )
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    before = package_files(home)

    assert build(capsys) == (0, "")

    tdd = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd"
    assert (tdd / "SKILL.md").read_text() == "# tdd\n"
    assert (tdd / "refs" / "x.md").read_text() == "x\n"
    assert not (tdd / ".git").exists()
    assert (home / ".cache" / "skill-graft" / "repos").is_dir()
    assert package_files(home) == before | {
        home / ".apm" / "skill-graft" / "skill-graft.lock"
    }


def test_skill_from_a_sha256_remote(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up", sha256=True)
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    config = write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )

    assert len(sha) == 64 and build(capsys) == (0, "")

    skills = config.parent / ".apm" / "skills"
    assert (skills / "tdd" / "SKILL.md").read_text() == "# tdd\n"


def test_build_reads_the_ref_not_the_tip(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "old\n"})
    upstream.commit({"tdd/SKILL.md": "new\n"})
    config = write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    text = config.read_text()

    assert build(capsys) == (0, "")

    skills = config.parent / ".apm" / "skills"
    assert (skills / "tdd" / "SKILL.md").read_text() == "old\n"
    assert config.read_text() == text


def test_discovery_stays_inside_a_git_source(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "local" / "secret")
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"skills/tdd/SKILL.md": "# tdd\n"})
    (upstream.path / "out").symlink_to(home / "local")
    (upstream.path / "in").symlink_to("skills")
    sha = upstream.commit({})
    git = f'[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'

    write_config('entries = ["mp/secret"]\n' + git)
    code, err = build(capsys)
    assert code == 1 and "mp/secret" in err

    write_config('entries = ["mp/tdd"]\n' + git)
    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def git_source(upstream: Upstream, entry: str) -> None:
    """Commits the upstream's working tree and makes `entry` the only entry."""
    sha = upstream.commit({})
    write_config(
        f'entries = ["{entry}"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )


def test_skill_md_linked_out_of_the_tree(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    (home / "local").mkdir()
    (home / "local" / "notes.md").write_text("---\nname: leaked-marker\n---\n")
    upstream = Upstream(tmp_path / "up")
    (upstream.path / "evil").mkdir()
    (upstream.path / "evil" / "SKILL.md").symlink_to(home / "local" / "notes.md")
    git_source(upstream, "mp/evil")

    code = main(["build", "--no-install"])

    out, err = capsys.readouterr()
    assert code == 1
    assert "evil/SKILL.md: a symlink leading outside its skill" in err
    assert "leaked-marker" not in out + err and "notes.md" not in out + err


def test_unused_skill_linked_out_of_the_tree(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    (upstream.path / "evil").mkdir()
    (upstream.path / "evil" / "SKILL.md").symlink_to("/dev/zero")
    git_source(upstream, "mp/tdd")

    with deadline(30):  # the git fetch too, on a slow machine
        assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_skill_md_linked_inside_its_skill(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"tdd/main.md": "---\nname: tdd\n---\nmain\n"})
    (upstream.path / "tdd" / "SKILL.md").symlink_to("main.md")
    git_source(upstream, "mp/tdd")

    assert build(capsys) == (0, "")

    vendored_md = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd" / "SKILL.md"
    assert vendored_md.read_text() == "---\nname: tdd\n---\nmain\n"


@pytest.mark.parametrize("entries", ['["mp/tdd"]', '["own/chisel"]'])
def test_git_source_without_ref(
    home: Path, tmp_path: Path, capsys: Capsys, entries: str
) -> None:
    skill(home / "src" / "chisel")
    configure(["own/chisel"], own="~/src")
    build(capsys)
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(
        f"entries = {entries}\n"
        f'[sources.own]\npath = "~/src"\n[sources.mp]\ngit = "{upstream.url}"\n'
    )

    code, err = build(capsys)

    assert code == 1
    assert "'mp'" in err and "skill-graft update mp" in err
    assert vendored() == {"chisel"}
    assert not (home / ".cache").exists()


def test_several_new_git_sources(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(
        f'[sources.a]\ngit = "{upstream.url}"\n[sources.b]\ngit = "{upstream.url}"\n'
    )

    code, err = build(capsys)

    assert code == 1
    assert "sources 'a', 'b' have no ref" in err and "skill-graft update a b" in err


def test_build_into_fetches_an_uncached_ref(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    into = tmp_path / "into"
    into.mkdir()

    assert main(["build", "--into", str(into)]) == 0

    assert (home / ".cache" / "skill-graft" / "repos").is_dir()
    assert (into / ".apm" / "skills" / "tdd" / "SKILL.md").read_text() == "# tdd\n"


def vanish(upstream: Upstream) -> None:
    """Resets `main` to a commit of its own, so no branch holds what it held, and
    has git delete what is left unreachable."""
    upstream.git("checkout", "-q", "--orphan", "rewritten")
    upstream.commit({"other/SKILL.md": "# other\n"})
    upstream.git("branch", "-D", "main")
    upstream.git("branch", "-m", "main")
    upstream.git("reflog", "expire", "--expire=now", "--all")
    upstream.git("gc", "-q", "--prune=now")


# A partial clone's gc keeps what its promisor packs hold; one cloned whole, as
# before blobless clones, keeps nothing unreachable.
@pytest.mark.parametrize("whole", [False, True])
def test_ref_vanished_upstream(tmp_path: Path, capsys: Capsys, whole: bool) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"skills/tdd/SKILL.md": "# tdd\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    if whole:
        seed(upstream, upstream.url)
    assert build(capsys) == (0, "")
    vanish(upstream)
    Cache.default().fetch("mp", upstream.url)
    repo = Cache.default().repository(upstream.url)
    subprocess.run(
        ["git", "--git-dir", str(repo), "gc", "-q", "--prune=now"], check=True
    )
    shutil.rmtree(paths.cache() / "trees")
    upstream.path.rename(tmp_path / "gone")

    assert build(capsys) == (0, "")

    skills = Path.home() / ".apm" / "skill-graft" / ".apm" / "skills"
    assert (skills / "tdd" / "SKILL.md").read_text() == "# tdd\n"


def test_ref_vanished_then_cache_deleted(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"skills/tdd/SKILL.md": "# tdd\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )
    assert build(capsys) == (0, "")
    vanish(upstream)
    shutil.rmtree(paths.cache())

    code, err = build(capsys)

    assert code == 1 and "'mp'" in err and sha in err
