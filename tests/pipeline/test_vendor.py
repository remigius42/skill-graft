"""Vendoring's steps: staging `skills.new`, the swap and its undo, and recovering a
run killed mid-swap."""

from pathlib import Path

import pytest
from conftest import configure, skill

from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import compute, config, vendor


def folders(tmp_path: Path, **names: str) -> Path:
    """`skills` beside the `skills.<suffix>` folders `names` gives, each holding
    one skill named by its value; returns `skills`."""
    skills = tmp_path / ".apm" / "skills"
    for suffix, name in names.items():
        skill(
            skills.with_name("skills" if suffix == "current" else f"skills.{suffix}")
            / name
        )
    return skills


def held(folder: Path) -> list[str] | None:
    """The names in `folder`, `None` if it is missing."""
    return sorted(p.name for p in folder.iterdir()) if folder.exists() else None


def test_stage_writes_skills_new(home: Path, tmp_path: Path) -> None:
    skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    scope = paths.Scope(home)
    skills = tmp_path / ".apm" / "skills"

    with compute.compute_hull(scope, config.load(scope), Cache.default()) as hull:
        vendor.stage(hull, skills)

    assert held(skills.with_name("skills.new")) == ["tdd"]
    assert held(skills) is None


@pytest.mark.needs_permissions
def test_copy_error_reported_over_the_cleanup_one(home: Path, tmp_path: Path) -> None:
    folder = skill(home / "own" / "tdd")
    (folder / "ro").mkdir()
    (folder / "ro" / "a.md").write_text("x\n")
    (folder / "ro" / "b.md").write_text("x\n")  # copied: held in a read-only folder
    configure(["own/tdd"], own="~/own")
    scope = paths.Scope(home)
    skills = tmp_path / ".apm" / "skills"

    with compute.compute_hull(scope, config.load(scope), Cache.default()) as hull:
        # Unreadable once walked: the copy fails, and keeps `ro`'s mode, so
        # the cleanup cannot delete the partial copy inside it either.
        (folder / "ro" / "a.md").chmod(0)
        (folder / "ro").chmod(0o555)
        try:
            with pytest.raises(SkillGraftError, match="copying .* failed"):
                vendor.stage(hull, skills)
        finally:
            for ro in [folder / "ro", skills.with_name("skills.new") / "tdd" / "ro"]:
                if ro.exists():
                    ro.chmod(0o755)
            (folder / "ro" / "a.md").chmod(0o644)


def test_swap_back_restores_previous(tmp_path: Path) -> None:
    skills = folders(tmp_path, current="a", new="b")
    vendor.swap(skills)
    assert held(skills) == ["b"]

    vendor.swap_back(skills)

    assert held(skills) == ["a"]
    assert held(skills.with_name("skills.new")) is None
    assert held(skills.with_name("skills.old")) is None


def test_swap_back_without_previous(tmp_path: Path) -> None:
    skills = folders(tmp_path, new="b")
    vendor.swap(skills)
    assert held(skills) == ["b"]

    vendor.swap_back(skills)

    assert not skills.parent.joinpath("skills").exists()
    assert held(skills.with_name("skills.new")) is None


def test_clear_old_removes_previous(tmp_path: Path) -> None:
    skills = folders(tmp_path, current="a", new="b")
    vendor.swap(skills)

    vendor.clear_old(skills)

    assert held(skills) == ["b"]
    assert held(skills.with_name("skills.old")) is None


def test_pending_touches_nothing(tmp_path: Path) -> None:
    skills = folders(tmp_path, current="a", old="b", new="c")
    old = skills.with_name("skills.old")
    seen: list[Path] = []

    def keep(folder: Path) -> bool:
        seen.append(folder)
        return True

    assert vendor.pending(skills, keep) == old
    assert vendor.pending(skills, lambda _: False) == skills
    assert seen == [old]
    assert [held(skills), held(old), held(skills.with_name("skills.new"))] == [
        ["a"],
        ["b"],
        ["c"],
    ]


def test_recover_lone_old(tmp_path: Path) -> None:
    skills = folders(tmp_path, old="b")
    assert vendor.pending(skills, lambda _: False) == skills.with_name("skills.old")

    vendor.recover(skills, lambda _: False)

    assert held(skills) == ["b"]
    assert held(skills.with_name("skills.old")) is None


def test_recover_keeps_old_that_matches(tmp_path: Path) -> None:
    skills = folders(tmp_path, current="a", old="b")

    vendor.recover(skills, lambda _: True)

    assert held(skills) == ["b"]
    assert held(skills.with_name("skills.old")) is None


def test_recover_drops_old_that_does_not(tmp_path: Path) -> None:
    skills = folders(tmp_path, current="a", old="b")

    vendor.recover(skills, lambda _: False)

    assert held(skills) == ["a"]
    assert held(skills.with_name("skills.old")) is None


def test_recover_drops_new(tmp_path: Path) -> None:
    skills = folders(tmp_path, current="a", new="c")

    vendor.recover(skills, lambda _: False)

    assert held(skills) == ["a"]
    assert held(skills.with_name("skills.new")) is None


def test_clear_old_leaves_nothing_recover_takes_back(tmp_path: Path) -> None:
    skills = folders(tmp_path, current="a", trash="b")

    vendor.recover(skills, lambda _: True)

    assert held(skills) == ["a"]
    assert held(skills.with_name("skills.trash")) is None
