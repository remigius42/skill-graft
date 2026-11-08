import os
import shutil
import tempfile
from pathlib import Path

import pytest
from conftest import (
    FakeApm,
    Upstream,
    deadline,
    make_patch,
    resolve_and_deploy,
    skill,
    vendored,
    write_config,
)

from skill_graft.cli import main
from skill_graft.infra import paths
from skill_graft.infra.cache import Cache
from skill_graft.pipeline import compute, config, lock, vendor
from skill_graft.pipeline.hull import Hull


def skills_dir(home: Path) -> Path:
    return home / ".apm" / "skill-graft" / ".apm" / "skills"


def test_whole_folder_copied(home: Path) -> None:
    source = skill(home / "src" / "chisel")
    (source / "refs").mkdir()
    (source / "refs" / "notes.bin").write_bytes(b"notes\x00\xff")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    vendored = skills_dir(home) / "chisel"
    assert (vendored / "SKILL.md").read_text() == "# skill\n"
    assert (vendored / "refs" / "notes.bin").read_bytes() == b"notes\x00\xff"


def test_removed_entry(home: Path) -> None:
    skill(home / "src" / "chisel")
    skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    resolve_and_deploy(["deploy", "--no-apm-install"])
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["tdd"]


def test_referenced_skill_vendored(home: Path) -> None:
    skill(home / "src" / "tdd", "Run /grilling.\n")
    skill(home / "src" / "grilling")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["grilling", "tdd"]


def test_skill_no_longer_referenced_is_removed(home: Path) -> None:
    tdd = skill(home / "src" / "tdd", "Run /grilling.\n")
    skill(home / "src" / "grilling")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')
    resolve_and_deploy(["deploy", "--no-apm-install"])
    (tdd / "SKILL.md").write_text("Nothing.\n")

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["tdd"]


def test_warning_does_not_stop_deploy(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "src" / "tdd", "Run /foo.\n")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert "skill-graft: warning: `own/tdd` calls `/foo`" in capsys.readouterr().err


def test_symlink_in_a_referenced_skill(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "src" / "tdd", "Run /grilling.\n")
    grilling = skill(home / "src" / "grilling")
    (grilling / "out").symlink_to(home / "secret")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["deploy", "--no-apm-install"]) == 1

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


def test_failed_deploy_announces_no_suggestions(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable(skill(home / "src" / "tdd", "then diagnosing-bugs\n"), monkeypatch)
    skill(home / "src" / "diagnosing-bugs")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert main(["deploy", "--no-apm-install"]) == 1

    assert "prose suggestion(s)" not in capsys.readouterr().err


def test_copy_fails(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "chisel")
    broken = skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    resolve_and_deploy(["deploy", "--no-apm-install"])
    unreadable(broken, monkeypatch)
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 1

    err = capsys.readouterr().err
    assert "copying" in err and "secret" in err
    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["chisel"]
    assert not (skills_dir(home).parent / "skills.new").exists()


def test_crash_between_the_renames_keeps_the_previous_deploy(
    home: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "chisel")
    broken = skill(home / "src" / "tdd")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    resolve_and_deploy(["deploy", "--no-apm-install"])
    # A run killed after moving skills/ aside and before moving skills.new/ in.
    skills_dir(home).rename(skills_dir(home).with_name("skills.old"))
    skill(skills_dir(home).with_name("skills.new") / "half")
    unreadable(broken, monkeypatch)
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 1

    assert sorted(p.name for p in skills_dir(home).parent.iterdir()) == ["skills"]
    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["chisel"]


@pytest.mark.needs_permissions
def test_undeletable_stale_folder(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    deploy_one_skill(home)
    locked = skill(skills_dir(home).with_name("skills.new") / "half")
    locked.chmod(0o500)
    try:
        assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 1
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

    assert main(["deploy", "--no-apm-install"]) == 1

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

    assert main(["deploy", "--no-apm-install"]) == 1

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

    assert main(["deploy", "--no-apm-install"]) == 1

    assert "skill-graft update mp" in capsys.readouterr().err


def test_clash_ignores_case(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "TDD")
    write_config(
        'entries = ["mp/tdd", "own/TDD"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.own]\npath = "~/own"\n'
    )

    assert main(["deploy", "--no-apm-install"]) == 1

    err = capsys.readouterr().err
    assert "mp/tdd" in err and "own/TDD" in err
    assert "'TDD'" in err and "'tdd'" in err


def test_clash_across_sources(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill(home / "mp" / "tdd")
    skill(home / "own" / "tdd")
    skill(home / "own" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/own"\n')
    resolve_and_deploy(["deploy", "--no-apm-install"])
    write_config(
        'entries = ["mp/tdd", "own/tdd"]\n'
        '[sources.mp]\npath = "~/mp"\n[sources.own]\npath = "~/own"\n'
    )

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 1

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

    assert main(["deploy", "--no-apm-install"]) == 1

    assert f"chisel/{link}" in capsys.readouterr().err
    assert not skills_dir(home).parent.exists()


def test_symlink_in_git_metadata_is_ignored(home: Path) -> None:
    chisel = skill(home / "chisel")
    (chisel / ".git").mkdir()
    (chisel / ".git" / "hook").symlink_to(home)
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/chisel"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert sorted(p.name for p in (skills_dir(home) / "chisel").iterdir()) == [
        "SKILL.md"
    ]


def test_symlink_loop_is_an_error(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chisel = skill(home / "src" / "chisel")
    (chisel / "loop").symlink_to("loop")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert main(["deploy", "--no-apm-install"]) == 1

    assert "chisel/loop" in capsys.readouterr().err


def test_symlink_inside_the_skill_is_copied(home: Path) -> None:
    chisel = skill(home / "src" / "chisel")
    (chisel / "refs").mkdir()
    (chisel / "refs" / "notes.md").write_text("inside\n")
    (chisel / "notes.md").symlink_to("refs/notes.md")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    copied = skills_dir(home) / "chisel" / "notes.md"
    assert not copied.is_symlink() and copied.read_text() == "inside\n"


def test_skill_md_linked_to_a_device(home: Path) -> None:
    skill(home / "src" / "tdd")
    (home / "src" / "x").mkdir()
    (home / "src" / "x" / "SKILL.md").symlink_to("/dev/zero")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')

    with deadline():
        assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert sorted(p.name for p in skills_dir(home).iterdir()) == ["tdd"]


def test_entry_names_a_fifo(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (home / "src" / "x").mkdir(parents=True)
    os.mkfifo(home / "src" / "x" / "SKILL.md")
    write_config('entries = ["own/x"]\n[sources.own]\npath = "~/src"\n')

    with deadline():
        assert main(["deploy", "--no-apm-install"]) == 1

    assert "x/SKILL.md: not a regular file" in capsys.readouterr().err


def test_git_metadata_is_not_vendored(home: Path) -> None:
    source = skill(home / "chisel")
    (source / ".git").mkdir()
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/chisel"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert sorted(p.name for p in (skills_dir(home) / "chisel").iterdir()) == [
        "SKILL.md"
    ]


def test_no_apm_install_does_not_run_apm(home: Path, fake_apm: FakeApm) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    assert (skills_dir(home) / "chisel" / "SKILL.md").exists()
    assert fake_apm.calls == []


def deploy_one_skill(home: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')


def test_apm_succeeds(
    home: Path, fake_apm: FakeApm, capfd: pytest.CaptureFixture[str]
) -> None:
    deploy_one_skill(home)

    assert resolve_and_deploy(["deploy"]) == 0

    assert fake_apm.calls == [["install", "-g", str(home / ".apm" / "skill-graft")]]
    assert "fake apm: install -g" in capfd.readouterr().out


def test_apm_exits_non_zero(
    home: Path, fake_apm: FakeApm, capsys: pytest.CaptureFixture[str]
) -> None:
    deploy_one_skill(home)
    fake_apm.exit_code = 7

    assert resolve_and_deploy(["deploy"]) == 1

    assert "exit code 7" in capsys.readouterr().err


def test_apm_missing(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    deploy_one_skill(home)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    assert resolve_and_deploy(["deploy"]) == 1

    assert "APM is not installed" in capsys.readouterr().err
    assert (skills_dir(home) / "chisel").exists()


def test_apm_not_executable(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    deploy_one_skill(home)
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "apm").write_text("#!/bin/sh\n")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    assert main(["deploy"]) == 1

    assert "skill-graft: " in capsys.readouterr().err


@pytest.mark.parametrize("manifest", [None, "dependencies:\n  apm:\n    - /other\n"])
def test_package_not_registered(
    home: Path,
    fake_apm: FakeApm,
    capsys: pytest.CaptureFixture[str],
    manifest: str | None,
) -> None:
    deploy_one_skill(home)
    fake_apm.register = False
    if manifest is not None:
        (home / ".apm" / "apm.yml").write_text(manifest)

    assert resolve_and_deploy(["deploy"]) == 1

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
    deploy_one_skill(home)
    fake_apm.register = False
    line = item.format(package=home / ".apm" / "skill-graft")
    (home / ".apm" / "apm.yml").write_text(f"dependencies:\n  apm:\n    {line}\n")

    assert resolve_and_deploy(["deploy"]) == 0


def test_symlinked_home(
    home: Path, tmp_path: Path, fake_apm: FakeApm, monkeypatch: pytest.MonkeyPatch
) -> None:
    link = tmp_path / "link-home"
    link.symlink_to(home)
    monkeypatch.setenv("HOME", str(link))
    deploy_one_skill(link)
    fake_apm.register = False
    (home / ".apm" / "apm.yml").write_text(
        f"dependencies:\n  apm:\n    - {home / '.apm' / 'skill-graft'}\n"
    )

    assert resolve_and_deploy(["deploy"]) == 0


def test_registration_removed_by_hand(home: Path, fake_apm: FakeApm) -> None:
    deploy_one_skill(home)
    manifest = home / ".apm" / "apm.yml"
    manifest.write_text("dependencies:\n  apm:\n    - /other\n")

    assert resolve_and_deploy(["deploy"]) == 0

    assert f"- {home / '.apm' / 'skill-graft'}" in manifest.read_text()


def test_vendor_and_lock_into_a_given_folder(
    scope: paths.Scope, home: Path, tmp_path: Path
) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = tmp_path / "into"

    with compute.compute_hull(scope, config.load(scope), Cache.default()) as hull:
        vendor.stage(hull, into / ".apm" / "skills")
        vendor.swap(into / ".apm" / "skills")
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


def test_throwaway_deploy(
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

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 0

    vendored = sorted(p.name for p in (into / ".apm" / "skills").iterdir())
    assert vendored == ["grill", "tdd"]
    assert 'id = "own/grilling"' in (into / "skill-graft.lock").read_text()


def test_package_untouched(home: Path, tmp_path: Path) -> None:
    chisel = skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0
    package = home / ".apm" / "skill-graft"
    before = snapshot(package)
    (chisel / "SKILL.md").write_text("# changed\n")
    into = empty_folder(tmp_path)

    assert main(["deploy", "--into", str(into)]) == 0

    assert snapshot(package) == before
    vendored = into / ".apm" / "skills" / "chisel" / "SKILL.md"
    assert vendored.read_text() == "# changed\n"


def test_package_never_resolved(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)

    assert main(["deploy", "--into", str(into)]) == 1

    assert "skill-graft resolve" in capsys.readouterr().err
    package = home / ".apm" / "skill-graft"
    assert sorted(p.name for p in package.iterdir()) == ["skill-graft.toml"]
    assert list(into.iterdir()) == []


def test_same_lock(home: Path, tmp_path: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 0
    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

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

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 1

    assert "secret" in capsys.readouterr().err
    assert list(into.iterdir()) == []


def test_lock_write_fails(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)

    def fail(text: str, file: Path) -> None:
        file.write_text(text[:10])
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    assert main(["deploy", "--into", str(into)]) == 1

    assert list(into.iterdir()) == []


def test_foreign_file_kept(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable_entry(home, monkeypatch)
    into = empty_folder(tmp_path)
    copy = vendor.stage

    def another_process_writes_first(hull: Hull, skills: Path) -> None:
        (into / ".apm").mkdir()
        (into / ".apm" / "x").write_text("theirs\n")
        copy(hull, skills)

    monkeypatch.setattr(vendor, "stage", another_process_writes_first)

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 1

    assert snapshot(into) == {".apm/x": b"theirs\n"}
    assert sorted(p.name for p in (into / ".apm").iterdir()) == ["x"]


def test_temporary_folder_inside_it(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable_entry(home, monkeypatch)
    into = empty_folder(tmp_path)
    monkeypatch.setattr(tempfile, "tempdir", str(into))

    assert main(["deploy", "--into", str(into)]) == 1

    assert list(into.iterdir()) == []


def chisel_config(home: Path) -> None:
    skill(home / "src" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/src"\n')


def test_into_a_missing_folder(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chisel_config(home)
    into = tmp_path / "into"

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

    lines = capsys.readouterr().err.splitlines()
    assert lines[0].startswith("skill-graft: package: ")
    assert lines[1] == f"skill-graft: into: {into}"
    assert lines[2].startswith(f"skill-graft: --into {into}: ")


def test_into_a_symlink_to_an_empty_folder(home: Path, tmp_path: Path) -> None:
    chisel_config(home)
    target = empty_folder(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(target)

    assert resolve_and_deploy(["deploy", "--into", str(link)]) == 0

    assert (target / ".apm" / "skills" / "chisel" / "SKILL.md").is_file()


def test_into_a_path_only_passing_through_a_package(home: Path, tmp_path: Path) -> None:
    chisel_config(home)
    (tmp_path / "other" / ".apm" / "skill-graft").mkdir(parents=True)
    out = empty_folder(tmp_path)
    into = tmp_path / "other" / ".apm" / "skill-graft" / ".." / ".." / ".." / "into"

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 0

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

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

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

    assert main(["deploy", "--into", str(into)]) == 1

    assert snapshot(into) == {"skill-graft.lock": b"theirs\n"}


def test_cleanup_keeps_the_real_error(
    home: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chisel_config(home)
    into = empty_folder(tmp_path)

    def fail(text: str, file: Path) -> None:
        file.mkdir()  # a lock the cleanup cannot unlink
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 1

    assert "skill-graft: disk full" in capsys.readouterr().err


def test_into_names_no_resolve_hint(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill(home / "src" / "tdd", "then diagnosing-bugs\n")
    skill(home / "src" / "diagnosing-bugs")
    write_config('entries = ["own/tdd"]\n[sources.own]\npath = "~/src"\n')
    into = empty_folder(tmp_path)

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 0

    assert "prose suggestion" not in capsys.readouterr().err
    assert 'id = "own/diagnosing-bugs"' in (into / "skill-graft.lock").read_text()


Capsys = pytest.CaptureFixture[str]


def package() -> Path:
    return Path.home() / ".apm" / "skill-graft"


def git_and_own(home: Path, tmp_path: Path, extra: str = "") -> Upstream:
    """Entries `mp/tdd`, in a git source, and `own/chisel`, in a path source;
    resolved."""
    upstream = Upstream(tmp_path / "up")
    sha = upstream.commit({"tdd/SKILL.md": "# tdd\n", "notes/SKILL.md": "# notes\n"})
    skill(home / "own" / "chisel")
    write_config(
        'entries = ["mp/tdd", "own/chisel"]\n'
        f'[sources.mp]\ngit = "{upstream.url}"\nref = "{sha}"\n'
        '[sources.own]\npath = "~/own"\n' + extra
    )
    assert main(["resolve"]) == 0
    return upstream


def refused(capsys: Capsys, *args: str) -> str:
    """Runs a refused `deploy --no-apm-install`, or the command `args`; its stderr."""
    capsys.readouterr()
    assert main(list(args) or ["deploy", "--no-apm-install"]) == 1
    return capsys.readouterr().err


def test_nothing_changed(home: Path, tmp_path: Path) -> None:
    git_and_own(home, tmp_path)
    before = (package() / "skill-graft.lock").read_bytes()

    assert main(["deploy", "--no-apm-install"]) == 0

    assert (package() / "skill-graft.lock").read_bytes() == before


def test_lock_reformatted_by_an_editor(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    git_and_own(home, tmp_path)
    lock_file = package() / "skill-graft.lock"
    written = lock_file.read_bytes()
    text = "# reviewed\n" + written.decode()
    lock_file.write_bytes(text.replace("\n", "\r\n").encode())
    capsys.readouterr()

    assert main(["deploy", "--no-apm-install"]) == 0

    err = capsys.readouterr().err
    assert "skill-graft.lock" not in err and "warning" not in err
    assert lock_file.read_bytes() == written  # rewritten as skill-graft writes it


def test_config_edited_by_hand(
    home: Path, tmp_path: Path, fake_apm: FakeApm, capsys: Capsys
) -> None:
    git_and_own(home, tmp_path)
    config_file = package() / "skill-graft.toml"
    config_file.write_text(
        config_file.read_text().replace('"own/chisel"', '"own/chisel", "mp/notes"')
    )
    before = snapshot(package())

    err = refused(capsys, "deploy")

    assert "differs from skill-graft.lock" in err and "mp/notes added" in err
    assert "skill-graft resolve" in err
    assert snapshot(package()) == before and fake_apm.calls == []
    assert not (package() / ".apm" / "skills.new").exists()


def test_patch_edited_by_hand(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    patches = package() / "patches"
    patches.mkdir(parents=True)
    patch = patches / "tdd.patch"
    patch.write_bytes(
        make_patch(tmp_path, {"SKILL.md": "# tdd\n"}, {"SKILL.md": "a\n"})
    )
    git_and_own(home, tmp_path, '[patches]\n"mp/tdd" = ["patches/tdd.patch"]\n')
    patch.write_bytes(
        make_patch(tmp_path, {"SKILL.md": "# tdd\n"}, {"SKILL.md": "b\n"})
    )

    err = refused(capsys)

    assert "mp/tdd changed" in err and "skill-graft resolve" in err


def test_cache_export_edited(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    upstream = git_and_own(home, tmp_path)
    sha = upstream.git("rev-parse", "HEAD")
    tree = Cache.default().checkout("mp", upstream.url, sha)
    file = tree / "tdd" / "SKILL.md"
    file.chmod(0o644)
    file.write_text("edited in the cache\n")

    assert "mp/tdd changed" in refused(capsys)


def test_accepted_with_resolve(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    config_file = package() / "skill-graft.toml"
    config_file.write_text(
        config_file.read_text().replace('"own/chisel"', '"own/chisel", "mp/notes"')
    )
    refused(capsys)

    assert main(["resolve"]) == 0
    assert main(["deploy", "--no-apm-install"]) == 0

    assert vendored() == {"tdd", "chisel", "notes"}


def test_no_lock(home: Path, capsys: Capsys) -> None:
    skill(home / "own" / "chisel")
    write_config('entries = ["own/chisel"]\n[sources.own]\npath = "~/own"\n')

    err = refused(capsys)

    assert "skill-graft resolve" in err
    assert sorted(p.name for p in package().iterdir()) == ["skill-graft.toml"]


def test_lock_of_another_version(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    shutil.rmtree(skills_dir(home))  # else the copies cannot be checked
    lock_file = package() / "skill-graft.lock"
    lock_file.write_text(lock_file.read_text().replace("version = 1", "version = 2"))
    before = snapshot(package())

    assert "skill-graft resolve" in refused(capsys)

    assert snapshot(package()) == before


def test_vendoring_fails_keeps_lock_and_copies(home: Path, tmp_path: Path) -> None:
    git_and_own(home, tmp_path)
    before = snapshot(package())
    (home / "own" / "chisel" / "SKILL.md").write_text("changed\n")
    (home / "own" / "chisel" / "dangling").symlink_to("missing")

    assert main(["deploy", "--no-apm-install"]) == 1

    assert snapshot(package()) == before


NOTICE = "own/chisel changed in its path source since skill-graft.lock: deployed as is"


def test_own_skill_edited(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    (home / "own" / "chisel" / "SKILL.md").write_text("changed\n")
    capsys.readouterr()

    assert main(["deploy", "--no-apm-install"]) == 0

    assert NOTICE in capsys.readouterr().err
    assert (skills_dir(home) / "chisel" / "SKILL.md").read_text() == "changed\n"
    locked = lock.load(package() / "skill-graft.lock") or {}
    assert lock.copy_problems(skills_dir(home), locked) == []


def test_no_notice_into_a_folder(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    (home / "own" / "chisel" / "SKILL.md").write_text("changed\n")
    into = empty_folder(tmp_path)
    capsys.readouterr()

    assert main(["deploy", "--into", str(into)]) == 0

    assert "deployed as is" not in capsys.readouterr().err
    vendored = into / ".apm" / "skills" / "chisel" / "SKILL.md"
    assert vendored.read_text() == "changed\n"


def test_no_notice_when_the_lock_write_fails(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    git_and_own(home, tmp_path)
    before = snapshot(package())
    (home / "own" / "chisel" / "SKILL.md").write_text("changed\n")

    def fail(text: str, file: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)

    err = refused(capsys)

    assert "disk full" in err and "own/chisel" not in err
    assert snapshot(package()) == before


def test_path_source_elsewhere_on_another_machine(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills = tmp_path / "opt" / "skills"  # outside both the project and home
    skill(skills / "chisel")
    project = tmp_path / "repo"
    config_file = project / ".apm" / "skill-graft" / "skill-graft.toml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        f'entries = ["own/chisel"]\n[sources.own]\npath = "{skills}"\n'
    )
    monkeypatch.chdir(project)
    assert main(["resolve"]) == 0
    lock_file = config_file.with_name("skill-graft.lock")
    lock_file.write_text(lock_file.read_text().replace(str(skills), "/other/skills"))

    assert main(["deploy", "--no-apm-install"]) == 0

    locked = lock.load(lock_file) or {}
    assert locked["sources"] == {"own": {"path": str(skills)}}


def home_project(home: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project at `~/repo` whose path source `own` is `~/skills`, holding
    `chisel`; its lock file, once `resolve` wrote it."""
    skill(home / "skills" / "chisel")
    config_file = home / "repo" / ".apm" / "skill-graft" / "skill-graft.toml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        'entries = ["own/chisel"]\n[sources.own]\npath = "~/skills"\n'
    )
    monkeypatch.chdir(home / "repo")
    assert main(["resolve"]) == 0
    return config_file.with_name("skill-graft.lock")


def test_home_path_source_on_another_machine(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    committed = home_project(home, monkeypatch).read_bytes()
    other = tmp_path / "other-home"
    shutil.copytree(home, other)
    monkeypatch.setenv("HOME", str(other))
    monkeypatch.chdir(other / "repo")

    assert main(["deploy", "--no-apm-install"]) == 0

    lock_file = other / "repo" / ".apm" / "skill-graft" / "skill-graft.lock"
    assert lock_file.read_bytes() == committed


def test_lock_from_before_home_paths(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_file = home_project(home, monkeypatch)
    lock_file.write_text(
        lock_file.read_text().replace('"~/skills"', f'"{home / "skills"}"')
    )

    assert main(["deploy", "--no-apm-install"]) == 0

    locked = lock.load(lock_file) or {}
    assert locked["sources"] == {"own": {"path": "~/skills"}}


def test_patched_own_skill(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    patches = package() / "patches"
    patches.mkdir(parents=True)
    patch = patches / "chisel.patch"
    text = "# skill\n"
    patch.write_bytes(make_patch(tmp_path, {"SKILL.md": text}, {"SKILL.md": "a\n"}))
    git_and_own(home, tmp_path, '[patches]\n"own/chisel" = ["patches/chisel.patch"]\n')
    before = snapshot(package())
    patch.write_bytes(make_patch(tmp_path, {"SKILL.md": text}, {"SKILL.md": "b\n"}))

    err = refused(capsys)

    assert "own/chisel changed" in err and "skill-graft resolve" in err
    assert snapshot(package()) == {**before, "patches/chisel.patch": patch.read_bytes()}


def test_own_skill_reaches_a_new_skill(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    git_and_own(home, tmp_path)
    skill(home / "own" / "grilling")
    before = snapshot(package())
    (home / "own" / "chisel" / "SKILL.md").write_text("/grilling\n")

    err = refused(capsys)

    assert "own/grilling added" in err and "skill-graft resolve" in err
    assert snapshot(package()) == before


def test_copy_edited(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    copy = skills_dir(home) / "tdd" / "SKILL.md"
    copy.write_text("edited\n")

    err = refused(capsys)

    assert str(skills_dir(home) / "tdd") in err
    assert "patch" in err and "delete the folder" in err
    assert copy.read_text() == "edited\n"


def test_edited_copy_before_an_edit_command(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    git_and_own(home, tmp_path)
    (skills_dir(home) / "tdd" / "SKILL.md").write_text("edited\n")
    before = snapshot(package())

    err = refused(capsys, "add", "mp/notes")

    assert str(skills_dir(home) / "tdd") in err
    assert snapshot(package()) == before


def test_folder_added_by_hand(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    skill(skills_dir(home) / "mine")

    assert str(skills_dir(home) / "mine") in refused(capsys)

    assert (skills_dir(home) / "mine" / "SKILL.md").exists()


def test_copy_deleted(home: Path, tmp_path: Path) -> None:
    git_and_own(home, tmp_path)
    shutil.rmtree(skills_dir(home) / "tdd")

    assert main(["deploy", "--no-apm-install"]) == 0

    assert (skills_dir(home) / "tdd" / "SKILL.md").read_text() == "# tdd\n"


def test_copies_without_a_lock(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    (package() / "skill-graft.lock").unlink()
    before = snapshot(package())

    err = refused(capsys, "resolve")

    assert "cannot be checked" in err and f"delete {skills_dir(home)}" in err
    assert "skill-graft resolve" in err
    assert snapshot(package()) == before


@pytest.mark.parametrize("text", ["not [toml\n", "version = 2\n"])
def test_lock_unreadable(home: Path, tmp_path: Path, capsys: Capsys, text: str) -> None:
    git_and_own(home, tmp_path)
    (package() / "skill-graft.lock").write_text(text)

    err = refused(capsys, "resolve")

    assert "cannot be checked" in err and "differs" not in err


def test_file_at_the_top(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    (skills_dir(home) / "README.md").write_text("mine\n")

    assert str(skills_dir(home) / "README.md") in refused(capsys, "resolve")

    assert (skills_dir(home) / "README.md").read_text() == "mine\n"


def test_killed_before_the_lock_was_written(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    git_and_own(home, tmp_path)
    # Swapped in, then killed: the previous copies in skills.old match the lock.
    shutil.copytree(skills_dir(home), skills_dir(home).with_name("skills.old"))
    (skills_dir(home) / "tdd" / "SKILL.md").write_text("from the killed run\n")

    assert main(["deploy", "--no-apm-install"]) == 0

    assert (skills_dir(home) / "tdd" / "SKILL.md").read_text() == "# tdd\n"


def test_killed_after_the_lock_was_written(home: Path, tmp_path: Path) -> None:
    upstream = git_and_own(home, tmp_path)
    previous = shutil.copytree(skills_dir(home), tmp_path / "previous")
    upstream.commit({"tdd/SKILL.md": "# tdd 2\n"})
    assert main(["update"]) == 0
    previous.rename(skills_dir(home).with_name("skills.old"))

    assert main(["deploy", "--no-apm-install"]) == 0

    assert (skills_dir(home) / "tdd" / "SKILL.md").read_text() == "# tdd 2\n"
    assert not skills_dir(home).with_name("skills.old").exists()


def test_killed_after_the_lock_was_written_skills_only_added(
    home: Path, tmp_path: Path
) -> None:
    git_and_own(home, tmp_path)
    previous = shutil.copytree(skills_dir(home), tmp_path / "previous")
    assert main(["add", "mp/notes"]) == 0
    previous.rename(skills_dir(home).with_name("skills.old"))

    assert main(["deploy", "--no-apm-install"]) == 0

    assert (skills_dir(home) / "notes" / "SKILL.md").read_text() == "# notes\n"
    assert not skills_dir(home).with_name("skills.old").exists()


def test_refused_deploy_leaves_a_killed_run_as_it_is(
    home: Path, tmp_path: Path, capsys: Capsys
) -> None:
    git_and_own(home, tmp_path)
    shutil.copytree(skills_dir(home), skills_dir(home).with_name("skills.old"))
    config_file = package() / "skill-graft.toml"
    config_file.write_text(
        config_file.read_text().replace('"own/chisel"', '"own/chisel", "mp/notes"')
    )
    before = snapshot(skills_dir(home).parent)

    assert "skill-graft resolve" in refused(capsys)

    assert snapshot(skills_dir(home).parent) == before


def test_stray_file_in_a_copy(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    (skills_dir(home) / "tdd" / ".DS_Store").write_bytes(b"\0")

    err = refused(capsys)

    assert f"{skills_dir(home) / 'tdd'}: differs from skill-graft.lock" in err


ATTRIBUTES = "/.apm/skills/** -text\n/patches/** -text\n"


def test_attributes_written(home: Path, tmp_path: Path) -> None:
    git_and_own(home, tmp_path)

    assert (package() / ".gitattributes").read_text() == ATTRIBUTES


def test_own_attributes_kept(home: Path, tmp_path: Path) -> None:
    (package()).mkdir(parents=True)
    (package() / ".gitattributes").write_bytes(b"* -text\n")

    git_and_own(home, tmp_path)

    assert (package() / ".gitattributes").read_bytes() == b"* -text\n"


def test_none_into_a_folder(home: Path, tmp_path: Path) -> None:
    git_and_own(home, tmp_path)
    (package() / ".gitattributes").unlink()
    into = empty_folder(tmp_path)

    assert main(["deploy", "--into", str(into)]) == 0

    assert not (package() / ".gitattributes").exists()
    assert not (into / ".gitattributes").exists()


def test_checkout_converting_line_endings(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    skill(home / "skills" / "chisel", "# chisel\nline two\n")
    project = Upstream(tmp_path / "repo")
    config_file = project.path / ".apm" / "skill-graft" / "skill-graft.toml"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        'entries = ["own/chisel"]\n[sources.own]\npath = "~/skills"\n'
    )
    monkeypatch.chdir(project.path)
    assert main(["resolve"]) == 0
    project.commit({})
    clone = tmp_path / "clone"
    project.git("clone", "-q", "-c", "core.autocrlf=true", project.url, str(clone))
    copy = clone / ".apm" / "skill-graft" / ".apm" / "skills" / "chisel" / "SKILL.md"
    assert copy.read_bytes() == b"# chisel\nline two\n"
    monkeypatch.chdir(clone)
    capsys.readouterr()

    assert main(["deploy", "--no-apm-install"]) == 0

    assert "differs" not in capsys.readouterr().err


def test_into_config_edited_by_hand(home: Path, tmp_path: Path, capsys: Capsys) -> None:
    git_and_own(home, tmp_path)
    config_file = package() / "skill-graft.toml"
    config_file.write_text(
        config_file.read_text().replace('"own/chisel"', '"own/chisel", "mp/notes"')
    )
    into = empty_folder(tmp_path)

    assert "skill-graft resolve" in refused(capsys, "deploy", "--into", str(into))

    assert list(into.iterdir()) == []


def test_into_emptied_after_an_interrupt_mid_stage(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chisel_config(home)
    assert main(["resolve"]) == 0
    into = empty_folder(tmp_path)

    def interrupted(hull: Hull, skills: Path) -> None:
        (skills.with_name("skills.new") / "chisel").mkdir(parents=True)
        raise KeyboardInterrupt

    monkeypatch.setattr(vendor, "stage", interrupted)

    with pytest.raises(KeyboardInterrupt):
        main(["deploy", "--into", str(into)])

    assert list(into.iterdir()) == []


def test_into_emptied_when_the_swap_cannot_be_undone(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chisel_config(home)
    assert main(["resolve"]) == 0
    into = empty_folder(tmp_path)

    def fail(text: str, file: Path) -> None:
        file.write_text(text)
        for name in ["skills.old", "skills.trash"]:
            (into / ".apm" / name / "chisel").mkdir(parents=True)
        raise OSError("disk full")

    monkeypatch.setattr(lock, "write", fail)
    monkeypatch.setattr(vendor, "swap_back", failing_rename)

    assert main(["deploy", "--into", str(into)]) == 1

    assert list(into.iterdir()) == []


def failing_rename(skills: Path) -> None:
    raise OSError("rename failed")


PREFIXED = 'reference-prefix = "foo:"\n'
NO_APM = (
    'reference-prefix "foo:" makes skills that work only inside a plugin; run'
    " skill-graft deploy --no-apm-install\n"
)


def prefixed_skills(home: Path, source: str = '[sources.mp]\npath = "~/mp"\n') -> str:
    """`mp/tdd` calling `/grilling` at `~/mp`, `own/y` at `~/own`; the config text
    without a reference prefix."""
    skill(home / "mp" / "tdd", "Run /grilling.\n")
    skill(home / "mp" / "grilling")
    skill(home / "own" / "y")
    return f'entries = ["mp/tdd"]\n{source}[sources.own]\npath = "~/own"\n'


def plugin_package(
    home: Path, monkeypatch: pytest.MonkeyPatch, text: str, manifest: str = ""
) -> Path:
    """`~/plugin` holding a package made by hand with `text` as its config, and
    `manifest` as its `apm.yml` if given; its package."""
    package = home / "plugin" / ".apm" / "skill-graft"
    package.mkdir(parents=True)
    (package / "skill-graft.toml").write_text(text)
    if manifest:
        (home / "plugin" / "apm.yml").write_text(manifest)
    monkeypatch.chdir(home / "plugin")
    return package


def uncached_git(home: Path) -> str:
    """A git source `mp` whose ref is not cached, and whose URL fetches nothing."""
    return f'[sources.mp]\ngit = "{home / "nowhere"}"\nref = "{"a" * 40}"\n'


WRITERS = [["resolve"], ["deploy"], ["deploy", "--no-apm-install"]]


@pytest.mark.parametrize("args", WRITERS, ids=" ".join)
def test_user_scope_refuses_a_reference_prefix(
    home: Path, capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    write_config(PREFIXED + prefixed_skills(home, uncached_git(home)))

    assert main(args) == 1

    assert (
        'reference-prefix "foo:" makes skills that work only inside a plugin, and APM'
        f" deploys {package()}: remove it, or curate the plugin's skills in a"
        " package inside the plugin\n"
    ) in capsys.readouterr().err
    assert sorted(p.name for p in package().iterdir()) == ["skill-graft.toml"]


@pytest.mark.parametrize("args", [*WRITERS, ["bind", "mp/x", "own/y"]], ids=" ".join)
def test_registered_project_package_refuses_a_reference_prefix(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
) -> None:
    text = PREFIXED + prefixed_skills(home, uncached_git(home))
    manifest = "dependencies:\n  apm:\n    - ./.apm/skill-graft\n"
    package = plugin_package(home, monkeypatch, text, manifest)

    assert main(args) == 1

    assert (
        'reference-prefix "foo:" makes skills that work only inside a plugin, and'
        f" {home / 'plugin' / 'apm.yml'} lists {package} for APM to deploy: remove"
        " one of them\n"
    ) in capsys.readouterr().err
    assert snapshot(package) == {"skill-graft.toml": text.encode()}


def test_unregistered_project_package_takes_a_reference_prefix(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = plugin_package(home, monkeypatch, PREFIXED + prefixed_skills(home))

    assert main(["resolve"]) == 0

    vendored = package / ".apm" / "skills"
    assert (vendored / "tdd" / "SKILL.md").read_text() == "Run /foo:grilling.\n"
    assert (vendored / "grilling" / "SKILL.md").read_text() == "# skill\n"


@pytest.mark.parametrize(
    "args", [["tree"], ["why", "mp/tdd"], ["vet"], ["resolve", "--dry-run"]]
)
def test_inspecting_stays_possible_with_a_reference_prefix(
    home: Path, args: list[str]
) -> None:
    write_config(PREFIXED + prefixed_skills(home))

    assert main(args) == 0

    assert sorted(p.name for p in package().iterdir()) == ["skill-graft.toml"]


def test_plain_deploy_refused_with_a_reference_prefix(
    home: Path,
    monkeypatch: pytest.MonkeyPatch,
    fake_apm: FakeApm,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = plugin_package(home, monkeypatch, PREFIXED + prefixed_skills(home))
    assert main(["resolve"]) == 0
    before = snapshot(package)
    capsys.readouterr()

    assert main(["deploy"]) == 1

    err = capsys.readouterr().err
    assert NO_APM in err
    assert fake_apm.calls == []
    assert snapshot(package) == before


def test_deploy_refused_before_any_fetch(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = PREFIXED + prefixed_skills(home, uncached_git(home))
    plugin_package(home, monkeypatch, text)

    assert main(["deploy"]) == 1

    err = capsys.readouterr().err
    assert NO_APM in err
    assert not Cache.default().repository(str(home / "nowhere")).exists()


def test_deploy_without_apm_takes_a_reference_prefix(
    home: Path, monkeypatch: pytest.MonkeyPatch, fake_apm: FakeApm
) -> None:
    package = plugin_package(home, monkeypatch, PREFIXED + prefixed_skills(home))

    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0

    tdd = package / ".apm" / "skills" / "tdd" / "SKILL.md"
    assert tdd.read_text() == "Run /foo:grilling.\n"
    assert fake_apm.calls == []


def test_deploy_into_a_folder_takes_a_reference_prefix(
    home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_package(home, monkeypatch, PREFIXED + prefixed_skills(home))
    into = empty_folder(tmp_path)

    assert resolve_and_deploy(["deploy", "--into", str(into)]) == 0

    tdd = into / ".apm" / "skills" / "tdd" / "SKILL.md"
    assert tdd.read_text() == "Run /foo:grilling.\n"


def test_reference_prefix_removed(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = prefixed_skills(home)
    package = plugin_package(home, monkeypatch, PREFIXED + text)
    tdd = package / ".apm" / "skills" / "tdd" / "SKILL.md"
    assert main(["resolve"]) == 0
    (package / "skill-graft.toml").write_text(text)
    capsys.readouterr()

    assert main(["deploy", "--no-apm-install"]) == 1

    err = capsys.readouterr().err
    assert "reference-prefix changed" in err and "skill-graft resolve" in err
    assert tdd.read_text() == "Run /foo:grilling.\n"
    assert resolve_and_deploy(["deploy", "--no-apm-install"]) == 0
    assert tdd.read_text() == "Run /grilling.\n"


def test_reference_prefix_set(
    home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = prefixed_skills(home)
    package = plugin_package(home, monkeypatch, text)
    assert main(["resolve"]) == 0
    (package / "skill-graft.toml").write_text(PREFIXED + text)
    capsys.readouterr()

    assert main(["deploy", "--no-apm-install"]) == 1

    err = capsys.readouterr().err
    assert "reference-prefix changed" in err and "skill-graft resolve" in err
