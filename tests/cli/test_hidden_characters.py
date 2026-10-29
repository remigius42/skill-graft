"""The `hidden-characters` spec end to end, through each command it names."""

from pathlib import Path
from typing import TypeAlias

import pytest
from conftest import FakeApm, Upstream, configure, skill, vendored, write_config

from skill_graft.cli import main
from skill_graft.infra import paths
from skill_graft.pipeline import config

Capsys: TypeAlias = pytest.CaptureFixture[str]

TAG = "\U000e0041"
LRI = "\N{LEFT-TO-RIGHT ISOLATE}"


def run(capsys: Capsys, *args: str) -> tuple[int, str, str]:
    code = main(list(args))
    out, err = capsys.readouterr()
    return code, out, err


def test_resolve(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "a\n" * 6 + f"x{TAG}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, out, err = run(capsys, "resolve")

    assert (code, out) == (1, "")
    assert err.endswith(
        "skill-graft: hidden characters:\n"
        f"  mp/tdd: {home}/mp/tdd/SKILL.md:7: U+E0041 (tag character)\n"
    )
    assert not (home / ".apm" / "skill-graft" / "skill-graft.lock").exists()


def test_debris_warns(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "a\nb\n\N{ZERO WIDTH SPACE}c\N{ZERO WIDTH SPACE}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, _, err = run(capsys, "resolve")

    assert code == 0
    assert err.endswith(
        f"skill-graft: warning: {home}/mp/tdd/SKILL.md:3: 2 invisible characters, "
        "the first U+200B\n"
    )


def test_build_into_stays_empty(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", f"{TAG}\n")
    configure(["mp/tdd"], mp="~/mp")
    into = tmp_path / "into"
    into.mkdir()

    code, _, err = run(capsys, "build", "--into", str(into))

    assert code == 1 and "U+E0041" in err
    assert list(into.iterdir()) == []


def test_build_runs_no_apm(home: Path, fake_apm: FakeApm, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", f"{TAG}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, _, err = run(capsys, "build")

    assert code == 1 and "U+E0041" in err
    assert fake_apm.calls == []
    assert vendored() == set()


def test_update_keeps_the_ref(tmp_path: Path, capsys: Capsys) -> None:
    upstream = Upstream(tmp_path / "up")
    old = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    upstream.commit({"tdd/SKILL.md": f"# tdd\n{TAG}\n"})
    file = write_config(
        f'entries = ["mp/tdd"]\n[sources.mp]\ngit = "{upstream.url}"\nref = "{old}"\n'
    )
    before = file.read_bytes()

    code, _, err = run(capsys, "update", "mp")

    assert code == 1 and "U+E0041" in err
    assert file.read_bytes() == before


def test_add_keeps_the_config(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes", f"{TAG}\n")
    file = write_config('entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n')
    before = file.read_bytes()

    code, _, err = run(capsys, "add", "mp/notes")

    assert code == 1 and "U+E0041" in err
    assert file.read_bytes() == before


def test_remove_the_skill_holding_one(
    scope: paths.Scope, home: Path, capsys: Capsys
) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "mp" / "notes", f"{TAG}\n")
    configure(["mp/tdd", "mp/notes"], mp="~/mp")

    code, _, _ = run(capsys, "remove", "mp/notes")

    assert code == 0
    assert config.load(scope).entries == [config.SkillId("mp", "tdd")]


def test_why_prints_the_path_first(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/deep\n")
    skill(home / "mp" / "deep", f"{LRI}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, out, err = run(capsys, "why", "mp/deep")

    assert code == 1
    assert out == (
        f"mp/deep\n└─← mp/tdd (/deep) (entry)\nupstream: {home / 'mp' / 'deep'}\n"
    )
    assert err == (
        "skill-graft: hidden characters:\n"
        f"  mp/deep: {home}/mp/deep/SKILL.md:1: U+2066 (bidi control)\n"
    )


def test_tree_prints_the_hull_first(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/deep\n")
    skill(home / "mp" / "deep", f"{LRI}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, out, err = run(capsys, "tree")

    assert code == 1
    assert out == "mp/tdd\n└── mp/deep (/deep)\n"
    assert "U+2066" in err


def test_why_after_a_failing_patch_prints_nothing(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", "/deep\n")
    skill(home / "mp" / "deep", f"{LRI}\n")
    patches = home / ".apm" / "skill-graft" / "patches"
    patches.mkdir(parents=True)
    (patches / "tdd.patch").write_text(
        "--- a/SKILL.md\n+++ b/SKILL.md\n@@ -1 +1 @@\n-gone\n+new\n"
    )
    write_config(
        'entries = ["mp/tdd"]\n[sources.mp]\npath = "~/mp"\n'
        '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n'
    )

    code, out, err = run(capsys, "why", "mp/tdd")

    assert (code, out) == (1, "")
    assert "patches do not apply:" in err


def test_why_an_unknown_skill_still_reports_them(home: Path, capsys: Capsys) -> None:
    skill(home / "mp" / "tdd", f"{TAG}\n")
    configure(["mp/tdd"], mp="~/mp")

    code, _, err = run(capsys, "why", "mp/gone")

    assert code == 1
    assert "mp/gone" in err and "U+E0041" in err
