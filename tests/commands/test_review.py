"""The Hull diff's old side read from the lock and the Vendored copies."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias, cast

import pytest
import tomlkit
from conftest import configure, skill, write_config

from skill_graft.cli import main
from skill_graft.commands import review
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.pipeline import compute, config, lock

Capsys: TypeAlias = pytest.CaptureFixture[str]


def hull_diff(capsys: Capsys) -> list[str]:
    """The Hull diff of the copies against the config's hull, as printed."""
    scope = paths.Scope(Path.home())
    before = review.vendored(scope.skills, lock.load(scope.lock_file))
    capsys.readouterr()
    with compute.compute_hull(scope, config.load(scope), Cache.default()) as hull:
        review.print_diff(before, hull, lock.skill_hashes(hull))
    return capsys.readouterr().out.splitlines()


def test_renamed_skill_changed(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "---\nname: tdd\n---\n")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/tdd" = "mp-tdd"\n'
    )

    assert hull_diff(capsys)[1:3] == [
        "~ mp/tdd",
        "  SKILL.md (changed, 18 -> 21 bytes)",
    ]


def test_first_add_all_added(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")

    assert hull_diff(capsys) == [
        "hull (+ added, - removed, ~ changed):",
        "+ mp/grilling",
        "  SKILL.md (new, 8 bytes)",
        "+ mp/tdd",
        "  SKILL.md (new, 10 bytes)",
    ]


def test_overwrites_a_deployed_diff_an_earlier_release_wrote(home: Path) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")
    old = (
        "# skill-graft Deployed diff: each Skill's text as `build` deploys it, Patches"
        " and Renames applied,\n# written by 0.3.0\n"
    )
    (home / "review.diff").write_text(old)

    assert main(["resolve", "--dry-run", "--diff-file", "review.diff"]) == 0

    text = (home / "review.diff").read_text()
    assert text.startswith(
        "# skill-graft Deployed diff: each Skill's text as deployed, Patches and"
        " Renames applied,\n"
    )
    assert "written by 0.3.0" not in text and "mp/tdd" in text


def edit_lock(change: Callable[[tomlkit.TOMLDocument], None]) -> None:
    file = paths.Scope(Path.home()).lock_file
    document = tomlkit.parse(file.read_text())
    change(document)
    file.write_text(tomlkit.dumps(document))


def test_lock_pointing_outside_the_copies(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    skills = paths.Scope(Path.home()).skills
    # Where a path joined from the lock would lead: the copy, as the lock hashes it.
    (skills / "tdd").rename(skills.parent.parent / "outside")
    edit_lock(lambda d: cast(Any, d["skills"])[0].update(deployed="../../outside"))

    assert hull_diff(capsys)[:2] == [
        "hull (+ added, - removed, ~ changed):",
        "+ mp/tdd",
    ]


def test_removed_id_quoted(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    scope = paths.Scope(Path.home())
    copy = skill(scope.skills / "x")
    item = {"id": "mp/x\n\x1b", "entry": False, "deployed": "x", "upstream": "x"}
    edit_lock(
        lambda d: cast(Any, d["skills"]).append(item | {"hash": lock.folder_hash(copy)})
    )

    assert hull_diff(capsys) == [
        "hull (+ added, - removed, ~ changed):",
        '- "mp/x\\n\\033"',
    ]
    before = review.vendored(scope.skills, lock.load(scope.lock_file))
    loaded = config.load(scope)
    with compute.compute_hull(scope, loaded, Cache.default()) as hull:
        hashes = lock.skill_hashes(hull)
        text = review.deployed_diff("", loaded, {}, before, hull, hashes, {}, [])
    assert text.splitlines() == ["#   mp/tdd", '# - "mp/x\\n\\033"']


def test_killed_run_reads_skills_old(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "1\n")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    skills = paths.Scope(Path.home()).skills
    # Swapped in, the lock not yet written: `skills.old` holds what it records.
    shutil.copytree(skills, skills.with_name("skills.old"))
    (skills / "tdd" / "SKILL.md").write_text("longer\n")
    skill(home / "mp" / "tdd", "22\n")

    assert hull_diff(capsys)[1:] == ["~ mp/tdd", "  SKILL.md (changed, 2 -> 3 bytes)"]


def test_resolve_dry_run_after_a_killed_run(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "1\n")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    skills = paths.Scope(Path.home()).skills
    shutil.copytree(skills, skills.with_name("skills.old"))
    (skills / "tdd" / "SKILL.md").write_text("longer\n")
    skill(home / "mp" / "tdd", "22\n")
    capsys.readouterr()

    assert main(["resolve", "--dry-run"]) == 0

    out = capsys.readouterr().out.splitlines()
    assert "  SKILL.md (changed, 2 -> 3 bytes)" in out  # not 7, the copy in skills/
