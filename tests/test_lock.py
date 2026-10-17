"""The lock's content (the `resolve` spec): sources, skills, edges, hashes."""

import os
import stat
import tomllib
from pathlib import Path
from typing import Any

from conftest import Upstream, configure, make_patch, skill, write_config

from skill_graft import cache, config, lock, paths, resolve
from skill_graft.cache import Cache
from skill_graft.cli import main


def render() -> str:
    loaded = config.load()
    folders = resolve.folders(loaded, Cache(paths.cache()), {})
    return lock.render(
        loaded, {}, resolve.resolve(loaded, folders, Path.home() / "work")
    )


def parsed() -> dict[str, Any]:
    return tomllib.loads(render())


def edges() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = parsed()["edges"]
    return result


def test_edges_with_kinds(home: Path) -> None:
    skill(home / "mp" / "tdd", "/grilling and Skill(notes)\n")
    skill(home / "mp" / "grilling")
    skill(home / "own" / "notes")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/notes" = "own/notes"\n'
    )

    assert edges() == [
        {"from": "mp/tdd", "to": "mp/grilling", "kind": "slash"},
        {"from": "mp/tdd", "to": "own/notes", "kind": "skill-tool", "bind": True},
    ]


def test_bound_and_default_edge_to_one_skill(home: Path) -> None:
    skill(home / "mp" / "tdd", "/g and /notes and /notes again\n")
    skill(home / "own" / "notes")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/g" = "own/notes"\n'
    )

    assert edges() == [
        {"from": "mp/tdd", "to": "own/notes", "kind": "slash"},
        {"from": "mp/tdd", "to": "own/notes", "kind": "slash", "bind": True},
    ]


def test_sources_and_skills(home: Path) -> None:
    skill(home / "own" / "tdd", "/grilling\n")
    skill(home / "own" / "grilling")
    configure(["own/tdd"], own="~/own")

    lock_data = parsed()

    assert lock_data["version"] == 1
    assert lock_data["sources"] == {"own": {"path": str(home / "own")}}
    assert [(s["id"], s["entry"]) for s in lock_data["skills"]] == [
        ("own/grilling", False),
        ("own/tdd", True),
    ]
    assert all(s["hash"].startswith("sha256:") for s in lock_data["skills"])


def test_upstream_recorded(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"skills/tdd/SKILL.md": "# tdd\n"})
    skill(home / "own" / "chisel")
    write_config(
        f'entries = ["mp/tdd", "own/chisel"]\n[sources.mp]\ngit = "{upstream.url}"\n'
        f'ref = "{sha}"\n[sources.own]\npath = "~/own"\n'
    )

    skills = {s["id"]: s for s in parsed()["skills"]}

    tree = paths.cache() / "trees" / cache.key(upstream.url) / sha
    assert skills["mp/tdd"]["upstream"] == str(tree / "skills" / "tdd")
    assert skills["own/chisel"]["upstream"] == str(home / "own" / "chisel")


def patched_tdd(home: Path, tmp_path: Path, files: list[str]) -> None:
    """Entry `mp/tdd` and `mp/notes`; each of `files` adds a line to `mp/tdd`."""
    skill(home / "mp" / "tdd", "# tdd\n")
    skill(home / "mp" / "notes")
    folder = home / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True, exist_ok=True)
    text = "# tdd\n"
    for name in files:
        data = make_patch(
            tmp_path, {"SKILL.md": text}, {"SKILL.md": text + f"{name}\n"}
        )
        (folder / name).write_bytes(data)
        text += f"{name}\n"
    listed = ", ".join(f'"patches/{name}"' for name in files)
    write_config(
        'entries = ["mp/tdd", "mp/notes"]\n[sources.mp]\npath = "~/mp"\n'
        + (f'[patches]\n"mp/tdd" = [{listed}]\n' if files else "")
    )


def test_patches_recorded(home: Path, tmp_path: Path) -> None:
    patched_tdd(home, tmp_path, ["b.patch", "a.patch"])

    skills = {s["id"]: s for s in parsed()["skills"]}

    assert skills["mp/tdd"]["patches"] == ["patches/b.patch", "patches/a.patch"]
    assert "patches" not in skills["mp/notes"]


def test_patch_changes_the_hash(home: Path, tmp_path: Path) -> None:
    patched_tdd(home, tmp_path, [])
    before = {s["id"]: s for s in parsed()["skills"]}
    patched_tdd(home, tmp_path, ["a.patch"])

    after = {s["id"]: s for s in parsed()["skills"]}

    assert after["mp/tdd"]["hash"] != before["mp/tdd"]["hash"]
    assert after["mp/tdd"]["upstream"] == before["mp/tdd"]["upstream"]
    assert after["mp/notes"] == before["mp/notes"]


def test_resolve_and_build_agree_with_patches(home: Path, tmp_path: Path) -> None:
    patched_tdd(home, tmp_path, ["a.patch", "b.patch"])
    lock_file = home / ".apm" / "skill-graft" / "skill-graft.lock"
    assert main(["resolve"]) == 0
    resolved = lock_file.read_bytes()

    assert main(["build", "--no-install"]) == 0

    assert lock_file.read_bytes() == resolved


def test_hash_follows_content(home: Path) -> None:
    skill(home / "own" / "tdd", "/notes\n")
    notes = skill(home / "own" / "notes")
    configure(["own/tdd"], own="~/own")
    before = {s["id"]: s["hash"] for s in parsed()["skills"]}
    (notes / "SKILL.md").write_text("changed\n")

    after = {s["id"]: s["hash"] for s in parsed()["skills"]}

    assert before["own/tdd"] == after["own/tdd"]
    assert before["own/notes"] != after["own/notes"]


def test_exec_bit_changes_the_hash(home: Path) -> None:
    tdd = skill(home / "own" / "tdd")
    (tdd / "run.sh").write_text("x\n")
    configure(["own/tdd"], own="~/own")
    before = parsed()["skills"][0]["hash"]
    (tdd / "run.sh").chmod(0o755)

    assert parsed()["skills"][0]["hash"] != before


def renaming(renames: str) -> None:
    """Entry `mp/tdd` calling `/grilling`, mentioning `` `grilling` ``, renamed so."""
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n[rename]\n{renames}\n'
    )


def test_renamed_skill(home: Path) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    renaming('"mp/grilling" = "mp-grilling"')

    assert [
        {k: v for k, v in s.items() if k not in ("hash", "upstream")}
        for s in parsed()["skills"]
    ] == [
        {"id": "mp/grilling", "entry": False, "deployed": "mp-grilling"},
        {"id": "mp/tdd", "entry": True},
    ]


def test_prose_edge(home: Path) -> None:
    skill(home / "mp" / "tdd", "/grilling and `grilling`\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")

    assert edges() == [
        {"from": "mp/tdd", "to": "mp/grilling", "kind": "prose"},
        {"from": "mp/tdd", "to": "mp/grilling", "kind": "slash"},
    ]


def test_suggestion_recorded(home: Path) -> None:
    skill(home / "mp" / "tdd", "/grilling, then diagnosing-bugs\n")
    skill(home / "mp" / "grilling", "see `diagnosing-bugs`\n")
    skill(home / "mp" / "diagnosing-bugs")
    configure(["mp/tdd"], mp="~/mp")

    assert parsed()["suggestions"] == [
        {"id": "mp/diagnosing-bugs", "from": ["mp/grilling", "mp/tdd"]}
    ]


def test_rename_changes_the_hash(home: Path) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    renaming("")
    before = {s["id"]: s["hash"] for s in parsed()["skills"]}
    renaming('"mp/grilling" = "mp-grilling"')

    after = {s["id"]: s["hash"] for s in parsed()["skills"]}

    assert before["mp/tdd"] != after["mp/tdd"]
    assert before["mp/grilling"] != after["mp/grilling"]


def test_resolve_and_build_agree_with_renames(home: Path) -> None:
    skill(home / "mp" / "tdd", "/grilling and diagnosing-bugs\n")
    skill(home / "mp" / "grilling")
    skill(home / "mp" / "diagnosing-bugs")
    renaming('"mp/tdd" = "mp-tdd"\n"mp/grilling" = "mp-grilling"')
    lock = paths.package() / "skill-graft.lock"

    assert main(["resolve"]) == 0
    resolved = lock.read_bytes()
    assert main(["build", "--no-install"]) == 0

    assert lock.read_bytes() == resolved


def test_same_input(home: Path) -> None:
    skill(home / "own" / "tdd", "/notes\n")
    skill(home / "own" / "notes")
    configure(["own/tdd"], own="~/own")

    assert render() == render()


def test_new_lock_follows_the_umask(home: Path) -> None:
    configure([])
    old = os.umask(0o022)
    try:
        lock.write("one\n")
    finally:
        os.umask(old)

    file = home / ".apm" / "skill-graft" / "skill-graft.lock"
    assert stat.S_IMODE(file.stat().st_mode) == 0o644


def test_lock_keeps_its_mode(home: Path) -> None:
    configure([])
    lock.write("one\n")
    file = home / ".apm" / "skill-graft" / "skill-graft.lock"
    file.chmod(0o640)

    lock.write("two\n")

    assert stat.S_IMODE(file.stat().st_mode) == 0o640


def test_write_replaces_the_lock(home: Path) -> None:
    configure([])
    lock.write("one\n")
    lock.write("two\n")

    file = home / ".apm" / "skill-graft" / "skill-graft.lock"
    assert file.read_text() == "two\n"
    assert [p.name for p in file.parent.iterdir() if "lock" in p.name] == [file.name]
