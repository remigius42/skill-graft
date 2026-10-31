"""The `skill-discovery` spec, through `skill-graft deploy --no-install`, and through
`discovery` itself where a deploy cannot show it."""

import os
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import (
    Upstream,
    deploy,
    configure,
    deadline,
    skill,
    vendored,
    write_config,
)

from skill_graft.infra import paths
from skill_graft.infra.errors import SkillGraftError
from skill_graft.pipeline import discovery

Capsys: TypeAlias = pytest.CaptureFixture[str]


def test_nested_layout(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "a")
    skill(home / "src" / "x" / "y" / "z" / "b")
    configure(["own/a", "own/b"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"a", "b"}


def test_hidden_folders_are_searched(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / ".claude" / "skills" / "a")
    configure(["own/a"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"a"}


def test_skill_inside_a_skill_is_part_of_it(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "a")
    skill(home / "src" / "a" / "examples" / "c")
    configure(["own/c"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1 and "own/c" in err
    configure(["own/a"], own="~/src")
    assert deploy(capsys) == (0, "")
    skills = home / ".apm" / "skill-graft" / ".apm" / "skills"
    assert (skills / "a" / "examples" / "c" / "SKILL.md").exists()


def test_symlinked_skill_folder(home: Path, capsys: Capsys) -> None:
    target = skill(home / "elsewhere" / "tdd")
    (home / "src").mkdir()
    (home / "src" / "tdd").symlink_to(target)
    configure(["own/tdd"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_symlink_cycle_finds_each_skill_once(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "a")
    (home / "src" / "loop").symlink_to(home / "src")
    configure(["own/a"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"a"}


def test_symlink_into_the_package_is_skipped(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "chisel")
    (home / "src" / "apm").symlink_to(home / ".apm")
    configure(["own/chisel"], own="~/src")
    deploy(capsys)

    assert deploy(capsys) == (0, "")
    assert vendored() == {"chisel"}


def test_git_metadata_is_skipped(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / ".git" / "x")
    configure(["own/x"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1 and "own/x" in err


def test_source_that_is_a_skill(home: Path, capsys: Capsys) -> None:
    skill(home / "chisel")
    configure(["own/chisel"], own="~/chisel")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"chisel"}


def test_front_matter_name(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd-v2", "---\nname: tdd\ndescription: d\n---\nbody\n")
    configure(["mp/tdd"], mp="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_front_matter_name_replaces_the_folder_name(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd-v2", "---\nname: tdd\n---\n")
    configure(["mp/tdd-v2"], mp="~/src")

    code, err = deploy(capsys)

    assert code == 1 and "mp/tdd-v2" in err


@pytest.mark.parametrize(
    "text",
    [
        "# no front matter\n",
        "---\ndescription: d\n---\n",
        "---\nname: x\n",
        "---\nmeta:\n  name: other\n---\n",
    ],
    ids=["none", "no name", "unclosed", "indented name"],
)
def test_folder_name_without_front_matter_name(
    home: Path, capsys: Capsys, text: str
) -> None:
    skill(home / "src" / "grilling", text)
    configure(["own/grilling"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"grilling"}


@pytest.mark.parametrize(
    "line", ['name: "tdd" # renamed', "name: 'tdd'", "name:   tdd   ", "name: tdd\t# x"]
)
def test_comment_and_quotes(home: Path, capsys: Capsys, line: str) -> None:
    skill(home / "src" / "x", f"﻿--- \n{line}\n---  \n")
    configure(["own/tdd"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


@pytest.mark.parametrize(
    "value", [">-", "|", "&anchor tdd", "*alias", "[a]", "{a: b}", ""]
)
def test_unsupported_yaml_form(home: Path, capsys: Capsys, value: str) -> None:
    skill(home / "src" / "x", f"---\nname: {value}\n  tdd\n---\n")
    configure(["own/x"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1 and "x/SKILL.md" in err


@pytest.mark.parametrize(
    ("first", "text"),
    [("a/tdd", "# skill\n"), ("a/x", "---\nname: tdd\n---\n")],
    ids=["folder names", "front matter and folder name"],
)
def test_duplicate_name(home: Path, capsys: Capsys, first: str, text: str) -> None:
    skill(home / "src" / first, text)
    skill(home / "src" / "b" / "tdd")
    configure(["mp/tdd"], mp="~/src")

    code, err = deploy(capsys)

    assert code == 1
    assert "mp/tdd" in err and first in err and "b/tdd" in err
    assert vendored() == set()


def test_entry_not_found(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd")
    configure(["mp/nope"], mp="~/src")

    code, err = deploy(capsys)

    assert code == 1 and "mp/nope" in err


def test_traversal_in_name_writes_nothing(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "x", "---\nname: ../../x\n---\n")
    configure(["own/x"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1 and "x/SKILL.md" in err
    assert vendored() == set()
    assert not (home / ".apm" / "skill-graft" / "x").exists()


def test_other_skills_problems_do_not_block(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "tdd")
    skill(home / "src" / "a" / "dup")
    skill(home / "src" / "b" / "dup")
    skill(home / "src" / "bad", "---\nname: ../bad\n---\n")
    skill(home / "src" / "odd", "---\nname: |\n  odd\n---\n")
    configure(["own/tdd"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_hash_inside_quotes_is_not_a_comment(home: Path, capsys: Capsys) -> None:
    skill(home / "src" / "x", '---\nname: "a #b" # comment\n---\n')
    configure(["own/x"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1 and r"name a\040\043b is" in err


@pytest.mark.parametrize("entry", ["own/foo", "own/x"])
def test_name_continued_on_the_next_line(
    home: Path, capsys: Capsys, entry: str
) -> None:
    skill(home / "src" / "x", "---\nname: foo\n  bar\n---\n")
    configure([entry], own="~/src")

    assert deploy(capsys)[0] == 1
    assert vendored() == set()


def test_unreadable_skill_with_the_entry_folder_name_is_ambiguous(
    home: Path, capsys: Capsys
) -> None:
    skill(home / "src" / "tdd-v2", "---\nname: tdd\n---\n")
    skill(home / "src" / "old" / "tdd", "---\nname: >-\n  tdd\n---\n")
    configure(["mp/tdd"], mp="~/src")

    code, err = deploy(capsys)

    assert code == 1
    assert "ambiguous" in err and "old/tdd/SKILL.md" in err and "tdd-v2" in err


def test_invalid_name_in_a_folder_with_the_entry_name_does_not_block(
    home: Path, capsys: Capsys
) -> None:
    skill(home / "src" / "tdd-v2", "---\nname: tdd\n---\n")
    skill(home / "src" / "other" / "tdd", "---\nname: tdd extra\n---\n")
    configure(["mp/tdd"], mp="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


def unreadable_skill(folder: Path, how: str) -> None:
    folder.mkdir(parents=True)
    if how == "not utf-8":
        (folder / "SKILL.md").write_bytes(b"---\nname: \xff\n---\n")
    else:
        (folder / "SKILL.md").symlink_to(folder / "nowhere")


@pytest.mark.parametrize("how", ["not utf-8", "dangling symlink"])
def test_unreadable_skill_elsewhere_does_not_block(
    home: Path, capsys: Capsys, how: str
) -> None:
    skill(home / "src" / "chisel")
    unreadable_skill(home / "src" / "other", how)
    configure(["own/chisel"], own="~/src")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"chisel"}


@pytest.mark.parametrize("how", ["not utf-8", "dangling symlink"])
def test_unreadable_named_skill(home: Path, capsys: Capsys, how: str) -> None:
    unreadable_skill(home / "src" / "other", how)
    configure(["own/other"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1 and "other/SKILL.md" in err


@pytest.mark.parametrize("via_symlink", [False, True])
def test_another_projects_package_is_skipped(
    home: Path, capsys: Capsys, via_symlink: bool
) -> None:
    apm = home / "src" / "repo" / ".apm"
    if via_symlink:
        apm = home / "team-repo" / ".apm"
        (home / "src").mkdir()
        (home / "src" / "team").symlink_to(apm)
    skill(apm / "skill-graft" / ".apm" / "skills" / "tdd")
    configure(["own/tdd"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1
    assert "own/tdd" in err


def test_link_into_another_package_is_skipped(home: Path, capsys: Capsys) -> None:
    vendored_skills = home / "team-repo" / ".apm" / "skill-graft" / ".apm" / "skills"
    skill(vendored_skills / "tdd")
    (home / "src").mkdir()
    (home / "src" / "team").symlink_to(vendored_skills)
    configure(["own/tdd"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1
    assert "own/tdd" in err


def test_symlinked_package_is_skipped(home: Path, capsys: Capsys) -> None:
    # The package folder itself is a link to a folder of another name.
    skill(home / "team-sg" / ".apm" / "skills" / "tdd")
    (home / "src" / "repo" / ".apm").mkdir(parents=True)
    (home / "src" / "repo" / ".apm" / "skill-graft").symlink_to(home / "team-sg")
    configure(["own/tdd"], own="~/src")

    code, err = deploy(capsys)

    assert code == 1
    assert "own/tdd" in err


def not_regular(skill_md: Path, how: str) -> None:
    """Makes `skill_md` something other than a regular file, links followed."""
    skill_md.parent.mkdir(parents=True)
    if how == "fifo":
        os.mkfifo(skill_md)
    elif how == "device":
        skill_md.symlink_to("/dev/zero")
    elif how == "dangling":
        skill_md.symlink_to(skill_md.parent / "nowhere")
    else:  # a link into a folder the user cannot search, so it cannot be stat'ed
        locked = skill_md.parents[2] / "locked"
        skill(locked)
        skill_md.symlink_to(locked / "SKILL.md")
        locked.chmod(0)


@pytest.fixture
def unlock(home: Path) -> Iterator[None]:
    yield
    for locked in home.rglob("locked"):
        locked.chmod(0o755)


@pytest.mark.parametrize("how", ["device", "fifo"])
def test_skill_md_not_a_regular_file_does_not_block(
    home: Path, capsys: Capsys, how: str
) -> None:
    skill(home / "src" / "tdd")
    not_regular(home / "src" / "x" / "SKILL.md", how)
    configure(["own/tdd"], own="~/src")

    with deadline():
        assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


@pytest.mark.parametrize(
    ("how", "cause"),
    [
        ("device", ""),
        ("fifo", ""),
        ("dangling", ": No such file or directory"),
        pytest.param(
            "unstatable", ": Permission denied", marks=pytest.mark.needs_permissions
        ),
    ],
)
@pytest.mark.usefixtures("unlock")
def test_skill_md_not_a_regular_file_is_unreadable(
    home: Path, capsys: Capsys, how: str, cause: str
) -> None:
    not_regular(home / "src" / "x" / "SKILL.md", how)
    configure(["own/x"], own="~/src")

    with deadline():
        code, err = deploy(capsys)

    assert code == 1
    assert f"{home / 'src' / 'x' / 'SKILL.md'}: not a regular file{cause}\n" in err


def test_read_name_refuses_a_fifo(home: Path) -> None:
    # As if a regular file were swapped for a FIFO after discovery checked it.
    os.mkfifo(home / "SKILL.md")

    with deadline(), pytest.raises(SkillGraftError, match="not a regular file"):
        discovery.read_name(home)


def test_read_name_takes_no_terminal(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A terminal swapped in after the check must not become the controlling one.
    skill(home / "x")
    flags = []
    real_open = os.open

    def spy(path: Path, flag: int) -> int:
        flags.append(flag)
        return real_open(path, flag)

    monkeypatch.setattr(os, "open", spy)

    discovery.read_name(home / "x")

    assert flags and all(flag & os.O_NOCTTY for flag in flags)


def test_link_into_a_project_package_is_skipped(home: Path, tmp_path: Path) -> None:
    # The project's package links to a folder of another name, which the source
    # reaches by a link of a third: only the scope's package names it.
    project = tmp_path / "project"
    skill(tmp_path / "team-sg" / ".apm" / "skills" / "tdd")
    (project / ".apm").mkdir(parents=True)
    (project / ".apm" / "skill-graft").symlink_to(tmp_path / "team-sg")
    (home / "src").mkdir()
    (home / "src" / "team").symlink_to(tmp_path / "team-sg")

    assert discovery.index(paths.Scope(project), home / "src").folders == {}
    assert discovery.index(paths.Scope(home), home / "src").folders == {
        "tdd": [home / "src" / "team" / ".apm" / "skills" / "tdd"]
    }


def test_regular_file_linked_from_outside_a_path_source(home: Path) -> None:
    # Discovery reads it; vendoring's symlink check refuses it in a hull skill.
    skill(home / "elsewhere", "---\nname: tdd\n---\n")
    (home / "src" / "x").mkdir(parents=True)
    (home / "src" / "x" / "SKILL.md").symlink_to(home / "elsewhere" / "SKILL.md")

    skills = discovery.index(paths.Scope(home), home / "src")

    assert skills.folders == {"tdd": [home / "src" / "x"]}


@pytest.mark.parametrize("target", ["file", "device", "missing"])
def test_confined_skill_md_linked_outside(home: Path, target: str) -> None:
    (home / "local").mkdir()
    (home / "local" / "SKILL.md").write_text("---\nname: leaked-marker\n---\n")
    targets = {
        "file": home / "local" / "SKILL.md",
        "device": Path("/dev/zero"),
        "missing": home / "local" / "missing",
    }
    (home / "src" / "evil").mkdir(parents=True)
    (home / "src" / "evil" / "SKILL.md").symlink_to(targets[target])

    with deadline():
        skills = discovery.index(paths.Scope(home), home / "src", confined=True)

    [error] = skills.unreadable["evil"]
    skill_md = home / "src" / "evil" / "SKILL.md"
    assert str(error) == f"{skill_md}: a symlink leading outside its skill"


def test_confined_skill_md_linked_to_a_sibling_skill(home: Path) -> None:
    skill(home / "src" / "tdd")
    (home / "src" / "copy").mkdir()
    (home / "src" / "copy" / "SKILL.md").symlink_to("../tdd/SKILL.md")

    skills = discovery.index(paths.Scope(home), home / "src", confined=True)

    assert "outside its skill" in str(skills.unreadable["copy"][0])
    assert skills.folders == {"tdd": [home / "src" / "tdd"]}


@pytest.mark.parametrize("through_link", [False, True])
def test_confined_skill_md_linked_inside(home: Path, through_link: bool) -> None:
    tdd = home / "src" / "skills" / "tdd"
    tdd.mkdir(parents=True)
    (tdd / "main.md").write_text("---\nname: tdd\n---\n")
    (tdd / "SKILL.md").symlink_to("main.md")
    if through_link:
        # Walked before `skills`, so the skill is reached through the link.
        (home / "src" / "a").symlink_to("skills")
        tdd = home / "src" / "a" / "tdd"

    skills = discovery.index(paths.Scope(home), home / "src", confined=True)

    assert skills.folders == {"tdd": [tdd]} and skills.unreadable == {}


def test_bad_folder_elsewhere_does_not_block(home: Path, capsys: Capsys) -> None:
    # Scenario: Elsewhere in the source.
    skill(home / "own" / "my skills" / "x")
    skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


@pytest.mark.parametrize(
    ("folder", "escaped"),
    [
        ("my skills/tdd", r"my\040skills/tdd"),
        ("ä/tdd", r"\303\244/tdd"),
        ("tdd\nupstream: /etc", r"tdd\012upstream\072\040/etc"),
    ],
)
def test_unusable_skill_path(
    home: Path, capsys: Capsys, folder: str, escaped: str
) -> None:
    # Scenarios: Space in a folder, Non-ASCII folder, Line break in a folder.
    skill(home / "own" / folder, "---\nname: tdd\n---\n")
    configure(["own/tdd"], own="~/own")

    code, err = deploy(capsys)

    assert code == 1
    assert err == (
        f"skill-graft: {home / 'own'}: skill folder {escaped} uses characters "
        "outside A-Z a-z 0-9 . _ -\n"
    )
    assert vendored() == set()


def test_shell_syntax_in_a_folder(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"skills/$(touch x)/tdd/SKILL.md": "# tdd\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )

    code, err = deploy(capsys)

    assert code == 1
    assert r"skills/\044\050touch\040x\051/tdd uses characters" in err
    assert "$(" not in err
    assert vendored() == set()
    assert not (home / "x").exists() and not (Path.cwd() / "x").exists()


def test_bad_path_and_a_symlink_out_of_the_skill(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    (home / "local").mkdir()
    (home / "local" / "notes.md").write_text("---\nname: tdd\n---\n")
    upstream = Upstream(tmp_path / "up")
    folder = upstream.path / "skills" / "$(x)" / "tdd"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").symlink_to(home / "local" / "notes.md")
    sha = upstream.commit({})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
    )

    code, err = deploy(capsys)

    assert code == 1
    assert r"skills/\044\050x\051/tdd uses characters" in err
    assert "$(" not in err


def test_unusable_skill_called_by_a_reference(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "a", "Run /tdd.\n")
    skill(home / "own" / "my skills" / "tdd")
    skill(home / "mp" / "tdd")
    configure(["own/a"], own="~/own", mp="~/mp")

    code, err = deploy(capsys)

    assert code == 1
    assert r"my\040skills/tdd uses characters" in err
    assert vendored() == set()


def test_unusable_skill_in_a_skill_tool_sentence(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "a", 'Call the Skill tool with "tdd".\n')
    skill(home / "own" / "my skills" / "tdd")
    configure(["own/a"], own="~/own")

    assert deploy(capsys) == (0, "")
    lock = home / ".apm" / "skill-graft" / "skill-graft.lock"
    assert tomllib.loads(lock.read_text()).get("edges", []) == []
    assert vendored() == {"a"}


def test_unusable_skill_path_and_a_namesake(home: Path, capsys: Capsys) -> None:
    # Scenario: Two skills of one name.
    skill(home / "own" / "tdd")
    skill(home / "own" / "my skills" / "tdd")
    configure(["own/tdd"], own="~/own")

    code, err = deploy(capsys)

    assert code == 1
    assert "ambiguous" in err and str(home / "own" / "tdd") in err
    assert r"my\040skills/tdd uses characters" in err


def test_bad_path_and_a_name_that_is_no_segment_does_not_block_a_namesake(
    home: Path, capsys: Capsys
) -> None:
    skill(home / "own" / "good", "---\nname: tdd\n---\n")
    skill(home / "own" / "my skills" / "tdd", "---\nname: a b\n---\n")
    configure(["own/tdd"], own="~/own")

    assert deploy(capsys) == (0, "")
    assert vendored() == {"tdd"}


def test_bad_path_and_a_name_that_is_no_segment_explains_a_miss(
    home: Path, capsys: Capsys
) -> None:
    skill(home / "own" / "my skills" / "tdd", "---\nname: a b\n---\n")
    configure(["own/tdd"], own="~/own")

    code, err = deploy(capsys)

    assert code == 1
    assert r"my\040skills/tdd uses characters" in err
    assert "not one path segment" not in err


def test_shell_syntax_in_a_name(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "x", "---\nname: $(curl x)/a\n---\n")
    configure(["own/x"], own="~/own")

    code, err = deploy(capsys)

    assert code == 1
    assert err == (
        f"skill-graft: {home / 'own'}: x/SKILL.md: name "
        r"\044\050curl\040x\051/a is not one path segment" + "\n"
    )


def test_bad_path_and_a_skill_md_that_is_a_device(
    home: Path, capsys: Capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = home / "own" / "my skills" / "tdd"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").symlink_to("/dev/zero")
    configure(["own/tdd"], own="~/own")
    read_name = discovery.read_name

    def never_on_it(found: Path) -> str:
        assert found != folder, "read_name opened the device"
        return read_name(found)

    monkeypatch.setattr(discovery, "read_name", never_on_it)

    with deadline():
        code, err = deploy(capsys)

    assert code == 1
    assert r"my\040skills/tdd uses characters" in err
