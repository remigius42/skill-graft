"""A skill as deployed, its summary and its diff (the `update` spec)."""

import os
import subprocess
from pathlib import Path

import pytest
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


NAMES = [
    "x\n",
    "a\tb",
    'say "hi"',
    "back\\slash",
    "caf\u00e9",
    "SKILL.md\u200b",
    "a\u2028b",
]


@pytest.mark.parametrize("name", NAMES)
def test_quote_as_git_does(tmp_path: Path, name: str) -> None:
    (tmp_path / name).write_text("x\n")
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    result = subprocess.run(
        ["git", "diff", "--no-index", "--", "/dev/null", name],
        cwd=tmp_path,
        capture_output=True,
        env=env,
    )
    # git ends a `+++` name holding a space with a tab; quoted, it needs none.
    headers = [line.rstrip("\t") for line in result.stdout.decode().split("\n")]

    old, new = deployed.quote(name, "a/"), deployed.quote(name, "b/")
    assert headers[0] == f"diff --git {old} {new}"
    assert f"+++ {new}" in headers


def test_quote_plain_name() -> None:
    assert deployed.quote("skills/run.sh", "b/") == "b/skills/run.sh"


def test_quote_trailing_space_unlike_git() -> None:
    assert deployed.quote("run.sh ") == '"run.sh "'
    assert deployed.quote("run.sh ", "a/") == '"a/run.sh "'


def test_quote_other_control_and_non_ascii_as_octal() -> None:
    assert deployed.quote("a\x01\x7f\u00e9") == '"a\\001\\177\\303\\251"'


def test_summary_file_lines() -> None:
    old = {"SKILL.md": (b"x" * 120, False)}
    new = {"SKILL.md": (b"x" * 180, False), "run.sh": (b"y" * 40, True)}

    assert deployed.summary(old, new) == [
        "SKILL.md (changed, 120 -> 180 bytes)",
        "run.sh (new, 40 bytes) (now executable)",
    ]


def test_summary_removed_and_unchanged() -> None:
    old = {"SKILL.md": (b"same", False), "old.md": (b"gone", True)}
    new = {"SKILL.md": (b"same", False)}

    assert deployed.summary(old, new) == ["old.md (removed)"]


def test_summary_made_executable() -> None:
    old = {"run.sh": (b"y" * 40, False)}
    new = {"run.sh": (b"y" * 40, True)}

    assert deployed.summary(old, new) == [
        "run.sh (changed, 40 -> 40 bytes) (now executable)"
    ]


def test_summary_no_longer_executable() -> None:
    old = {"run.sh": (b"a", True)}
    new = {"run.sh": (b"b", False)}

    assert deployed.summary(old, new) == [
        "run.sh (changed, 1 -> 1 bytes) (no longer executable)"
    ]


def test_summary_many_files() -> None:
    new = {f"f{i:02}.md": (b"x", False) for i in range(50)}

    lines = deployed.summary({}, new)

    assert lines[:2] == ["f00.md (new, 1 bytes)", "f01.md (new, 1 bytes)"]
    assert len(lines) == 21
    assert lines[20] == "\u2026 30 more"


def test_summary_lookalike_names() -> None:
    old = {"SKILL.md": (b"x", False)}
    new = {"SKILL.md": (b"y", False), "SKILL.md\u200b": (b"z", False)}

    assert deployed.summary(old, new) == [
        "SKILL.md (changed, 1 -> 1 bytes)",
        '"SKILL.md\\342\\200\\213" (new, 1 bytes)',
    ]


def test_summary_trailing_space() -> None:
    new = {"run.sh": (b"x", False), "run.sh ": (b"x", False)}

    assert deployed.summary({}, new) == [
        "run.sh (new, 1 bytes)",
        '"run.sh " (new, 1 bytes)',
    ]
