"""Finding slash and Skill tool references in a skill's Markdown (the `hull` spec)."""

from pathlib import Path

import pytest
from conftest import skill

from skill_graft import references
from skill_graft.errors import SkillGraftError


def found(folder: Path) -> list[str]:
    """The references in `folder`, as written."""
    refs, _ = references.scan(folder)
    return [ref.text for ref in refs]


@pytest.mark.parametrize(
    "text",
    ["run /grilling.", "`/grilling`", "(/grilling)", "**/grilling**", "/grilling"],
)
def test_standalone_token(tmp_path: Path, text: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    refs, _ = references.scan(folder)

    assert [(r.name, r.kind) for r in refs] == [("grilling", "slash")]


@pytest.mark.parametrize(
    "text",
    [
        "/usr/bin",
        "src/grilling",
        "https://x.org/grilling",
        "~/grilling",
        "</grilling>",
        "/plugin:grilling",
        "/my-dir/file",
        "cd /tmp.d/x",
        "and/or",
        "1/2",
    ],
)
def test_paths_and_urls(tmp_path: Path, text: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    assert found(folder) == []


@pytest.mark.parametrize(
    "text",
    [
        "Skill(grilling)",
        'Skill("grilling")',
        "Skill( 'grilling' )",
        'Skill(skill: "grilling")',
        "Skill(skill=grilling)",
        'Skill(skill: "grilling", args: "x")',
    ],
)
def test_call_forms(tmp_path: Path, text: str) -> None:
    folder = skill(tmp_path / "tdd", f"Use {text} now.\n")

    refs, _ = references.scan(folder)

    assert [(r.name, r.kind, r.text) for r in refs] == [
        ("grilling", "skill-tool", "Skill(grilling)")
    ]


@pytest.mark.parametrize("text", ['Skill("grilling)', "MySkill(grilling)"])
def test_not_a_call(tmp_path: Path, text: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    assert found(folder) == []


def test_references_in_text_order(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "Skill(a) then /b, then Skill(c)\n")

    assert found(folder) == ["Skill(a)", "/b", "Skill(c)"]


def test_case_is_kept(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "/Grilling and Skill(TDD)\n")

    assert found(folder) == ["/Grilling", "Skill(TDD)"]


def test_every_markdown_file(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "/c\n")
    (folder / "refs").mkdir()
    (folder / "refs" / "loop.md").write_text("/b\n")
    (folder / "a.MD").write_text("/a\n")
    (folder / "script.sh").write_text("/nope\n")
    (folder / ".git").mkdir()
    (folder / ".git" / "x.md").write_text("/nope\n")

    refs, _ = references.scan(folder)

    assert [(r.text, r.file.relative_to(folder).as_posix()) for r in refs] == [
        ("/c", "SKILL.md"),
        ("/a", "a.MD"),
        ("/b", "refs/loop.md"),
    ]


def test_not_utf8_is_skipped_with_a_warning(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "/a\n")
    (folder / "notes.md").write_bytes(b"/b \xff\n")

    refs, warnings = references.scan(folder)

    assert [r.text for r in refs] == ["/a"]
    assert len(warnings) == 1 and "notes.md" in warnings[0]


def test_dangling_link_is_an_error(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd")
    (folder / "notes.md").symlink_to("gone.md")

    with pytest.raises(SkillGraftError, match="notes.md"):
        references.scan(folder)
