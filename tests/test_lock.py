"""The lock's content (the `resolve` spec): sources, skills, edges, hashes."""

import tomllib
from pathlib import Path
from typing import Any

from conftest import configure, skill, write_config

from skill_graft import config, lock, paths, resolve
from skill_graft.cache import Cache


def render() -> str:
    loaded = config.load()
    folders = resolve.folders(loaded, Cache(paths.cache()), {})
    return lock.render(loaded, {}, resolve.resolve(loaded, folders))


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


def test_same_input(home: Path) -> None:
    skill(home / "own" / "tdd", "/notes\n")
    skill(home / "own" / "notes")
    configure(["own/tdd"], own="~/own")

    assert render() == render()


def test_write_replaces_the_lock(home: Path) -> None:
    configure([])
    lock.write("one\n")
    lock.write("two\n")

    file = home / ".apm" / "skill-graft" / "skill-graft.lock"
    assert file.read_text() == "two\n"
    assert [p.name for p in file.parent.iterdir() if "lock" in p.name] == [file.name]
