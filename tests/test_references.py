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
    [
        "run /grilling.",
        "`/grilling`",
        "(/grilling)",
        "(`/grilling`)",
        "run '/grilling'",
        "**/grilling**",
        "/grilling",
    ],
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
        "see [docs](/docs)",
        '<a href="/about">',
        "<a href='/about'>",
        'from "@/utils"',
    ],
)
def test_paths_and_urls(tmp_path: Path, text: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    assert found(folder) == []


@pytest.mark.parametrize(
    "text",
    [
        "fetch('/orders')",
        'open("/grilling")',
        '["/a"]',
        "fetch(`/users/${userId}/orders`)",
        "its `package.json`/build-tool scripts",
        "`lint`/check",
    ],
)
def test_path_arguments_and_after_a_code_span(tmp_path: Path, text: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    refs, _ = references.scan(folder)

    assert [r.text for r in refs if r.kind == "slash"] == []


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


@pytest.mark.parametrize(
    ("text", "written"),
    [
        ("use `grilling` now", "`grilling`"),
        ("then diagnosing-bugs.", "diagnosing-bugs"),
        ("```bash\npre-commit run\n```", "pre-commit"),
    ],
)
def test_prose(tmp_path: Path, text: str, written: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    refs, _ = references.scan(folder)

    assert [(r.name, r.kind, r.text) for r in refs] == [
        (written.strip("`"), "prose", written)
    ]


@pytest.mark.parametrize(
    "text",
    [
        "grilling",
        "`grilling --fast`",
        "`mp/grilling`",
        "--dry-run",
        "refs/red-green.md",
        "x-ray.png",
        "[see](my-skill)",
        "[x](#my-skill)",
        "[x](other.md#my-skill)",
        '<a id="my-skill">',
        "foo_my-skill",
        "https://x.org/docs?q=my-skill",
        "x=my-skill",
        "a&b=my-skill",
        "$my-skill",
        "allowed-tools: Bash",
        "  argument-hint: x",
        "my-skill%20x",
        "my-skill+x",
        "My-Skill",
        "https://x.org/my-skill",
    ],
)
def test_not_prose(tmp_path: Path, text: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    assert found(folder) == []


@pytest.mark.parametrize(
    ("text", "written"),
    [
        ("`/grilling`", "/grilling"),
        ("Skill(diagnosing-bugs)", "Skill(diagnosing-bugs)"),
        ('Skill(skill: "grilling", args: "diagnosing-bugs")', "Skill(grilling)"),
        ("Skill(grilling, `notes` and x-y)", "Skill(grilling)"),
    ],
)
def test_slash_form_wins(tmp_path: Path, text: str, written: str) -> None:
    folder = skill(tmp_path / "tdd", f"{text}\n")

    assert found(folder) == [written]


def test_span_is_the_name_alone(tmp_path: Path) -> None:
    text = "Run /grilling. Then Skill('notes', x) and `tdd`, or diagnosing-bugs...\n"
    folder = skill(tmp_path / "tdd", text)

    refs, _ = references.scan(folder)

    assert [text[slice(*r.span)] for r in refs] == [
        "grilling",
        "notes",
        "tdd",
        "diagnosing-bugs",
    ]


@pytest.mark.parametrize("line", ["name: code-review", 'name: "code-review" # x'])
def test_own_name_line(tmp_path: Path, line: str) -> None:
    folder = skill(
        tmp_path / "code-review",
        f"---\n{line}\ndescription: before code-review\n---\nsee code-review\n",
    )
    (folder / "notes.md").write_text(f"---\n{line}\n---\n")

    refs, _ = references.scan(folder)

    assert [(r.file.name, r.span[0]) for r in refs] == [
        ("SKILL.md", len(f"---\n{line}\ndescription: before ")),
        ("SKILL.md", len(f"---\n{line}\ndescription: before code-review\n---\nsee ")),
        ("notes.md", 4 + line.index("code-review")),
    ]


def kinds(text: str, tmp_path: Path) -> list[tuple[str, str]]:
    """Each reference in a skill holding `text`: its name and kind."""
    refs, _ = references.scan(skill(tmp_path / "tdd", text))
    return [(r.name, r.kind) for r in refs]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            'Call the Skill tool twice, for "grilling" and "domain-modeling".\n',
            [("grilling", "skill-tool"), ("domain-modeling", "skill-tool")],
        ),
        (
            "Call the Skill tool with `writing-for-agents` for the style guide.\n",
            [("writing-for-agents", "skill-tool")],
        ),
        (
            'call the Skill tool with\n"codebase-design" for the vocabulary.\n',
            [("codebase-design", "skill-tool")],
        ),
        (
            'Call the Skill tool, e.g. with "grilling" or "domain-modeling."\n',
            [("grilling", "skill-tool"), ("domain-modeling", "skill-tool")],
        ),
        (
            "Call the Skill tool, e.g. `grilling`.\n",
            [("grilling", "skill-tool")],
        ),
    ],
)
def test_sentence_form(
    tmp_path: Path, text: str, expected: list[tuple[str, str]]
) -> None:
    assert kinds(text, tmp_path) == expected


@pytest.mark.parametrize(
    "text",
    [
        'Use the Skill tool. Then see "grilling" and `notes`.\n',
        "Use the Skill tool for this\n- `notes`\n",
        "Use the Skill tool for this\n\n`notes`\n",
        "Use the Skill tool for this\n# `notes`\n",
        "Use the Skill tool. `notes` holds them.\n",
        "**Use the Skill tool.** Then see `notes`.\n",
        "(Use the Skill tool.) Then `notes`.\n",
        'Use the Skill tool. "Hello" he said, `notes`.\n',
        'Use the Skill tool:\n```json\n{"skill": "x"}\n```\n`notes`\n',
        'Use the Skill tool:\n| "x" |\n\n`notes`\n',
    ],
)
def test_sentence_ends(tmp_path: Path, text: str) -> None:
    assert kinds(text, tmp_path) == [("notes", "prose")]


@pytest.mark.parametrize(
    "text",
    [
        'If the Skill tool fails, call the Skill tool again with "grilling".\n',
        'Call the Skill tool: Skill("grilling").\n',
    ],
)
def test_one_reference_per_name(tmp_path: Path, text: str) -> None:
    assert kinds(text, tmp_path) == [("grilling", "skill-tool")]


def test_unquoted_name(tmp_path: Path) -> None:
    assert kinds("call the Skill tool with grilling.\n", tmp_path) == []


def test_sentence_text_and_order(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", '/a first.\n\nCall the Skill tool with "b".\n')

    assert found(folder) == ["/a", 'Skill tool "b"']


@pytest.mark.parametrize(
    "text",
    [
        'Run "/tdd", "/grilling" in order.\n',
        "运行`/tdd`和`/grilling`\n",
        "step1`/tdd` `/grilling`\n",
        "Run ``/tdd`` and ``/grilling`` now\n",
    ],
)
def test_commands_in_lists_and_without_spaces(tmp_path: Path, text: str) -> None:
    assert kinds(text, tmp_path) == [("tdd", "slash"), ("grilling", "slash")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('Use the `Skill` tool with "grilling".\n', [("grilling", "skill-tool")]),
        ('MySkill tool with "grilling".\n', []),
        ('Skill tooling with "grilling".\n', []),
        (
            'Use the Skill tool with "a-b" or the `Skill` tool with "c-d".\n',
            [("a-b", "skill-tool"), ("c-d", "skill-tool")],
        ),
    ],
)
def test_skill_tool_words(
    tmp_path: Path, text: str, expected: list[tuple[str, str]]
) -> None:
    assert kinds(text, tmp_path) == expected


def test_sentence_skips_the_own_name_line(tmp_path: Path) -> None:
    text = '---\ndescription: via the Skill tool\nname: "tdd"\n---\n'

    assert kinds(text, tmp_path) == []
