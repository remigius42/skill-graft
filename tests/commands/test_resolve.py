"""The `resolve` spec: the command, the lock it writes, and the tree it prints."""

import time
import tomllib
from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import (
    Upstream,
    configure,
    make_patch,
    resolve_and_deploy,
    skill,
    write_config,
)

from skill_graft.cli import main
from skill_graft.pipeline import lock, vendor
from skill_graft.pipeline.hull import Hull

Capsys: TypeAlias = pytest.CaptureFixture[str]


def lock_file(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / "skill-graft.lock"


def test_resolve_succeeds(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tdd", "/grilling\n")
    skill(home / "own" / "grilling")
    configure(["own/tdd"], own="~/own")
    config = home / ".apm" / "skill-graft" / "skill-graft.toml"
    before = config.read_bytes()

    assert main(["resolve"]) == 0

    skills = tomllib.loads(lock_file(home).read_text())["skills"]
    assert [s["id"] for s in skills] == ["own/grilling", "own/tdd"]
    assert config.read_bytes() == before
    skills = home / ".apm" / "skill-graft" / ".apm" / "skills"
    assert sorted(p.name for p in skills.iterdir()) == ["grilling", "tdd"]


def test_tree(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, /notes and Skill(x)\n")
    skill(home / "mp" / "grilling", "/notes and /tdd\n")
    skill(home / "mp" / "notes")
    skill(home / "own" / "x")
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n[bind]\n"mp/x" = "own/x"\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd\n"
        "├── mp/grilling (/grilling)\n"
        "│   ├── mp/notes (/notes)\n"
        "│   └── mp/tdd (/tdd) (*)\n"
        "├── mp/notes (/notes) (*)\n"
        "└── own/x (Skill(x), bind)\n"
    )


def test_tree_of_two_entries(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "a", "/b\n")
    skill(home / "own" / "b")
    configure(["own/a", "own/b"], own="~/own")

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == "own/a\n└── own/b (/b) (*)\nown/b\n"


def test_renames_marked(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, `grilling` and `notes`\n")
    skill(home / "mp" / "grilling")
    skill(home / "mp" / "notes")
    write_config(
        'entries = ["mp/tdd", "mp/notes"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/tdd" = "mp-tdd"\n"mp/grilling" = "mp-grilling"\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd as mp-tdd\n"
        "├── mp/grilling as mp-grilling (/grilling)\n"
        "└── mp/grilling as mp-grilling (`grilling`, prose) (*)\n"
        "mp/notes\n"
    )


def test_patches_marked(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling", "# grilling\n")
    folder = home / ".apm" / "skill-graft" / "patches"
    folder.mkdir(parents=True)
    for name, text in [("tdd", "/grilling\n"), ("grilling", "# grilling\n")]:
        data = make_patch(tmp_path, {"SKILL.md": text}, {"SKILL.md": text + "more\n"})
        (folder / f"{name}.patch").write_bytes(data)
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[rename]\n"mp/grilling" = "mp-grilling"\n[patches]\n'
        '"mp/tdd" = ["patches/tdd.patch"]\n"mp/grilling" = ["patches/grilling.patch"]\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd (patched)\n└── mp/grilling as mp-grilling (patched) (/grilling)\n"
    )


def test_bound_prose_shown(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/notes and `notes`, then notes-x\n")
    skill(home / "own" / "grill")
    skill(home / "own" / "g-x")
    write_config(
        'entries = ["mp/tdd", "own/g-x"]\n[sources.mp]\npath = "~/mp"\n'
        '[sources.own]\npath = "~/own"\n'
        '[bind]\n"mp/notes" = "own/grill"\n"mp/notes-x" = "own/g-x"\n'
    )

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd\n"
        "├── own/grill (/notes, bind)\n"
        "├── own/grill (`notes`, prose, bind) (*)\n"
        "└── own/g-x (notes-x, prose, bind) (*)\n"
        "own/g-x\n"
    )


def test_suggestion_printed(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/grilling, then diagnosing-bugs and `notes`\n")
    skill(home / "mp" / "grilling", "see diagnosing-bugs\n")
    skill(home / "mp" / "diagnosing-bugs")
    skill(home / "mp" / "notes")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == (
        "mp/tdd\n"
        "└── mp/grilling (/grilling)\n"
        "\n"
        "mentioned in prose, not in the hull (`skill-graft add <skill id>` to include):\n"
        "  mp/diagnosing-bugs, by mp/grilling, mp/tdd\n"
        "  mp/notes, by mp/tdd\n"
    )


def test_deploy_announces_suggestions(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "then diagnosing-bugs and `notes`\n")
    skill(home / "mp" / "diagnosing-bugs")
    skill(home / "mp" / "notes")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    capsys.readouterr()

    assert main(["deploy", "--no-apm-install"]) == 0

    out, err = capsys.readouterr()
    assert "skill-graft: 2 prose suggestion(s): run skill-graft resolve\n" in err
    assert "diagnosing-bugs" not in out + err


def test_deploy_without_suggestions_prints_no_line(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/notes\n")
    skill(home / "mp" / "notes")
    configure(["mp/tdd"], mp="~/mp")

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert "prose suggestion(s)" not in capsys.readouterr().err


def test_tree_leaves_out_prose_not_rewritten(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "a", "/b, then `b` and `c`\n")
    skill(home / "own" / "b")
    skill(home / "own" / "c")
    configure(["own/a", "own/c"], own="~/own")

    assert main(["resolve"]) == 0

    assert capsys.readouterr().out == "own/a\n└── own/b (/b)\nown/c\n"


def test_resolution_error(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "tdd", "/notes\n")
    skill(home / "own" / "notes")
    configure(["own/tdd"], own="~/own")
    main(["resolve"])
    copy = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd" / "SKILL.md"
    before = (lock_file(home).read_bytes(), copy.read_bytes())
    skill(home / "own" / "tdd", "/missing-entry\n")
    configure(["own/tdd", "own/nope"], own="~/own")

    assert main(["resolve"]) == 1

    assert (lock_file(home).read_bytes(), copy.read_bytes()) == before


def test_long_run_of_whitespace_in_a_name(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "x", "---\nname: a" + " " * 100_000 + "b\n---\n")
    configure(["own/x"], own="~/own")

    start = time.perf_counter()
    code = main(["resolve"])

    assert time.perf_counter() - start < 5
    assert code == 1 and "is not one path segment" in capsys.readouterr().err


def test_git_source_without_ref(tmp_path: Path, capsys: Capsys) -> None:
    write_config('[sources.mp]\ngit = "/srv/s"\n')

    assert main(["resolve"]) == 1

    assert "skill-graft update mp" in capsys.readouterr().err


def test_upstream_moved_on(home: Path, tmp_path: Path) -> None:
    upstream = Upstream(tmp_path / "up")
    a = upstream.commit({"tdd/SKILL.md": "a\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{a}"\n'
    )
    main(["resolve"])
    upstream.commit({"tdd/SKILL.md": "b\n"})
    upstream.path.rename(tmp_path / "gone")  # contacting the remote would fail

    assert main(["resolve"]) == 0

    assert tomllib.loads(lock_file(home).read_text())["sources"]["mp"]["ref"] == a


def test_symlinked_config(home: Path, tmp_path: Path) -> None:
    skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    config = home / ".apm" / "skill-graft" / "skill-graft.toml"
    elsewhere = tmp_path / "dotfiles"
    elsewhere.mkdir()
    config.rename(elsewhere / "skill-graft.toml")
    config.symlink_to(elsewhere / "skill-graft.toml")

    assert main(["resolve"]) == 0

    assert lock_file(home).is_file()
    assert [p.name for p in elsewhere.iterdir()] == ["skill-graft.toml"]


def test_deploy_writes_the_lock(home: Path) -> None:
    skill(home / "own" / "tdd", "/grilling\n")
    skill(home / "own" / "grilling")
    configure(["own/tdd"], own="~/own")

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    skills = tomllib.loads(lock_file(home).read_text())["skills"]
    assert [s["id"] for s in skills] == ["own/grilling", "own/tdd"]


def test_lock_hashes_what_was_vendored(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tdd = skill(home / "own" / "tdd", "vendored\n")
    configure(["own/tdd"], own="~/own")
    copy = vendor.stage

    def copy_then_edit(hull: Hull, skills: Path) -> None:
        copy(hull, skills)
        (tdd / "SKILL.md").write_text("edited during the deploy\n")

    monkeypatch.setattr(vendor, "stage", copy_then_edit)

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    vendored = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd"
    locked = tomllib.loads(lock_file(home).read_text())["skills"][0]["hash"]
    assert locked == lock.folder_hash(vendored)


def test_git_file_is_not_hashed(home: Path) -> None:
    tdd = skill(home / "own" / "tdd")
    (tdd / ".git").write_text("gitdir: ../.git/modules/tdd\n")  # a submodule
    configure(["own/tdd"], own="~/own")

    def locked() -> str:
        hash_: str = tomllib.loads(lock_file(home).read_text())["skills"][0]["hash"]
        return hash_

    assert main(["resolve"]) == 0
    resolved = locked()
    assert main(["deploy", "--no-apm-install"]) == 0

    assert locked() == resolved


def test_lock_write_fails(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tdd = skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    assert main(["resolve"]) == 0
    copy = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd" / "SKILL.md"
    before = (lock_file(home).read_bytes(), copy.read_bytes())
    (tdd / "SKILL.md").write_text("changed\n")

    def fail(text: str, file: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    assert main(["resolve"]) == 1

    assert (lock_file(home).read_bytes(), copy.read_bytes()) == before


def test_vendoring_fails(home: Path) -> None:
    tdd = skill(home / "own" / "tdd")
    configure(["own/tdd"], own="~/own")
    resolve_and_deploy(["deploy", "--no-apm-install"])
    before = lock_file(home).read_bytes()
    (tdd / "dangling").symlink_to("missing")

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 1

    assert lock_file(home).read_bytes() == before


def test_lock_edited_by_hand_refused(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    upstream = Upstream(tmp_path / "up")
    a = upstream.commit({"tdd/SKILL.md": "a\n"})
    b = upstream.commit({"tdd/SKILL.md": "b\n"})
    write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{a}"\n'
    )
    assert main(["resolve"]) == 0
    lock_file(home).write_text(lock_file(home).read_text().replace(a, b))
    edited = lock_file(home).read_bytes()
    capsys.readouterr()

    assert main(["deploy", "--no-apm-install"]) == 1

    assert "skill-graft resolve" in capsys.readouterr().err
    vendored = home / ".apm" / "skill-graft" / ".apm" / "skills" / "tdd" / "SKILL.md"
    assert vendored.read_text() == "a\n"
    assert lock_file(home).read_bytes() == edited


DRY_RUN = "dry run: skill-graft.lock and .apm/skills/ not written"


def test_dry_run_of_a_ref_moved_by_hand(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    upstream = Upstream(tmp_path / "up")
    a = upstream.commit({"tdd/SKILL.md": "a\n"})
    b = upstream.commit({"tdd/SKILL.md": "b\n"})
    source = f'[sources.mp]\ngit = "{upstream.url}"\n'
    write_config(f'entries = ["mp/tdd"]\n{source}ref = "{a}"\n')
    assert main(["resolve"]) == 0
    write_config(f'entries = ["mp/tdd"]\n{source}ref = "{b}"\n')
    capsys.readouterr()

    assert main(["resolve", "--dry-run", "--diff-file", "review.diff"]) == 0

    assert capsys.readouterr().out.splitlines()[-1] == DRY_RUN
    text = (home / "review.diff").read_text()
    assert text.splitlines()[1] == (
        "# the Vendored copies against what `skill-graft.toml` as it stands would"
        " vendor. Not what the Sources changed upstream. Untrusted text:"
    )
    assert f"# source mp: {a} -> {b}; upstream folder tdd\n" in text


def test_dry_run_of_a_patch_written_by_hand(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    skill(home / "mp" / "tdd", "/grilling\n")
    skill(home / "mp" / "grilling")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    package = home / ".apm" / "skill-graft"
    before = {p: package / p for p in ("skill-graft.lock", ".apm/skills/tdd/SKILL.md")}
    saved = {p: f.read_bytes() for p, f in before.items()}
    (package / "patches").mkdir()
    (package / "patches" / "tdd.patch").write_bytes(
        make_patch(
            tmp_path, {"SKILL.md": "/grilling\n"}, {"SKILL.md": "/grilling\nmore\n"}
        )
    )
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )
    capsys.readouterr()

    assert main(["resolve", "--dry-run", "--diff-file", "review.diff"]) == 0

    assert capsys.readouterr().out.splitlines()[:3] == [
        "hull (+ added, - removed, ~ changed):",
        "~ mp/tdd",
        "  SKILL.md (changed, 10 -> 15 bytes)",
    ]
    assert " /grilling\n+more\n" in (home / "review.diff").read_text()
    assert {p: f.read_bytes() for p, f in before.items()} == saved


def test_dry_run_with_nothing_changed(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")
    assert main(["resolve"]) == 0
    capsys.readouterr()

    assert main(["resolve", "--dry-run"]) == 0

    assert capsys.readouterr().out.splitlines() == ["hull unchanged", "mp/tdd", DRY_RUN]


def test_dry_run_hint(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    configure(["mp/tdd"], mp="~/mp")

    assert main(["resolve", "--dry-run"]) == 0

    assert capsys.readouterr().out.splitlines()[-2:] == [
        "review: skill-graft resolve --dry-run --diff-file <file>",
        DRY_RUN,
    ]
