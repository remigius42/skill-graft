"""Deployed names carried into `name:` and every reference (the `renames` spec)."""

import os
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import Upstream, configure, skill, write_config

from skill_graft import config, paths, rename, resolve
from skill_graft.cache import Cache
from skill_graft.cli import main
from skill_graft.config import SkillId
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
    hull = resolve.resolve(loaded, resolve.folders(loaded, Cache(paths.cache()), {}))
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
