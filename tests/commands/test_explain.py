"""The `explain` spec: `why` and `tree` show the hull and write nothing."""

import base64
import json
import os
import re
import zlib
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import Upstream, configure, make_patch, skill, write_config

from skill_graft.cli import main
from skill_graft.commands import explain

Capsys: TypeAlias = pytest.CaptureFixture[str]


def lock_file(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / "skill-graft.lock"


def upstream(folder: Path) -> str:
    """`why`'s last line, naming the asked skill's upstream folder."""
    return f"upstream: {folder.resolve()}\n"


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
        '  subgraph s0["mp"]\n'
        '    n0["mp/tdd"]:::entry\n'
        '    n1["mp/grilling as mp-grilling"]\n'
        "  end\n"
        '  n0 -->|"/grilling"| n1\n'
        '  n0 -.->|"#96;grilling#96;, prose"| n1\n'
        "  classDef entry fill:#fde68a,stroke:#b45309,stroke-width:3px,color:#451a03\n"
    )


def test_mermaid_subgraphs_in_hull_order(home: Path, capsys: Capsys) -> None:
    skill(home / "a" / "x", "/y\n")
    skill(home / "b" / "y", "/z\n")
    skill(home / "a" / "z")
    configure(["a/x"], a="~/a", b="~/b")

    assert main(["tree", "--format", "mermaid"]) == 0

    assert capsys.readouterr().out == (
        "flowchart TD\n"
        '  subgraph s0["a"]\n'
        '    n0["a/x"]:::entry\n'
        '    n2["a/z"]\n'
        "  end\n"
        '  subgraph s1["b"]\n'
        '    n1["b/y"]\n'
        "  end\n"
        '  n0 -->|"/y"| n1\n'
        '  n1 -->|"/z"| n2\n'
        "  classDef entry fill:#fde68a,stroke:#b45309,stroke-width:3px,color:#451a03\n"
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
    assert len(labels) == 7  # a subgraph title, three nodes, three arrows
    for label in (a or b for a, b in labels):
        assert label.startswith('"') and label.endswith('"'), label
        assert "`" not in label and '"' not in label[1:-1], label


def test_mermaid_has_no_source_links(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    upstream = Upstream(tmp_path / "upstream")
    sha = upstream.commit({"tdd/SKILL.md": "/notes\n"})
    skill(home / "own" / "notes")
    url = "https://user:secret@example.com/mp.git?private_token=t0k3n"
    Path(os.environ["GIT_CONFIG_GLOBAL"]).write_text(
        f'[url "{upstream.url}"]\n\tinsteadOf = {url}\n'
    )
    write_config(
        'entries = ["mp/tdd"]\n'
        f'[sources.mp]\ngit = "{url}"\nref = "{sha}"\n'
        '[sources.own]\npath = "~/own"\n'
    )

    assert main(["tree", "--format", "mermaid"]) == 0
    first = capsys.readouterr().out
    assert main(["tree", "--format", "mermaid"]) == 0

    assert 'subgraph s0["mp"]\n' in first and 'subgraph s1["own"]\n' in first
    assert "own/notes" in first
    for text in ["<a", "click", "://", "user", "secret", "example.com", "t0k3n"]:
        assert text not in first, text
    assert capsys.readouterr().out == first


def test_mermaid_link_decodes_to_the_diagram(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["tree", "--format", "mermaid"]) == 0
    diagram = capsys.readouterr().out

    assert main(["tree", "--format", "mermaid", "--link"]) == 0

    out = capsys.readouterr().out
    prefix = "https://mermaid.live/edit#pako:"
    assert out.startswith(prefix) and out.endswith("\n") and out.count("\n") == 1
    data = out[len(prefix) : -1]
    assert "=" not in data  # url-safe base64, unpadded, as js-base64 writes it
    state = json.loads(zlib.decompress(base64.urlsafe_b64decode(data + "==")))
    assert state["code"] == diagram
    assert json.loads(state["mermaid"]) == {"theme": "default"}


def test_link_needs_mermaid(home: Path, capsys: Capsys) -> None:
    with pytest.raises(SystemExit) as exit:
        main(["tree", "--link"])

    assert exit.value.code == 2
    err = capsys.readouterr().err
    assert "--link" in err and "--format mermaid" in err


def test_why_two_paths(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, then /implement\n")
    skill(home / "mp" / "implement", "Skill(grilling)\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["why", "mp/grilling"]) == 0

    assert capsys.readouterr().out == (
        "mp/grilling\n"
        "├─← mp/tdd (/grilling) (entry)\n"
        "└─← mp/implement (Skill(grilling))\n"
        "    └─← mp/tdd (/implement) (entry)\n"
    ) + upstream(home / "mp" / "grilling")


def test_why_repeated_skill(home: Path, capsys: Capsys) -> None:
    for name in ("a", "b"):
        skill(home / "mp" / name, "/mid\n")
    skill(home / "mp" / "mid", "/x and /y\n")
    for name in ("x", "y"):
        skill(home / "mp" / name, "/leaf\n")
    skill(home / "mp" / "leaf")
    configure(["mp/a", "mp/b"], mp="~/mp")

    assert main(["why", "mp/leaf"]) == 0

    assert capsys.readouterr().out == (
        "mp/leaf\n"
        "├─← mp/x (/leaf)\n"
        "│   └─← mp/mid (/x)\n"
        "│       ├─← mp/a (/mid) (entry)\n"
        "│       └─← mp/b (/mid) (entry)\n"
        "└─← mp/y (/leaf)\n"
        "    └─← mp/mid (/y) (*)\n"
    ) + upstream(home / "mp" / "leaf")


def test_why_an_entry(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling", "/tdd\n")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["why", "mp/tdd"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd (entry)\n└─← mp/grilling (/tdd)\n    └─← mp/tdd (/grilling) (entry)\n"
    ) + upstream(home / "mp" / "tdd")


def test_why_renamed_patched_and_bound(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "mp" / "tdd", "/notes\n")
    skill(home / "own" / "notes")
    patches = home / ".apm" / "skill-graft" / "patches"
    patches.mkdir(parents=True)
    (patches / "tdd.patch").write_bytes(
        make_patch(tmp_path, {"SKILL.md": "/notes\n"}, {"SKILL.md": "/notes\nmore\n"})
    )
    write_config(
        'entries = ["mp/tdd"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.own]\npath = "~/own"\n'
        '[rename]\n"mp/tdd" = "mp-tdd"\n'
        '[bind]\n"mp/notes" = "own/notes"\n'
        '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )

    assert main(["why", "own/notes"]) == 0

    assert capsys.readouterr().out == (
        "own/notes\n└─← mp/tdd as mp-tdd (patched) (/notes, bind) (entry)\n"
    ) + upstream(home / "own" / "notes")


def test_why_leaves_prose_out(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, see `grilling`\n")
    skill(home / "mp" / "grilling")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/grilling" = "mp-grilling"\n'  # so the prose edge is shown in tree
    )

    assert main(["why", "mp/grilling"]) == 0

    assert capsys.readouterr().out == (
        "mp/grilling as mp-grilling\n└─← mp/tdd (/grilling) (entry)\n"
    ) + upstream(home / "mp" / "grilling")


def test_why_by_deployed_name(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/code-review and /grilling\n")
    skill(home / "mp" / "code-review")
    skill(home / "mp" / "grilling")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/code-review" = "mp-code-review"\n'
    )

    assert main(["why", "mp-code-review"]) == 0
    assert capsys.readouterr().out == (
        "mp/code-review as mp-code-review\n└─← mp/tdd (/code-review) (entry)\n"
    ) + upstream(home / "mp" / "code-review")
    assert main(["why", "grilling"]) == 0
    assert capsys.readouterr().out == (
        "mp/grilling\n└─← mp/tdd (/grilling) (entry)\n"
        + upstream(home / "mp" / "grilling")
    )


def why_fails(argv: list[str], capsys: Capsys) -> str:
    """Runs `why`, which must fail with nothing on stdout; returns stderr."""
    assert main(argv) == 1
    out, err = capsys.readouterr()
    assert out == ""
    return err


def test_why_upstream_name_of_a_renamed_skill(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/code-review\n")
    skill(home / "mp" / "code-review")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/code-review" = "mp-code-review"\n'
    )

    err = why_fails(["why", "code-review"], capsys)

    assert "mp/code-review" in err and "mp-code-review" in err


def test_why_outside_the_hull_mentioned_in_prose(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "then diagnosing-bugs\n")
    skill(home / "mp" / "diagnosing-bugs")
    configure(["mp/tdd"], mp="~/mp")

    for argv in (["why", "mp/diagnosing-bugs"], ["why", "diagnosing-bugs"]):
        err = why_fails(argv, capsys)

        assert "`mp/diagnosing-bugs` is not in the hull" in err
        assert "mp/tdd" in err
        assert "skill-graft add mp/diagnosing-bugs" in err


def test_why_outside_the_hull_not_mentioned(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes")
    configure(["mp/tdd"], mp="~/mp")

    err = why_fails(["why", "mp/notes"], capsys)

    assert "`mp/notes` is not in the hull: `skill-graft add mp/notes`" in err


def test_why_unknown(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")

    for argv in (["why", "mp/nope"], ["why", "nope"]):
        err = why_fails(argv, capsys)

        assert "nope" in err
        assert "skill-graft add" not in err


def test_why_undeclared_alias(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")

    err = why_fails(["why", "zz/tdd"], capsys)

    assert "no source 'zz' is declared" in err


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

    assert main(["why", "own/b"]) == 0

    assert capsys.readouterr().out == "own/b (entry)\n" + upstream(home / "own" / "b")
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


def test_why_names_a_path_sources_upstream_folder(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "chisel")
    configure(["own/chisel"], own="~/src")

    assert main(["why", "own/chisel"]) == 0

    out = capsys.readouterr().out
    assert out.splitlines()[-1] == f"upstream: {(home / 'src' / 'chisel').resolve()}"


def test_why_names_a_remote_sources_upstream_folder(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit(
        {"skills/tdd/SKILL.md": "---\nname: tdd\n---\nupstream text\n"}
    )
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )

    assert main(["why", "mp/tdd"]) == 0

    line = capsys.readouterr().out.splitlines()[-1]
    folder = Path(line.removeprefix("upstream: "))
    assert line.startswith("upstream: ") and folder.is_absolute()
    assert (folder / "SKILL.md").read_text().endswith("upstream text\n")


@pytest.mark.parametrize(
    ("url", "repository"),
    [
        ("https://github.com/o/r.git", "https://github.com/o/r"),
        ("https://github.com/o/r/", "https://github.com/o/r"),
        ("http://GitHub.com/o/r", "https://github.com/o/r"),
        ("git://github.com/o/r.git", "https://github.com/o/r"),
        ("ssh://git@github.com/o/r.git", "https://github.com/o/r"),
        ("ssh://git@github.com:22/o/r.git", "https://github.com/o/r"),
        ("git@github.com:o/r.git", "https://github.com/o/r"),
        ("github.com:o/r", "https://github.com/o/r"),
        ("https://user:secret@github.com/o/r.git", "https://github.com/o/r"),
        ("git@gitlab.com:g/sub/r.git", "https://gitlab.com/g/sub/r"),
        ("https://oauth2:secret@gitlab.com/g/r", "https://gitlab.com/g/r"),
        ("HTTPS://GITHUB.COM/o/r", "https://github.com/o/r"),
        ("https://github.com:443/o/r", "https://github.com/o/r"),
        ("https://github.com/o/r.git.git", "https://github.com/o/r.git"),
        ("https://github.com@evil.example/o/r", None),
        ("https://evil.example/github.com/o/r", None),
        ("https://github.com.evil.example/o/r", None),
        ("https://www.github.com/o/r", None),
        ("https://github.com/o", None),
        ("https://github.com/o/r/x", None),
        ("https://gitlab.com/g", None),
        ("https://github.com/o/r?private_token=t", None),
        ("https://github.com/o/r#x", None),
        ("https://github.com/o/%72", None),
        ("https://github.com/o/../r", None),
        ("https://github.com//o/r", None),
        ("https://github.com/o/r.git/x", None),
        ("git@github.com:~o/r", None),
        ("git@github.com:/o/r", None),
        ("file:///srv/github.com/o/r", None),
        ("/srv/github.com/o/r", None),
        ("user:tok@github.com:o/r", None),
        ("https://git\thub.com/o/r", None),
        ("https://github.com/o/r//", None),
        ("https://github.com/o/r?", None),
        ("https://github.com/o/r#", None),
        ("ssh://git@github.com:o/r", None),
        ("https://github.com/o/r x", None),
        ("https://github.com/o/r\n", None),
        ("https://github.com/o/r\x00", None),
    ],
)
def test_repository(url: str, repository: str | None) -> None:
    assert explain.repository(url) == repository
