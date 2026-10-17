"""Deployed names carried into `name:` and every reference (the `renames` spec)."""

import os
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import Upstream, after_package_line, configure, skill, write_config

from skill_graft import config, paths, rename, resolve, vendor
from skill_graft.cache import Cache
from skill_graft.cli import main
from skill_graft.config import SkillId
from skill_graft.errors import SkillGraftError
from skill_graft.hull import Hull


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (
            "---\nname: grilling # upstream\ndescription: x\n---\n# Grilling\n",
            "---\nname: mp-grilling\ndescription: x\n---\n# Grilling\n",
        ),
        (
            "---\r\nname: 'grilling'\r\n---\r\nbody\r\n",
            "---\r\nname: mp-grilling\r\n---\r\nbody\r\n",
        ),
        ("﻿---\nname: grilling\n---\n", "﻿---\nname: mp-grilling\n---\n"),
    ],
)
def test_name_line_replaced(before: str, after: str) -> None:
    assert rename.set_name(before, "mp-grilling") == after


def test_front_matter_without_a_name() -> None:
    before = "---\ndescription: x\n---\nbody\n"

    assert (
        rename.set_name(before, "mp-tdd")
        == "---\nname: mp-tdd\ndescription: x\n---\nbody\n"
    )


@pytest.mark.parametrize("before", ["# TDD\n", "---\nnot closed\n", "", "﻿# TDD\n"])
def test_no_front_matter(before: str) -> None:
    bom = "﻿" if before.startswith("﻿") else ""

    assert rename.set_name(before, "mp-tdd") == (
        f"{bom}---\nname: mp-tdd\n---\n{before.removeprefix(bom)}"
    )


@pytest.mark.parametrize(
    ("name", "written"),
    [
        ("true", '"true"'),
        ("no", '"no"'),
        ("null", '"null"'),
        ("123", '"123"'),
        ("1e5", '"1e5"'),
        ("Notes", '"Notes"'),
        ("my_skill", '"my_skill"'),
        ("v1.2", '"v1.2"'),
        ("mp-tdd", "mp-tdd"),
        ("notes", "notes"),
    ],
)
def test_name_yaml_would_misread(name: str, written: str) -> None:
    assert (
        rename.set_name("---\nname: x\n---\n", name) == f"---\nname: {written}\n---\n"
    )


def resolved(**renames: str) -> Hull:
    """The hull, with these skill IDs (`alias__name`) deployed under new names."""
    loaded = config.load()
    folders = resolve.folders(loaded, Cache(paths.cache()), {})
    hull = resolve.resolve(loaded, folders, Path.home() / "work")
    deployed = {SkillId(*key.split("__")): name for key, name in renames.items()}
    return replace(hull, deployed=hull.deployed | deployed)


def rewritten(hull: Hull) -> dict[str, dict[str, str]]:
    return {
        str(skill_id): {path.as_posix(): data.decode() for path, data in files.items()}
        for skill_id, files in rename.rewrites(hull).items()
    }


def test_bound_to_another_name(home: Path) -> None:
    skill(home / "mp" / "grilling")
    skill(home / "own" / "grill")
    skill(home / "mp" / "tdd", "Run /grilling.\n")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/grilling" = "own/grill"\n'
    )

    assert rewritten(resolved()) == {"mp/tdd": {"SKILL.md": "Run /grill.\n"}}


def test_every_form_rewritten(home: Path) -> None:
    skill(home / "mp" / "grilling")
    skill(home / "mp" / "diagnosing-bugs")
    skill(
        home / "mp" / "tdd",
        'Run /grilling. Then Skill(skill: "grilling", args: "x"),\n'
        "`grilling` and diagnosing-bugs...\n",
    )
    configure(["mp/tdd", "mp/diagnosing-bugs"], mp="~/mp")

    hull = resolved(mp__grilling="mp-grilling", **{"mp__diagnosing-bugs": "mp-dbg"})

    assert rewritten(hull)["mp/tdd"] == {
        "SKILL.md": 'Run /mp-grilling. Then Skill(skill: "mp-grilling", args: "x"),\n'
        "`mp-grilling` and mp-dbg...\n"
    }


def test_self_reference_and_sibling_file(home: Path) -> None:
    folder = skill(home / "mp" / "tdd", "/tdd and /grilling\n")
    (folder / "refs").mkdir()
    (folder / "refs" / "loop.md").write_text("/grilling\n")
    (folder / "refs" / "plain.md").write_text("nothing\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")

    hull = resolved(mp__tdd="mp-tdd", mp__grilling="mp-grilling")

    assert rewritten(hull) == {
        "mp/tdd": {
            "SKILL.md": "---\nname: mp-tdd\n---\n/mp-tdd and /mp-grilling\n",
            "refs/loop.md": "/mp-grilling\n",
        },
        "mp/grilling": {"SKILL.md": "---\nname: mp-grilling\n---\n# skill\n"},
    }


def test_own_name_line_not_rewritten(home: Path) -> None:
    skill(home / "mp" / "code-review", "---\nname: code-review\n---\n")
    skill(home / "own" / "review")
    write_config(
        'entries = ["mp/code-review", "own/review"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/code-review" = "own/review"\n'
    )

    assert rewritten(resolved()) == {}


@pytest.mark.parametrize("change", ["not UTF-8", "deleted", "edited"])
def test_file_changed_before_vendoring(home: Path, change: str) -> None:
    tdd = skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")
    hull = resolved(mp__grilling="mp-grilling")
    if change == "deleted":
        (tdd / "SKILL.md").unlink()
    elif change == "edited":
        (tdd / "SKILL.md").write_text("A new first line\n/grilling\n")
    else:
        (tdd / "SKILL.md").write_bytes(b"/grilling \xff\n")

    with pytest.raises(SkillGraftError, match="SKILL.md"):
        vendor.vendor(hull)

    assert not (package() / ".apm" / "skills.new").exists()


def test_unresolved_names_untouched(home: Path) -> None:
    folder = skill(home / "mp" / "tdd", "/foo, /grilling\n```\npre-commit run\n```\n")
    (folder / "notes.md").write_bytes(b"/grilling \xff\n")
    skill(home / "mp" / "grilling")
    skill(home / "mp" / "pre-commit")
    write_config(
        'entries = ["mp/tdd", "mp/pre-commit"]\n[sources.mp]\npath = "~/mp"\n'
        '[bind]\n"mp/pre-commit" = false\n'
    )

    hull = resolved(mp__grilling="mp-grilling", **{"mp__pre-commit": "mp-pc"})

    assert rewritten(hull)["mp/tdd"] == {
        "SKILL.md": "/foo, /mp-grilling\n```\npre-commit run\n```\n"
    }


def package() -> Path:
    return Path.home() / ".apm" / "skill-graft"


def bound_grill(home: Path, tdd: str = "Run /grilling.\n") -> Path:
    """Entry `mp/tdd` holding `tdd`, `/grilling` bound to `own/grill`."""
    skill(home / "own" / "grill")
    folder = skill(home / "mp" / "tdd", tdd)
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/grilling" = "own/grill"\n'
    )
    return folder


def test_bound_reference_rewritten_on_build(home: Path) -> None:
    bound_grill(home)

    assert main(["build", "--no-install"]) == 0

    vendored = package() / ".apm" / "skills"
    assert (vendored / "tdd" / "SKILL.md").read_text() == "Run /grill.\n"
    assert (vendored / "grill" / "SKILL.md").read_text() == "# skill\n"


def test_read_only_upstream_rewritten(home: Path) -> None:
    folder = bound_grill(home)
    (folder / "refs").mkdir()
    (folder / "refs" / "loop.md").write_text("/grilling\n")
    for path, mode in [(folder / "refs" / "loop.md", 0o444), (folder / "refs", 0o555)]:
        path.chmod(mode)
    try:
        assert main(["build", "--no-install"]) == 0

        copy = package() / ".apm" / "skills" / "tdd" / "refs"
        assert (copy / "loop.md").read_text() == "/grill\n"
        assert (copy / "loop.md").stat().st_mode & 0o777 == 0o444
    finally:
        for root in [folder, package()]:
            for dirpath, _, _ in os.walk(root):
                Path(dirpath).chmod(0o755)


def test_resolve_and_build_agree(home: Path) -> None:
    bound_grill(home)
    lock = package() / "skill-graft.lock"

    assert main(["resolve"]) == 0
    resolved_lock = lock.read_bytes()
    assert main(["build", "--no-install"]) == 0

    assert lock.read_bytes() == resolved_lock


def test_update_and_resolve_agree(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    upstream.commit({"tdd/SKILL.md": "Run /grilling.\n"})
    skill(home / "own" / "grill")
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/grilling" = "own/grill"\n'
    )
    lock = package() / "skill-graft.lock"

    assert main(["update"]) == 0
    updated_lock = lock.read_bytes()
    assert main(["resolve"]) == 0

    assert lock.read_bytes() == updated_lock


def with_renames(home: Path, entries: list[str], renames: str) -> None:
    """Sources `mp` and `own` under `home`, these entries, and a [rename] table."""
    for alias in ["mp", "own"]:
        (home / alias).mkdir(exist_ok=True)
    configure(entries, mp="~/mp", own="~/own")
    file = package() / "skill-graft.toml"
    file.write_text(file.read_text() + f"[rename]\n{renames}\n")


def skills_dir() -> Path:
    return package() / ".apm" / "skills"


def test_renamed_skill_vendored(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(
        home / "mp" / "tdd",
        "---\nname: tdd # upstream\n---\n/grilling and `grilling`\n",
    )
    skill(home / "mp" / "grilling")
    with_renames(home, ["mp/tdd"], '"mp/tdd" = "mp-tdd"\n"mp/grilling" = "mp-grilling"')

    assert main(["build", "--no-install"]) == 0

    assert after_package_line(capsys.readouterr().err) == ""
    assert {p.name for p in skills_dir().iterdir()} == {"mp-tdd", "mp-grilling"}
    assert (skills_dir() / "mp-tdd" / "SKILL.md").read_text() == (
        "---\nname: mp-tdd\n---\n/mp-grilling and `mp-grilling`\n"
    )


def test_renamed_in_a_skill_tool_sentence(home: Path) -> None:
    skill(home / "mp" / "tdd", 'Call the Skill tool with "grilling".\n')
    skill(home / "mp" / "grilling")
    with_renames(home, ["mp/tdd"], '"mp/grilling" = "mp-grilling"')

    assert main(["build", "--no-install"]) == 0
    assert main(["build", "--no-install"]) == 0

    assert (skills_dir() / "tdd" / "SKILL.md").read_text() == (
        'Call the Skill tool with "mp-grilling".\n'
    )


def test_bind_silences_a_skill_tool_sentence(home: Path) -> None:
    skill(home / "mp" / "tdd", 'Call the Skill tool with "grilling".\n')
    skill(home / "mp" / "grilling")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[bind]\n"mp/grilling" = false\n'
    )

    assert main(["build", "--no-install"]) == 0

    assert {p.name for p in skills_dir().iterdir()} == {"tdd"}


def test_rename_outside_the_hull(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "review")
    with_renames(home, ["mp/tdd"], '"mp/review" = "mp-review"')

    assert main(["build", "--no-install"]) == 0

    err = capsys.readouterr().err
    assert err.count("mp/review") == 1 and "renames no skill in the hull" in err


def test_clash_across_sources(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "tdd")
    skill(home / "own" / "x")
    with_renames(home, ["own/x"], '"own/x" = "own-x"')
    assert main(["build", "--no-install"]) == 0
    lock = (package() / "skill-graft.lock").read_bytes()
    with_renames(home, ["mp/tdd", "own/tdd"], '"own/x" = "own-x"')

    assert main(["build", "--no-install"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/tdd" in err
    assert '[rename] "own/tdd" = "own-tdd"' in err
    assert {p.name for p in skills_dir().iterdir()} == {"own-x"}
    assert (package() / "skill-graft.lock").read_bytes() == lock


def test_rename_settles_a_clash(home: Path) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "tdd")
    with_renames(home, ["mp/tdd", "own/tdd"], '"own/tdd" = "own-tdd"')

    assert main(["build", "--no-install"]) == 0

    assert {p.name for p in skills_dir().iterdir()} == {"tdd", "own-tdd"}


def test_reserved_by_the_user(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "review")
    with_renames(home, ["mp/review"], "")
    file = package() / "skill-graft.toml"
    file.write_text('reserved = ["Review"]\n' + file.read_text())

    for args in [["resolve"], ["build", "--no-install"]]:
        assert main(args) == 1
        err = capsys.readouterr().err
        assert "mp/review" in err and "reserved" in err
        assert '[rename] "mp/review" = "mp-review"' in err
    assert not skills_dir().exists()


def test_renamed_out_of_the_way(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "review")
    with_renames(home, ["mp/review"], '"mp/review" = "mp-review"')
    file = package() / "skill-graft.toml"
    file.write_text('reserved = ["review"]\n' + file.read_text())

    assert main(["build", "--no-install"]) == 0
    assert after_package_line(capsys.readouterr().err) == ""


def test_shipped_clash(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "code-review")
    with_renames(home, ["mp/code-review"], "")

    assert main(["build", "--no-install"]) == 0

    err = capsys.readouterr().err
    assert err.count("mp/code-review") == 2  # one warning, its rename line
    assert err.rstrip().endswith('[rename] "mp/code-review" = "mp-code-review"')


def test_renamed_onto_a_shipped_name(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "mp" / "check")
    with_renames(home, ["mp/check"], '"mp/check" = "review"')

    assert main(["build", "--no-install"]) == 0

    err = capsys.readouterr().err
    assert "mp/check" in err and "`review`" in err and "[rename]" not in err


def test_both_lists(home: Path) -> None:
    skill(home / "mp" / "code-review")
    with_renames(home, ["mp/code-review"], "")
    file = package() / "skill-graft.toml"
    file.write_text('reserved = ["code-review"]\n' + file.read_text())

    assert main(["build", "--no-install"]) == 1


def test_rename_onto_another_skills_name(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "mp" / "grilling")
    skill(home / "own" / "notes")
    with_renames(home, ["mp/grilling", "own/notes"], '"mp/grilling" = "Notes"')

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "mp/grilling" in err and "own/notes" in err
    assert '[rename] "own/notes" = "own-notes"' in err  # never a second key


def test_clash_of_two_renames(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "a")
    skill(home / "own" / "b")
    with_renames(home, ["mp/a", "own/b"], '"mp/a" = "x"\n"own/b" = "x"')

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert 'change [rename] "own/b" = "x"' in err
    assert '"own/b" = "own-b"' not in err


def test_renamed_onto_a_reserved_name(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "mp" / "check")
    with_renames(home, ["mp/check"], '"mp/check" = "review"')
    file = package() / "skill-graft.toml"
    file.write_text('reserved = ["review"]\n' + file.read_text())

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert 'change [rename] "mp/check" = "review"' in err
    assert "mp-check" not in err


def with_prefixes(
    home: Path, entries: list[str], renames: str = "", **prefixes: str
) -> None:
    """Path sources `mp` and `own` under `home`, these prefixes, entries and renames."""
    text = f"entries = {entries!r}\n".replace("'", '"')
    for alias in ["mp", "own"]:
        (home / alias).mkdir(exist_ok=True)
        text += f'[sources.{alias}]\npath = "~/{alias}"\n'
        if alias in prefixes:
            text += f'prefix = "{prefixes[alias]}"\n'
    write_config(text + f"[rename]\n{renames}\n")


def test_dependency_prefixed(home: Path) -> None:
    skill(home / "mp" / "tdd", "---\nname: tdd\n---\n/grilling and `grilling`\n")
    skill(home / "mp" / "grilling", "---\nname: grilling\n---\n")
    skill(home / "own" / "notes")
    with_prefixes(home, ["mp/tdd", "own/notes"], mp="mp-")

    assert main(["build", "--no-install"]) == 0

    assert {p.name for p in skills_dir().iterdir()} == {
        "mp-tdd",
        "mp-grilling",
        "notes",
    }
    assert (skills_dir() / "mp-tdd" / "SKILL.md").read_text() == (
        "---\nname: mp-tdd\n---\n/mp-grilling and `mp-grilling`\n"
    )
    assert (skills_dir() / "mp-grilling" / "SKILL.md").read_text() == (
        "---\nname: mp-grilling\n---\n"
    )


def test_rename_wins_over_the_prefix_used_as_written(home: Path) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "grilling")
    with_prefixes(home, ["mp/tdd", "mp/grilling"], '"mp/tdd" = "tdd"', mp="mp")

    assert main(["build", "--no-install"]) == 0

    assert {p.name for p in skills_dir().iterdir()} == {"tdd", "mpgrilling"}


def test_bound_to_a_prefixed_skill(home: Path) -> None:
    skill(home / "mp" / "tdd", "Run /grilling.\n")
    skill(home / "own" / "grill")
    with_prefixes(home, ["mp/tdd"], own="own-")
    file = package() / "skill-graft.toml"
    file.write_text(file.read_text() + '[bind]\n"mp/grilling" = "own/grill"\n')

    assert main(["build", "--no-install"]) == 0

    assert (skills_dir() / "tdd" / "SKILL.md").read_text() == "Run /own-grill.\n"


def test_prefix_onto_another_skills_name(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "mp-tdd")
    with_prefixes(home, ["own/mp-tdd", "mp/tdd"], mp="mp-")

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/mp-tdd" in err
    assert '[rename] "own/mp-tdd" = "own-mp-tdd"' in err
    assert '"mp/tdd" = "mp-tdd"' not in err


def test_two_sources_one_prefix(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "tdd")
    with_prefixes(home, ["mp/tdd", "own/tdd"], mp="x-", own="x-")

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/tdd" in err
    assert (
        'add a [rename] key for "own/tdd", or change [sources.own] prefix = "x-"' in err
    )


def test_prefixed_onto_a_reserved_name(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "mp" / "review")
    with_prefixes(home, ["mp/review"], mp="mp-")
    file = package() / "skill-graft.toml"
    file.write_text('reserved = ["mp-review"]\n' + file.read_text())

    assert main(["resolve"]) == 1

    err = capsys.readouterr().err
    assert "mp/review" in err and "`mp-review`" in err
    assert (
        'add a [rename] key for "mp/review", or change [sources.mp] prefix = "mp-"'
        in err
    )


def test_prefixed_onto_a_shipped_name(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "own" / "view")
    with_prefixes(home, ["own/view"], own="re")

    assert main(["build", "--no-install"]) == 0

    err = after_package_line(capsys.readouterr().err)
    assert "own/view" in err and "`review`" in err
    assert "[rename]" not in err and "prefix" not in err
