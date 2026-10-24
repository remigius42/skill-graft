"""A skill as deployed, its summary and its diff (the `update` spec)."""

from pathlib import Path

from conftest import skill

from skill_graft.pipeline import deployed


def test_files_with_bytes_and_bit(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# tdd\n")
    (folder / "bin").mkdir()
    (folder / "bin" / "run.sh").write_bytes(b"echo\n")
    (folder / "bin" / "run.sh").chmod(0o755)

    assert deployed.deployed_files(folder, {}) == {
        "SKILL.md": (b"# tdd\n", False),
        "bin/run.sh": (b"echo\n", True),
    }


def test_override_replaces_bytes(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# tdd\n")

    view = deployed.deployed_files(folder, {Path("SKILL.md"): b"# renamed\n"})

    assert view == {"SKILL.md": (b"# renamed\n", False)}


def test_symlink_followed_and_git_skipped(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# tdd\n")
    (folder / "link.md").symlink_to("SKILL.md")
    (folder / ".git").write_text("gitdir: elsewhere\n")

    view = deployed.deployed_files(folder, {})

    assert view == {"SKILL.md": (b"# tdd\n", False), "link.md": (b"# tdd\n", False)}
