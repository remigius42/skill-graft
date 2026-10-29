import os
import shutil
import tempfile
from pathlib import Path

import pytest
from conftest import FakeApm, Upstream, deadline, skill, write_config

from skill_graft.cli import main
from skill_graft.infra import paths
from skill_graft.pipeline import compute, config, lock, vendor
from skill_graft.pipeline.hull import Hull


def skills_dir(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / ".apm" / "skills"


def test_whole_folder_copied(home: Path) -> None:
    source = skill(home / "src" / "chisel")
    (source / "refs").mkdir()
    (source / "refs" / "notes.bin").write_bytes(b"notes\x00\xff")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    vendored = skills_dir(home) / "chisel"
    assert (vendored / "SKILL.md").read_text() == "# skill\n"
    assert (vendored / "refs" / "notes.bin").read_bytes() == b"notes\x00\xff"


def test_removed_entry(home: Path) -> None:
    skill(home / "src" / "chisel")
    skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    main(["build", "--no-install"])
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["tdd"]


def test_referenced_skill_vendored(home: Path) -> None:
    skill(home / "src" / "tdd", "Run /grilling.\n")
    skill(home / "src" / "grilling")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["grilling", "tdd"]


def test_skill_no_longer_referenced_is_removed(home: Path) -> None:
    tdd = skill(home / "src" / "tdd", "Run /grilling.\n")
    skill(home / "src" / "grilling")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')
    main(["build", "--no-install"])
    (tdd / "SKILL.md").write_text("Nothing.\n")

    assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["tdd"]


def test_warning_does_not_stop_build(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "src" / "tdd", "Run /foo.\n")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    assert "skill-graft: warning: `own/tdd` calls `/foo`" in capsys.readouterr().err


def test_symlink_in_a_referenced_skill(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "src" / "tdd", "Run /grilling.\n")
    grilling = skill(home / "src" / "grilling")
    (grilling / "out").symlink_to(home / "secret")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 1

    assert "out" in capsys.readouterr().err and not skills_dir(home).exists()


def unreadable(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file `secret` the copy cannot read, though resolution reads it."""
    (folder / "secret").write_text("x")
    copy2 = shutil.copy2

    def refuse(source: str, target: str) -> object:
        if Path(source).name == "secret":
            raise PermissionError(13, "Permission denied", source)
        return copy2(source, target)

    monkeypatch.setattr(shutil, "copy2", refuse)  # as `vendor` calls it


def test_failed_build_announces_no_suggestions(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable(skill(home / "src" / "tdd", "then diagnosing-bugs\n"), monkeypatch)
    skill(home / "src" / "diagnosing-bugs")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 1

    assert "prose suggestion(s)" not in capsys.readouterr().err


def test_copy_fails(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "chisel")
    broken = skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    main(["build", "--no-install"])
    unreadable(broken, monkeypatch)
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 1

    err = capsys.readouterr().err
    assert "copying" in err and "secret" in err
    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["chisel"]
    assert not (skills_dir(home).parent / "skills.new").exists()


def test_crash_between_the_renames_keeps_the_previous_build(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "chisel")
    broken = skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    main(["build", "--no-install"])
    # A run killed after moving skills/ aside and before moving skills.new/ in.
    skills_dir(home).rename(skills_dir(home).with_name("skills.old"))
    skill(skills_dir(home).with_name("skills.new") / "half")
    unreadable(broken, monkeypatch)
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 1

    assert sorted(p.name for p in skills_dir(home).parent.iterdir()) == ["skills"]
    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["chisel"]


def test_undeletable_stale_folder(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    build_one_skill(home)
    locked = skill(skills_dir(home).with_name("skills.new") / "half")
    locked.chmod(0o500)
    try:
        assert main(["build", "--no-install"]) == 1
    finally:
        locked.chmod(0o700)

    assert "skills.new" in capsys.readouterr().err


def test_clash_is_reported_before_searching(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (home / "mp").mkdir()
    skill(home / "own" / "tdd")
    write_config(
        'entries = ["mp/tdd", "own/tdd"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.own]\npath = "~/own"\n'
    )

    assert main(["build", "--no-install"]) == 1

    assert "deployed name 'tdd'" in capsys.readouterr().err


def test_entries_clash_before_any_fetch(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n"})
    skill(home / "own" / "tdd")
    write_config(
        'entries = ["mp/tdd", "own/tdd"]\n'
        f'[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
        '[sources.own]\npath = "~/own"\n'
    )

    assert main(["build", "--no-install"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/tdd" in err
    assert not paths.cache().exists()


def test_missing_ref_before_entries_clash(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "own" / "tdd")
    write_config(
        'entries = ["mp/tdd", "own/tdd"]\n'
        f'[sources.mp]\ngit = "{tmp_path / "nowhere"}"\n'
        '[sources.own]\npath = "~/own"\n'
    )

    assert main(["build", "--no-install"]) == 1

    assert "skill-graft update mp" in capsys.readouterr().err


def test_clash_ignores_case(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "TDD")
    write_config(
        'entries = ["mp/tdd", "own/TDD"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.own]\npath = "~/own"\n'
    )

    assert main(["build", "--no-install"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/TDD" in err
    assert "'TDD'" in err and "'tdd'" in err


def test_clash_across_sources(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "tdd")
    skill(home / "own" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/own"\n')
    main(["build", "--no-install"])
    write_config(
        'entries = ["mp/tdd", "own/tdd"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.own]\npath = "~/own"\n'
    )

    assert main(["build", "--no-install"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/tdd" in err
    assert sorted(p.name for p in skills_dir(home).parent.iterdir()) == ["skills"]
    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["chisel"]


@pytest.mark.parametrize(
    ("link", "target"),
    [
        ("ext", "../../shared"),
        ("notes.md", "../../shared/notes.md"),
        ("self", "."),
        ("inner", "refs"),
    ],
    ids=["folder outside", "file outside", "cycle", "folder inside"],
)
def test_symlink_leaving_the_skill_writes_nothing(
    home: Path, capsys: pytest.CaptureFixture[str], link: str, target: str
) -> None:
    (home / "shared").mkdir()
    (home / "shared" / "notes.md").write_text("outside\n")
    chisel = skill(home / "src" / "chisel")
    (chisel / "refs").mkdir()
    (chisel / link).symlink_to(target)
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 1

    assert f"chisel/{link}" in capsys.readouterr().err
    assert not skills_dir(home).parent.exists()


def test_symlink_in_git_metadata_is_ignored(home: Path) -> None:
    chisel = skill(home / "chisel")
    (chisel / ".git").mkdir()
    (chisel / ".git" / "hook").symlink_to(home)
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/chisel"\n')

    assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in (skills_dir(home) / "chisel").iterdir()) == [
        "SKILL.md"
    ]


def test_symlink_loop_is_an_error(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chisel = skill(home / "src" / "chisel")
    (chisel / "loop").symlink_to("loop")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 1

    assert "chisel/loop" in capsys.readouterr().err


def test_symlink_inside_the_skill_is_copied(home: Path) -> None:
    chisel = skill(home / "src" / "chisel")
    (chisel / "refs").mkdir()
    (chisel / "refs" / "notes.md").write_text("inside\n")
    (chisel / "notes.md").symlink_to("refs/notes.md")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    copied = skills_dir(home) / "chisel" / "notes.md"
    assert not copied.is_symlink() and copied.read_text() == "inside\n"


def test_skill_md_linked_to_a_device(home: Path) -> None:
    skill(home / "src" / "tdd")
    (home / "src" / "x").mkdir()
    (home / "src" / "x" / "SKILL.md").symlink_to("/dev/zero")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    with deadline():
        assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["tdd"]


def test_entry_names_a_fifo(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (home / "src" / "x").mkdir(parents=True)
    os.mkfifo(home / "src" / "x" / "SKILL.md")
    write_config('entries = ["own/x"]\n[sources.own]\npath = "~/src"\n')

    with deadline():
        assert main(["build", "--no-install"]) == 1

    assert "x/SKILL.md: not a regular file" in capsys.readouterr().err


def test_git_metadata_is_not_vendored(home: Path) -> None:
    source = skill(home / "chisel")
    (source / ".git").mkdir()
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/chisel"\n')

    assert main(["build", "--no-install"]) == 0

    assert sorted(p.name for p in (skills_dir(home) / "chisel").iterdir()) == [
        "SKILL.md"
    ]


def test_no_install_does_not_run_apm(home: Path, fake_apm: FakeApm) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--no-install"]) == 0

    assert (skills_dir(home) / "chisel" / "SKILL.md").exists()
    assert fake_apm.calls == []


def build_one_skill(home: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')


def test_apm_succeeds(
    home: Path, fake_apm: FakeApm, capfd: pytest.CaptureFixture[str]
) -> None:
    build_one_skill(home)

    assert main(["build"]) == 0

    assert fake_apm.calls == [["install", "-g", str(home / ".apm" / "skill-graft")]]
    assert "fake apm: install -g" in capfd.readouterr().out


def test_apm_exits_non_zero(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    build_one_skill(home)
    fake_apm.exit_code = 7

    assert main(["build"]) == 1

    assert "exit code 7" in capsys.readouterr().err


def test_apm_missing(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_one_skill(home)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert main(["build"]) == 1

    assert "APM is not installed" in capsys.readouterr().err
    assert (skills_dir(home) / "chisel").exists()


def test_apm_not_executable(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_one_skill(home)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "apm").write_text("#!/bin/sh\n")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    assert main(["build"]) == 1

    assert "skill-graft: " in capsys.readouterr().err


@pytest.mark.parametrize("manifest", [None, "dependencies:\n  apm:\n    - /other\n"])
def test_package_not_registered(
    home: Path,
    fake_apm: FakeApm,
    capsys: pytest.CaptureFixture[str],
    manifest: str | None,
) -> None:
    build_one_skill(home)
    fake_apm.register = False
    if manifest is not None:
        (home / ".apm" / "apm.yml").write_text(manifest)

    assert main(["build"]) == 1

    err = capsys.readouterr().err
    assert str(home / ".apm" / "apm.yml") in err
    assert str(home / ".apm" / "skill-graft") in err


@pytest.mark.parametrize(
    "item",
    [
        "- ~/.apm/skill-graft",
        "- '~/.apm/skill-graft/'",
        '- "{package}"',
        "- path: {package}",
        "- path: ~/.apm/skill-graft # pinned",
    ],
)
def test_listed_forms(home: Path, fake_apm: FakeApm, item: str) -> None:
    build_one_skill(home)
    fake_apm.register = False
    line = item.format(package=home / ".apm" / "skill-graft")
    (home / ".apm" / "apm.yml").write_text(f"dependencies:\n  apm:\n    {line}\n")

    assert main(["build"]) == 0


def test_symlinked_home(
    home: Path, tmp_path: Path, fake_apm: FakeApm, monkeypatch: pytest.MonkeyPatch
) -> None:
    link = tmp_path / "link-home"
    link.symlink_to(home)
    monkeypatch.setenv("HOME", str(link))
    build_one_skill(link)
    fake_apm.register = False
    (home / ".apm" / "apm.yml").write_text(
        f"dependencies:\n  apm:\n    - {home / '.apm' / 'skill-graft'}\n"
    )

    assert main(["build"]) == 0


def test_registration_removed_by_hand(home: Path, fake_apm: FakeApm) -> None:
    build_one_skill(home)
    manifest = home / ".apm" / "apm.yml"
    manifest.write_text("dependencies:\n  apm:\n    - /other\n")

    assert main(["build"]) == 0

    assert f"- {home / '.apm' / 'skill-graft'}" in manifest.read_text()


def test_vendor_and_lock_into_a_given_folder(
    scope: paths.Scope, home: Path, tmp_path: Path
) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = tmp_path / "into"

    with compute.compute_hull(scope, config.load(scope)) as hull:
        vendor.vendor(hull, into / ".apm" / "skills")
    lock.write("lock\n", into / "skill-graft.lock")

    assert (into / ".apm" / "skills" / "chisel" / "SKILL.md").is_file()
    assert (into / "skill-graft.lock").read_text() == "lock\n"
    package = home / ".apm" / "skill-graft"
    assert sorted(p.name for p in package.iterdir()) == ["skill-graft.toml"]


def snapshot(folder: Path) -> dict[str, bytes]:
    """Each file under `folder` by relative path, with its bytes."""
    return {
        str(f.relative_to(folder)): f.read_bytes()
        for f in sorted(folder.rglob("*"))
        if f.is_file()
    }


def empty_folder(tmp_path: Path) -> Path:
    into = tmp_path / "into"
    into.mkdir()
    return into


def test_throwaway_build(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "tdd", "Run /grilling.\n")
    skill(home / "src" / "grilling")
    write_config(
        'entries = ["own/tdd"]\n[rename]\n"own/grilling" = "grill"\n'
        '[sources.own]\npath = "~/src"\n'
    )
    into = empty_folder(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "no-apm"))

    assert main(["build", "--into", str(into)]) == 0

    vendored = sorted(p.name for p in (into / ".apm" / "skills").iterdir())
    assert vendored == ["grill", "tdd"]
    assert 'id = "own/grilling"' in (into / "skill-graft.lock").read_text()


def test_package_untouched(home: Path, tmp_path: Path) -> None:
    chisel = skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    assert main(["build", "--no-install"]) == 0
    package = home / ".apm" / "skill-graft"
    before = snapshot(package)
    (chisel / "SKILL.md").write_text("# changed\n")
    into = empty_folder(tmp_path)

    assert main(["build", "--into", str(into)]) == 0

    assert snapshot(package) == before
    vendored = into / ".apm" / "skills" / "chisel" / "SKILL.md"
    assert vendored.read_text() == "# changed\n"


def test_package_never_built(home: Path, tmp_path: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["build", "--into", str(empty_folder(tmp_path))]) == 0

    package = home / ".apm" / "skill-graft"
    assert sorted(p.name for p in package.iterdir()) == ["skill-graft.toml"]


def test_same_lock(home: Path, tmp_path: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)

    assert main(["build", "--into", str(into)]) == 0
    assert main(["build", "--no-install"]) == 0

    package_lock = home / ".apm" / "skill-graft" / "skill-graft.lock"
    assert (into / "skill-graft.lock").read_bytes() == package_lock.read_bytes()


def unreadable_entry(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    skill(home / "src" / "chisel")
    unreadable(skill(home / "src" / "tdd", "Run /chisel.\n"), monkeypatch)
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')


def test_vendoring_into_the_folder_fails(
    home: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unreadable_entry(home, monkeypatch)
    into = empty_folder(tmp_path)

    assert main(["build", "--into", str(into)]) == 1

    assert "secret" in capsys.readouterr().err
    assert list(into.iterdir()) == []


def test_lock_write_fails(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)

    def fail(text: str, file: Path | None = None) -> None:
        assert file is not None
        file.write_text(text[:10])
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    assert main(["build", "--into", str(into)]) == 1

    assert list(into.iterdir()) == []


def test_interrupted(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)
    copy = vendor.vendor

    def copy_then_interrupt(hull: Hull, skills: Path | None = None) -> None:
        copy(hull, skills)
        raise KeyboardInterrupt

    monkeypatch.setattr(vendor, "vendor", copy_then_interrupt)

    with pytest.raises(KeyboardInterrupt):
        main(["build", "--into", str(into)])

    assert list(into.iterdir()) == []


def test_foreign_file_kept(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable_entry(home, monkeypatch)
    into = empty_folder(tmp_path)
    copy = vendor.vendor

    def another_process_writes_first(hull: Hull, skills: Path | None = None) -> None:
        (into / ".apm").mkdir()
        (into / ".apm" / "x").write_text("theirs\n")
        copy(hull, skills)

    monkeypatch.setattr(vendor, "vendor", another_process_writes_first)

    assert main(["build", "--into", str(into)]) == 1

    assert snapshot(into) == {".apm/x": b"theirs\n"}
    assert sorted(p.name for p in (into / ".apm").iterdir()) == ["x"]


def test_temporary_folder_inside_it(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable_entry(home, monkeypatch)
    into = empty_folder(tmp_path)
    monkeypatch.setattr(tempfile, "tempdir", str(into))

    assert main(["build", "--into", str(into)]) == 1

    assert list(into.iterdir()) == []


def chisel_config(home: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')


def test_into_a_missing_folder(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chisel_config(home)
    into = tmp_path / "into"

    assert main(["build", "--into", str(into)]) == 1

    assert f"skill-graft: --into {into}: no such folder" in capsys.readouterr().err
    assert not into.exists()


@pytest.mark.parametrize("kind", ["file", "folder holding a file"])
def test_into_not_empty(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    chisel_config(home)
    into = tmp_path / "into"
    if kind == "file":
        into.write_text("mine\n")
    else:
        into.mkdir()
        (into / "mine").write_text("mine\n")

    assert main(["build", "--into", str(into)]) == 1

    err = capsys.readouterr().err
    assert f"skill-graft: --into {into}: " in err
    assert "not a folder" in err if kind == "file" else "not empty" in err
    if kind == "file":
        assert into.read_text() == "mine\n"
    else:
        assert snapshot(into) == {"mine": b"mine\n"}


def test_into_refused_before_the_config_loads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config("not toml [\n")
    into = tmp_path / "into"
    into.mkdir()
    (into / "mine").write_text("mine\n")

    assert main(["build", "--into", str(into)]) == 1

    lines = capsys.readouterr().err.splitlines()
    assert lines[0].startswith("skill-graft: package: ")
    assert lines[1] == f"skill-graft: into: {into}"
    assert lines[2].startswith(f"skill-graft: --into {into}: ")


def test_into_a_symlink_to_an_empty_folder(home: Path, tmp_path: Path) -> None:
    chisel_config(home)
    target = empty_folder(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(target)

    assert main(["build", "--into", str(link)]) == 0

    assert (target / ".apm" / "skills" / "chisel" / "SKILL.md").is_file()


def test_into_a_path_only_passing_through_a_package(home: Path, tmp_path: Path) -> None:
    chisel_config(home)
    (tmp_path / "other" / ".apm" / "skill-graft").mkdir(parents=True)
    out = empty_folder(tmp_path)
    into = tmp_path / "other" / ".apm" / "skill-graft" / ".." / ".." / ".." / "into"

    assert main(["build", "--into", str(into)]) == 0

    assert (out / ".apm" / "skills" / "chisel" / "SKILL.md").is_file()


@pytest.mark.parametrize(
    "where",
    [
        "home/.apm/skill-graft/tmp",
        "other/.apm/skill-graft/tmp",
        "other/.APM/Skill-Graft/tmp",
        "link/tmp",  # `link` leads into the package
    ],
)
def test_into_a_package(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], where: str
) -> None:
    chisel_config(home)
    package = home / ".apm" / "skill-graft"
    (tmp_path / "link").symlink_to(package)
    into = tmp_path / where
    into.mkdir(parents=True)
    before = snapshot(package)

    assert main(["build", "--into", str(into)]) == 1

    err = capsys.readouterr().err
    assert f"skill-graft: --into {into}: inside a package" in err
    assert snapshot(package) == before and list(into.iterdir()) == []


@pytest.mark.parametrize("linked", [False, True])
def test_into_the_cache(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    linked: bool,
) -> None:
    chisel_config(home)
    cache = tmp_path / "cache"
    cache.mkdir()
    if linked:
        (tmp_path / "cache-link").symlink_to(cache)
    monkeypatch.setenv(
        "XDG_CACHE_HOME", str(tmp_path / ("cache-link" if linked else "cache"))
    )
    into = cache / "skill-graft" / "tmp"
    into.mkdir(parents=True)

    assert main(["build", "--into", str(into)]) == 1

    assert f"skill-graft: --into {into}: overlaps the cache" in capsys.readouterr().err
    assert list(into.iterdir()) == []


def test_cache_inside_the_folder(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chisel_config(home)
    into = empty_folder(tmp_path)
    monkeypatch.setenv("XDG_CACHE_HOME", str(into / "cache"))

    assert main(["build", "--into", str(into)]) == 1

    assert f"skill-graft: --into {into}: overlaps the cache" in capsys.readouterr().err
    assert list(into.iterdir()) == []


@pytest.mark.parametrize("where", ["src/tmp", "empty"])
def test_into_a_source(
    home: Path, capsys: pytest.CaptureFixture[str], where: str
) -> None:
    skill(home / "src" / "chisel")
    (home / "empty").mkdir()
    write_config(
        'entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n'
        '[sources.none]\npath = "~/empty"\n'
    )
    into = home / where
    into.mkdir(exist_ok=True)

    assert main(["build", "--into", str(into)]) == 1

    alias = "own" if where == "src/tmp" else "none"
    err = capsys.readouterr().err
    assert f"skill-graft: --into {into}: inside source '{alias}'" in err
    assert list(into.iterdir()) == []


def test_into_a_source_ignoring_case(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chisel_config(home)
    into = home / "SRC" / "tmp"  # the same folder as ~/src/tmp on macOS
    into.mkdir(parents=True)

    assert main(["build", "--into", str(into)]) == 1

    assert f"--into {into}: inside source 'own'" in capsys.readouterr().err


def test_into_the_cache_ignoring_case(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chisel_config(home)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    into = tmp_path / "CACHE" / "Skill-Graft" / "tmp"
    into.mkdir(parents=True)

    assert main(["build", "--into", str(into)]) == 1

    assert f"--into {into}: overlaps the cache" in capsys.readouterr().err


def test_into_untouched_when_the_config_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_config("entries = [\n")
    into = empty_folder(tmp_path)
    load = config.load

    def another_process_writes_first(scope: paths.Scope) -> config.Config:
        (into / "skill-graft.lock").write_text("theirs\n")
        return load(scope)

    monkeypatch.setattr(config, "load", another_process_writes_first)

    assert main(["build", "--into", str(into)]) == 1

    assert snapshot(into) == {"skill-graft.lock": b"theirs\n"}


def test_cleanup_keeps_the_real_error(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chisel_config(home)
    into = empty_folder(tmp_path)

    def fail(text: str, file: Path | None = None) -> None:
        assert file is not None
        file.mkdir()  # a lock the cleanup cannot unlink
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    assert main(["build", "--into", str(into)]) == 1

    assert "skill-graft: disk full" in capsys.readouterr().err


def test_into_names_no_resolve_hint(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "src" / "tdd", "then diagnosing-bugs\n")
    skill(home / "src" / "diagnosing-bugs")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)

    assert main(["build", "--into", str(into)]) == 0

    assert "prose suggestion" not in capsys.readouterr().err
    assert 'id = "own/diagnosing-bugs"' in (into / "skill-graft.lock").read_text()
