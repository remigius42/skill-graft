"""The `explain` spec: `why` and `tree` show the hull and write nothing."""

import re
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import Upstream, configure, make_patch, skill, write_config

from skill_graft.cli import main

Capsys: TypeAlias = pytest.CaptureFixture[str]


def lock_file(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / "skill-graft.lock"


def test_tree_is_resolves_tree(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, then diagnosing-bugs\n")
    skill(home / "mp" / "grilling", "/notes\n")
    skill(home / "mp" / "notes")
    skill(home / "mp" / "diagnosing-bugs")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    resolved = capsys.readouterr().out

    assert main(["tree"]) == 0

    tree = capsys.readouterr().out
    assert tree == ("mp/tdd\n└── mp/grilling (/grilling)\n    └── mp/notes (/notes)\n")
    assert resolved.startswith(tree + "\nmentioned in prose")


def test_mermaid_diagram(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, see `grilling`\n")
    skill(home / "mp" / "grilling")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/grilling" = "mp-grilling"\n'
    )

    assert main(["tree", "--format", "mermaid"]) == 0

    assert capsys.readouterr().out == (
        "flowchart TD\n"
        '  n0["mp/tdd"]:::entry\n'
        '  n1["mp/grilling as mp-grilling"]\n'
        '  n0 -->|"/grilling"| n1\n'
        '  n0 -.->|"#96;grilling#96;, prose"| n1\n'
        "  classDef entry stroke-width:3px\n"
    )


def test_mermaid_labels_quoted(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", 'Skill(skill="grilling"), /notes, see `notes`\n')
    skill(home / "mp" / "grilling")
    skill(home / "mp" / "notes")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/notes" = "n"\n'
    )

    assert main(["tree", "--format", "mermaid"]) == 0

    out = capsys.readouterr().out
    labels = re.findall(r"\[(.*?)\]|\|(.*?)\|", out)
    assert len(labels) == 6  # three nodes, three arrows
    for label in (a or b for a, b in labels):
        assert label.startswith('"') and label.endswith('"'), label
        assert "`" not in label and '"' not in label[1:-1], label


def test_mermaid_has_no_source_links(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    upstream = Upstream(tmp_path / "upstream")
    sha = upstream.commit({"tdd/SKILL.md": "/notes\n"})
    skill(home / "own" / "notes")
    write_config(
        'entries = ["mp/tdd"]\n'
        f'[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
        '[sources.own]\npath = "~/own"\n'
    )

    assert main(["tree", "--format", "mermaid"]) == 0
    first = capsys.readouterr().out
    assert main(["tree", "--format", "mermaid"]) == 0

    assert "own/notes" in first
    assert "click" not in first and "://" not in first
    assert capsys.readouterr().out == first


def test_tree_writes_no_lock(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["tree"]) == 0

    assert capsys.readouterr().out == "mp/tdd\n"
    assert not lock_file(home).exists()


def test_stale_lock_left_alone(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "b")
    configure(["mp/tdd"], mp="~/mp", own="~/own")
    assert main(["resolve"]) == 0
    before = lock_file(home).read_bytes()
    configure(["mp/tdd", "own/b"], mp="~/mp", own="~/own")
    capsys.readouterr()

    assert main(["tree"]) == 0

    assert capsys.readouterr().out == "mp/tdd\nown/b\n"
    assert lock_file(home).read_bytes() == before


def test_tree_fails_on_a_failing_patch(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "mp" / "tdd", "# changed\n")
    patches = home / ".apm" / "skill-graft" / "patches"
    patches.mkdir(parents=True)
    (patches / "tdd.patch").write_bytes(
        make_patch(tmp_path, {"SKILL.md": "# x\n"}, {"SKILL.md": "# x\nmore\n"})
    )
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )

    assert main(["tree"]) == 1

    out, err = capsys.readouterr()
    assert out == ""
    assert "patches/tdd.patch: SKILL.md: hunk" in err
