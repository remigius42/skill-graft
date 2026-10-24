"""The lock's content (the `resolve` spec): sources, skills, edges, hashes."""

import os
from dataclasses import replace
import stat
import tomllib
from pathlib import Path
from typing import Any

from conftest import Upstream, configure, make_patch, skill, write_config

from skill_graft.cli import main
from skill_graft.infra import paths
from skill_graft.pipeline import compute, config, lock


def render() -> str:
    loaded = config.load()
    with compute.compute_hull(loaded) as hull:
        return lock.render(loaded, {}, hull)


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

    assert skills["mp/tdd"]["upstream"] == "skills/tdd"
    assert skills["own/chisel"]["upstream"] == "chisel"


def test_skill_at_the_source_root(home: Path) -> None:
    skill(home / "own")
    write_config('entries = ["own/own"]\n[sources.own]\npath = "~/own"\n')

    assert [s["upstream"] for s in parsed()["skills"]] == ["."]


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


def test_hash_value_is_stable(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# s\n")
    (folder / "sub").mkdir()
    (folder / "sub" / "run.sh").write_text("echo\n")
    (folder / "sub" / "run.sh").chmod(0o755)
    (folder / ".git").mkdir()
    (folder / ".git" / "HEAD").write_text("x\n")
    (folder / "link.md").symlink_to("SKILL.md")

    assert lock.folder_hash(folder) == (
        "sha256:6a8c71ed184542457c2c601c1c755bfae8244a0034d488bfb9a541da9638c75d"
    )
    assert lock.folder_hash(folder, {Path("SKILL.md"): b"# t\n"}) == (
        "sha256:766a8278496236e3a888b1a7ddf33a861b85f515c476070f281d67153b5631be"
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


def test_header_first_when_empty(home: Path) -> None:
    skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")

    lines = render().splitlines()

    assert lines[0] == "# Written by skill-graft; update reads its hashes. Do not edit."
    assert parsed()["edges"] == parsed()["suggestions"] == []


def test_header_first_when_the_hull_is_empty(home: Path) -> None:
    (home / "own").mkdir()
    configure([], own="~/own")

    assert render().startswith(
        "# Written by skill-graft; update reads its hashes. Do not edit.\n"
    )
    assert parsed()["skills"] == []


def test_version_1_keys(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    tdd = "# tdd\n/g, then `diagnosing-bugs`\n"
    sha = upstream.commit(
        {
            "pack/tdd/SKILL.md": tdd,
            "pack/diagnosing-bugs/SKILL.md": "# diagnosing-bugs\n",
        }
    )
    skill(home / "own" / "chisel")
    skill(home / "own" / "notes")
    package = home / ".apm" / "skill-graft"
    (package / "patches").mkdir(parents=True)
    (package / "patches" / "tdd.patch").write_bytes(
        make_patch(tmp_path, {"SKILL.md": tdd}, {"SKILL.md": tdd + "patched\n"})
    )
    write_config(
        'entries = ["cp/tdd", "own/chisel"]\n'
        f'[sources.cp]\ngit = "{upstream.url}"\nref = "{sha}"\nsubdirectory = "pack"\n'
        '[sources.own]\npath = "~/own"\n'
        '[rename]\n"cp/tdd" = "cp-tdd"\n'
        '[patches]\n"cp/tdd" = ["patches/tdd.patch"]\n'
        '[bind]\n"cp/g" = "own/notes"\n'
    )

    lock_data = parsed()
    skills = {s["id"]: s for s in lock_data["skills"]}
    keys = {
        "top": set(lock_data),
        "git source": set(lock_data["sources"]["cp"]),
        "path source": set(lock_data["sources"]["own"]),
        "renamed, patched skill": set(skills["cp/tdd"]),
        "plain entry": set(skills["own/chisel"]),
        "bound edge": set(lock_data["edges"][0]),
        "suggestion": set(lock_data["suggestions"][0]),
    }

    assert lock_data["version"] == 1
    assert lock_data["edges"][0]["bind"] is True
    assert keys == {
        "top": {"version", "sources", "skills", "edges", "suggestions"},
        "git source": {"git", "ref", "subdirectory"},
        "path source": {"path"},
        "renamed, patched skill": {
            "id",
            "entry",
            "deployed",
            "upstream",
            "patches",
            "hash",
        },
        "plain entry": {"id", "entry", "upstream", "hash"},
        "bound edge": {"from", "to", "kind", "bind"},
        "suggestion": {"id", "from"},
    }, "the lock's layout changed: raise its `version` (and the graft-check skill's)"


def digest() -> str:
    with compute.compute_hull(config.load()) as hull:
        return lock.digest(hull, lock.skill_hashes(hull))


def test_digest_ignores_the_order_reached(home: Path) -> None:
    skill(home / "own" / "tdd")
    skill(home / "own" / "grilling")
    configure(["own/tdd", "own/grilling"], own="~/own")
    first = digest()
    configure(["own/grilling", "own/tdd"], own="~/own")

    assert digest() == first
    assert len(first) == 64 and first == first.lower()


def test_digest_follows_a_hash(home: Path) -> None:
    folder = skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    first = digest()
    (folder / "SKILL.md").write_text("changed\n")

    assert digest() != first


def test_digest_follows_a_deployed_name_alone(home: Path) -> None:
    skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    with compute.compute_hull(config.load()) as hull:
        hashes = lock.skill_hashes(hull)
        renamed = replace(
            hull, deployed={skill_id: "other" for skill_id in hull.deployed}
        )

        assert lock.digest(renamed, hashes) != lock.digest(hull, hashes)
