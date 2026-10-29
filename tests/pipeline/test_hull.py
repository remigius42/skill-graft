"""The `hull` spec, through `skill-graft build --no-install`."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import (
    after_package_line,
    build,
    configure,
    skill,
    vendored,
    write_config,
    write_patch,
)

from skill_graft.cli import main
from skill_graft.infra import paths
from skill_graft.pipeline import compute, config
from skill_graft.pipeline.config import SkillId
from skill_graft.pipeline.hull import Hull

Capsys: TypeAlias = pytest.CaptureFixture[str]


def test_reference_pulls_in_a_skill(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "Run /grilling first.\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "grilling"}


def two_sources(home: Path, tdd: str, **extra: str) -> None:
    """Entry `mp/tdd` holding `tdd`, sources `mp` and `own`, plus `extra` ones."""
    skill(home / "mp" / "tdd", tdd)
    (home / "own").mkdir(exist_ok=True)
    for alias in extra:
        (home / alias).mkdir(exist_ok=True)
    configure(["mp/tdd"], mp="~/mp", own="~/own", **extra)


def test_own_source_wins(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling", "mp\n")
    skill(home / "own" / "grilling", "own\n")
    two_sources(home, "/grilling\n")

    assert build(capsys) == (0, "")
    assert (vendored_dir(home) / "grilling" / "SKILL.md").read_text() == "mp\n"


def test_one_other_source(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "notes")
    two_sources(home, "/notes\n")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "notes"}


def test_several_other_sources(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "notes")
    skill(home / "x" / "notes")
    two_sources(home, "/notes\n", x="~/x")

    code, err = build(capsys)

    assert code == 1
    for text in ["mp/tdd", "/notes", "own/notes", "x/notes"]:
        assert text in err
    assert "skill-graft bind mp/notes <source>/<name>" in err
    assert vendored() == set()


def test_no_such_skill(home: Path, capsys: Capsys) -> None:
    two_sources(home, "/foo and again /foo\n")

    code, err = build(capsys)

    assert code == 0 and vendored() == {"tdd"}
    warning = "`mp/tdd` calls `/foo`: no declared source has a skill `foo`"
    assert err.count(warning) == 1
    assert "skill-graft bind mp/foo false" in err


def test_skill_tool_form_named(home: Path, capsys: Capsys) -> None:
    two_sources(home, "Skill(foo)\n")

    _, err = build(capsys)

    assert "`mp/tdd` calls `Skill(foo)`" in err


def test_different_case(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "grilling")
    two_sources(home, "/Grilling\n")

    code, err = build(capsys)

    assert code == 0 and vendored() == {"tdd"}
    assert "no declared source has a skill `Grilling`" in err


def test_invalid_name_does_not_count(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling", '---\nname: "Grilling Tool"\n---\n')
    skill(home / "own" / "grilling", "own\n")
    two_sources(home, "/grilling\n")

    assert build(capsys) == (0, "")
    assert (vendored_dir(home) / "grilling" / "SKILL.md").read_text() == "own\n"


def test_two_hops(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling", "Then Skill(notes).\n")
    skill(home / "own" / "notes")
    two_sources(home, "/grilling\n")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "grilling", "notes"}


def test_cycle(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "a", "/b\n")
    skill(home / "mp" / "b", "/a\n")
    configure(["mp/a"], mp="~/mp")

    assert build(capsys) == (0, "")
    assert vendored() == {"a", "b"}


def test_self_reference(home: Path, capsys: Capsys) -> None:
    two_sources(home, "Run /tdd again.\n")

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_ambiguous_target(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "a" / "grilling")
    skill(home / "mp" / "b" / "grilling")
    two_sources(home, "/grilling\n")

    code, err = build(capsys)

    assert code == 1
    assert "'mp/tdd' calls /grilling" in err
    assert str(home / "mp" / "a" / "grilling") in err
    assert str(home / "mp" / "b" / "grilling") in err


def test_clash_through_a_reference(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    skill(home / "own" / "grilling")
    configure(["mp/tdd", "own/grilling"], mp="~/mp", own="~/own")

    code, err = build(capsys)

    assert code == 1
    assert "mp/grilling" in err and "own/grilling" in err
    assert vendored() == set()


def test_not_utf8_fails(home: Path, capsys: Capsys) -> None:
    two_sources(home, "/grilling\n")
    (home / "mp" / "tdd" / "notes.md").write_bytes(b"\xff")

    code, err = build(capsys)

    assert code == 1
    assert f"mp/tdd: {home}/mp/tdd/notes.md: not UTF-8" in err
    assert vendored() == set()


TAG = "\U000e0041"


def test_hidden_character_fails(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "a\n" * 6 + f"x{TAG}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, err = build(capsys)

    assert code == 1
    assert err == (
        "skill-graft: hidden characters:\n"
        f"  mp/tdd: {home}/mp/tdd/SKILL.md:7: U+E0041 (tag character)\n"
    )
    assert vendored() == set()


def test_symlink_to_a_device(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    (home / "mp" / "grilling" / "x.md").symlink_to("/dev/zero")
    two_sources(home, "/grilling\n")

    code, err = build(capsys)

    assert code == 1 and "x.md" in err and "outside" in err


@pytest.mark.parametrize("command", ["resolve", "build"])
def test_fifo_is_an_error(home: Path, capsys: Capsys, command: str) -> None:
    skill(home / "mp" / "grilling")
    os.mkfifo(home / "mp" / "grilling" / "pipe")
    two_sources(home, "/grilling\n")

    assert main([command, "--no-install"] if command == "build" else [command]) == 1

    err = capsys.readouterr().err
    assert "pipe" in err and "not a regular file" in err


def test_link_to_a_fifo_is_an_error(home: Path, capsys: Capsys) -> None:
    grilling = skill(home / "mp" / "grilling")
    (grilling / ".git").mkdir()
    os.mkfifo(grilling / ".git" / "pipe")
    (grilling / "x.md").symlink_to(".git/pipe")
    two_sources(home, "/grilling\n")

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "x.md" in err and "not a regular file" in err


def test_dangling_link_is_caught_before_copying(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    (home / "mp" / "grilling" / "data.txt").symlink_to("gone.txt")
    two_sources(home, "/grilling\n")

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "data.txt" in err and "missing" in err


def test_dangling_link(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    (home / "mp" / "grilling" / "notes.md").symlink_to("gone.md")
    two_sources(home, "/grilling\n")

    code, err = build(capsys)

    assert code == 1 and "notes.md" in err and "Traceback" not in err
    assert vendored() == set()


def with_binds(binds: str) -> None:
    """Appends a [bind] table to the config."""
    file = Path.home() / ".apm" / "skill-graft" / "skill-graft.toml"
    file.write_text(file.read_text() + f"[bind]\n{binds}\n")


def test_bind_across_sources(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "grilling")
    skill(home / "own" / "grill")
    two_sources(home, "/grilling\n")
    with_binds('"mp/grilling" = "own/grill"')

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd", "grill"}


def test_bind_settles_ambiguity(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "notes", "own\n")
    skill(home / "x" / "notes", "x\n")
    two_sources(home, "/notes\n", x="~/x")
    with_binds('"mp/notes" = "x/notes"')

    assert build(capsys) == (0, "")
    assert (vendored_dir(home) / "notes" / "SKILL.md").read_text() == "x\n"


def test_bind_to_a_missing_skill(home: Path, capsys: Capsys) -> None:
    two_sources(home, "/grilling\n")
    with_binds('"mp/grilling" = "own/nope"')

    code, err = build(capsys)

    assert code == 1 and "mp/grilling" in err and "own/nope" in err


def test_unused_bind_to_a_missing_skill(home: Path, capsys: Capsys) -> None:
    two_sources(home, "nothing\n")
    with_binds('"mp/grill" = "own/nope"')

    code, err = build(capsys)

    assert code == 1 and "mp/grill" in err and "own/nope" in err
    assert vendored() == set()


def test_prose_bind_to_a_missing_skill(home: Path, capsys: Capsys) -> None:
    two_sources(home, "See `notes`.\n")
    with_binds('"mp/notes" = "own/nope"')

    code, err = build(capsys)

    assert code == 1 and '[bind] "mp/notes" = "own/nope"' in err


def test_path_in_a_code_block(home: Path, capsys: Capsys) -> None:
    two_sources(home, "```sh\ncd /tmp\n```\n")
    with_binds('"mp/tmp" = false')

    assert build(capsys) == (0, "")


def test_unwanted_match(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tmp")
    two_sources(home, "cd /tmp\n")
    with_binds('"mp/tmp" = false')

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_typo_in_a_bind(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "grilling")
    two_sources(home, "nothing\n")
    with_binds('"mp/grill" = "own/grilling"')

    code, err = build(capsys)

    assert code == 0 and "mp/grill" in err and "binds no reference" in err


def test_bound_self_reference(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tdd")
    two_sources(home, "/tdd\n")
    with_binds('"mp/tdd" = "own/tdd"')

    code, err = build(capsys)

    assert code == 1 and "mp/tdd" in err and "own/tdd" in err
    assert "deployed name" in err


def test_prose_never_extends_the_hull(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "diagnosing-bugs")
    two_sources(home, "Then diagnosing-bugs, or `foo`.\n")

    # A suggestion, announced; no warning, and not vendored.
    assert build(capsys) == (
        0,
        "skill-graft: 1 prose suggestion(s): run skill-graft resolve\n",
    )
    assert vendored() == {"tdd"}


def prose_edges(hull: Hull) -> set[tuple[str, str, bool]]:
    return {
        (str(e.source), str(e.target), e.bind) for e in hull.edges if e.kind == "prose"
    }


def test_prose_inside_the_hull(scope: paths.Scope, home: Path) -> None:
    skill(home / "mp" / "grilling")
    skill(home / "mp" / "notes")
    two_sources(home, "/grilling, then `notes`\n")
    configure(["mp/tdd", "mp/notes"], mp="~/mp", own="~/own")

    with compute.compute_hull(config.load(scope)) as hull:
        assert prose_edges(hull) == {("mp/tdd", "mp/notes", False)}
        assert hull.suggestions == {}


def test_prose_outside_the_hull(scope: paths.Scope, home: Path) -> None:
    skill(home / "mp" / "diagnosing-bugs")
    skill(home / "mp" / "grilling", "see diagnosing-bugs\n")
    two_sources(home, "/grilling, then diagnosing-bugs\n")

    with compute.compute_hull(config.load(scope)) as hull:
        assert list(hull.skills) == [SkillId("mp", "tdd"), SkillId("mp", "grilling")]
        assert prose_edges(hull) == set()
        assert hull.suggestions == {
            SkillId("mp", "diagnosing-bugs"): {
                SkillId("mp", "tdd"),
                SkillId("mp", "grilling"),
            }
        }


@pytest.mark.parametrize(
    "layout",
    [
        "only-another-source-has-it",
        "ambiguous-in-its-own-source",
        "unreadable-in-its-own-source",
        "matches-nothing",
    ],
)
def test_prose_is_no_reference(
    scope: paths.Scope, home: Path, capsys: Capsys, layout: str
) -> None:
    if layout == "only-another-source-has-it":
        skill(home / "own" / "notes")
    elif layout == "ambiguous-in-its-own-source":
        skill(home / "mp" / "a" / "notes")
        skill(home / "mp" / "b" / "notes")
    elif layout == "unreadable-in-its-own-source":
        skill(home / "mp" / "notes", "---\nname: [x]\n---\n")
    two_sources(home, "see `notes`\n")

    with compute.compute_hull(config.load(scope)) as hull:
        assert prose_edges(hull) == set() and hull.suggestions == {}
    assert main(["resolve"]) == 0
    assert after_package_line(capsys.readouterr().err) == ""


def test_bound_prose(scope: paths.Scope, home: Path) -> None:
    skill(home / "own" / "notes")
    two_sources(home, "/x and `notes`\n")
    configure(["mp/tdd", "own/notes"], mp="~/mp", own="~/own")
    with_binds('"mp/notes" = "own/notes"\n"mp/x" = false')

    with compute.compute_hull(config.load(scope)) as hull:
        assert prose_edges(hull) == {("mp/tdd", "own/notes", True)}


def test_bound_prose_outside_the_hull(scope: paths.Scope, home: Path) -> None:
    skill(home / "own" / "notes")
    two_sources(home, "see `notes`\n")
    with_binds('"mp/notes" = "own/notes"')

    with compute.compute_hull(config.load(scope)) as hull:
        assert list(hull.skills) == [SkillId("mp", "tdd")]
        assert hull.suggestions == {SkillId("own", "notes"): {SkillId("mp", "tdd")}}
        assert "binds no reference" not in " ".join(hull.warnings)


def test_bound_prose_to_a_missing_skill(home: Path, capsys: Capsys) -> None:
    two_sources(home, "see `notes`\n")
    with_binds('"mp/notes" = "own/nope"')

    assert main(["resolve"]) == 1
    err = capsys.readouterr().err
    assert "mp/notes" in err and "nope" in err


def test_prose_bound_to_nothing(scope: paths.Scope, home: Path) -> None:
    skill(home / "mp" / "pre-commit")
    skill(home / "mp" / "grilling")
    two_sources(home, "/grilling\n```\npre-commit run\n```\n")
    configure(["mp/tdd", "mp/pre-commit"], mp="~/mp", own="~/own")
    with_binds('"mp/pre-commit" = false')

    with compute.compute_hull(config.load(scope)) as hull:
        assert prose_edges(hull) == set() and hull.suggestions == {}
        assert hull.warnings == []


def vendored_dir(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / ".apm" / "skills"


def test_skill_tool_sentence_pulls_in_a_skill(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", 'Call the Skill tool with "grilling" and set "fast".\n')
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")

    assert build(capsys) == (0, "")  # no warning for the unresolved "fast"
    assert vendored() == {"tdd", "grilling"}

    assert main(["tree"]) == 0
    assert '(Skill tool "grilling")' in capsys.readouterr().out


def test_skill_tool_sentence_never_fails_on_a_quoted_word(
    home: Path, capsys: Capsys
) -> None:
    # "fast" is ambiguous across two other sources, "slow" unreadable in its own.
    skill(home / "mp" / "tdd", 'Call the Skill tool with "fast" or "slow".\n')
    skill(home / "mp" / "slow", "---\nname: [x]\n---\n")
    skill(home / "a" / "fast")
    skill(home / "b" / "fast")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.a]\npath = "~/a"\n[sources.b]\npath = "~/b"\n'
    )

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_skill_tool_sentence_ambiguous_when_another_source_has_two(
    home: Path, capsys: Capsys
) -> None:
    # `a` holds "deploy" twice, so `b`'s single one must not win.
    skill(home / "mp" / "tdd", 'Call the Skill tool with "deploy".\n')
    skill(home / "a" / "x" / "deploy")
    skill(home / "a" / "y" / "deploy")
    skill(home / "b" / "deploy")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.a]\npath = "~/a"\n[sources.b]\npath = "~/b"\n'
    )

    assert build(capsys) == (0, "")
    assert vendored() == {"tdd"}


RLO = "\N{RIGHT-TO-LEFT OVERRIDE}"


def hidden_lines(err: str) -> list[str]:
    """The lines under `hidden characters:` in `err`."""
    after = err.partition("hidden characters:\n")[2]
    return [line for line in after.splitlines() if line.startswith("  ")]


def test_two_skills_in_one_run(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", f"{TAG}\nRun /grilling.\n")
    skill(home / "mp" / "grilling", f"a\n{RLO}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, err = build(capsys)

    assert code == 1
    assert hidden_lines(err) == [
        f"  mp/tdd: {home}/mp/tdd/SKILL.md:1: U+E0041 (tag character)",
        f"  mp/grilling: {home}/mp/grilling/SKILL.md:2: U+202E (bidi control)",
    ]


def test_with_markdown_not_utf8(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "Run /grilling.\n")
    (home / "mp" / "tdd" / "notes.md").write_bytes("caf\xe9\n".encode("latin-1"))
    skill(home / "mp" / "grilling", f"{RLO}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, err = build(capsys)

    assert code == 1
    assert hidden_lines(err) == [
        f"  mp/tdd: {home}/mp/tdd/notes.md: not UTF-8, so its references cannot be read",
        f"  mp/grilling: {home}/mp/grilling/SKILL.md:1: U+202E (bidi control)",
    ]


def test_outside_the_hull(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes", f"{TAG}\n")
    configure(["mp/tdd"], mp="~/mp")

    assert build(capsys) == (0, "")


def test_unused_key_warnings_left_out(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", f"{TAG}\n")
    skill(home / "mp" / "x")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n[bind]\n"mp/y" = "mp/x"\n'
    )

    code, err = build(capsys)

    assert code == 1 and "skill-graft: warning" not in err


def test_debris_warns(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "a\nb\n\N{ZERO WIDTH SPACE}c\N{ZERO WIDTH SPACE}\n")
    configure(["mp/tdd"], mp="~/mp")

    assert build(capsys) == (
        0,
        f"skill-graft: warning: {home}/mp/tdd/SKILL.md:3: 2 invisible characters, "
        "the first U+200B\n",
    )
    assert vendored() == {"tdd"}


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_unreadable_file(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    (home / "mp" / "tdd" / "secret").write_text("x")
    (home / "mp" / "tdd" / "secret").chmod(0)
    configure(["mp/tdd"], mp="~/mp")

    code, err = build(capsys)

    assert code == 1
    assert f"{home}/mp/tdd/secret cannot be read" in err


def git_patch(
    tmp_path: Path, before: dict[str, bytes], after: dict[str, bytes]
) -> bytes:
    """`git diff` from a folder holding `before` to one holding `after`."""
    repo = tmp_path / "git-patch"
    shutil.rmtree(repo, ignore_errors=True)
    repo.mkdir()

    def git(*args: str) -> bytes:
        return subprocess.run(
            ["git", *args], cwd=repo, check=True, capture_output=True
        ).stdout

    def write(files: dict[str, bytes]) -> None:
        for path in [p for p in repo.iterdir() if p.name != ".git"]:
            shutil.rmtree(path) if path.is_dir() else path.unlink()
        for name, data in files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_bytes(data)

    git("init", "-q")
    write(before)
    git("add", "-A")
    git("commit", "-qm", "before", "--allow-empty")
    write(after)
    git("add", "-A")
    return git("diff", "--cached")


def patched_tdd(
    tmp_path: Path, upstream: dict[str, bytes], after: dict[str, bytes]
) -> None:
    """Entry `mp/tdd` holding `upstream`, patched by `patches/tdd.patch` to `after`."""
    for name, data in upstream.items():
        (Path.home() / "mp" / "tdd" / name).parent.mkdir(parents=True, exist_ok=True)
        (Path.home() / "mp" / "tdd" / name).write_bytes(data)
    write_patch("tdd.patch", git_patch(tmp_path, upstream, after))
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )


def test_patch_adds_one(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    patched_tdd(
        tmp_path, {"SKILL.md": b"# tdd\n"}, {"SKILL.md": f"# tdd\n{RLO}\n".encode()}
    )

    code, err = build(capsys)

    assert code == 1
    assert hidden_lines(err) == ["  mp/tdd: patches/tdd.patch:7: U+202E (bidi control)"]


def test_patch_moves_one(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    text = "a\n" * 6 + f"{TAG}\n"
    patched_tdd(
        tmp_path, {"SKILL.md": text.encode()}, {"SKILL.md": ("x\n" * 3 + text).encode()}
    )

    code, err = build(capsys)

    assert code == 1
    assert hidden_lines(err) == [
        f"  mp/tdd: {home}/mp/tdd/SKILL.md:7: U+E0041 (tag character)"
    ]


def test_patch_removes_one(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    patched_tdd(
        tmp_path, {"SKILL.md": f"# tdd\n{TAG}\n".encode()}, {"SKILL.md": b"# tdd\n"}
    )

    code, err = build(capsys)

    assert code == 1
    assert hidden_lines(err) == [
        f"  mp/tdd: {home}/mp/tdd/SKILL.md:2: U+E0041 (tag character)"
    ]


def test_patch_creates_a_name(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    patched_tdd(
        tmp_path,
        {"SKILL.md": b"# tdd\n"},
        {"SKILL.md": b"# tdd\n", f"x{RLO}.txt": b"plain\n"},
    )
    assert (
        b'"b/x\\342\\200\\256.txt"'
        in (home / ".apm/skill-graft/patches/tdd.patch").read_bytes()
    )

    code, err = build(capsys)

    assert code == 1
    assert hidden_lines(err) == [
        "  mp/tdd: as patched, x\\u202e.txt: its name holds U+202E (bidi control)"
    ]


def test_debris_in_a_patch_warns(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    patched_tdd(
        tmp_path,
        {"SKILL.md": b"# tdd\n"},
        {"SKILL.md": "# tdd\n\N{SOFT HYPHEN}\n".encode()},
    )

    code, err = build(capsys)

    assert code == 0
    assert err == (
        "skill-graft: warning: patches/tdd.patch:7: 1 invisible character, "
        "the first U+00AD\n"
    )


def test_with_a_failing_patch(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    patched_tdd(tmp_path, {"SKILL.md": b"# tdd\n"}, {"SKILL.md": b"# tdd\nmore\n"})
    (home / "mp" / "tdd" / "SKILL.md").write_text("# changed\n")
    skill(home / "mp" / "notes", f"{TAG}\n")
    write_config(
        'entries = ["mp/tdd", "mp/notes"]\n[sources.mp]\npath = "~/mp"\n'
        '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )

    code, err = build(capsys)

    assert code == 1
    assert err.index("patches do not apply:") < err.index("hidden characters:")
    assert "mp/tdd: patches/tdd.patch: SKILL.md: hunk" in err
    assert hidden_lines(err) == [
        f"  mp/notes: {home}/mp/notes/SKILL.md:1: U+E0041 (tag character)"
    ]


def test_patch_makes_markdown_not_utf8(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    patched_tdd(
        tmp_path,
        {"SKILL.md": b"# tdd\n", "notes.md": b"plain\n"},
        {"SKILL.md": b"# tdd\n", "notes.md": b"caf\xe9\n"},
    )

    code, err = build(capsys)

    assert code == 1
    assert hidden_lines(err) == [
        "  mp/tdd: as patched, notes.md: not UTF-8, so its references cannot be read"
    ]


def test_parent_folder_name_shown_escaped(home: Path, capsys: Capsys) -> None:
    skill(home / f"m{RLO}p" / "tdd", f"{TAG}\n")
    configure(["mp/tdd"], mp=f"~/m{RLO}p")

    code, err = build(capsys)

    assert code == 1 and RLO not in err
    assert "m\\u202ep/tdd/SKILL.md:1: U+E0041" in err
