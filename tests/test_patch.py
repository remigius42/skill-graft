"""`patch.apply`: a skill's patches applied, in order, to a copy of its folder."""

import os
import subprocess
from pathlib import Path

import pytest
from conftest import make_patch, skill

from skill_graft import patch
from skill_graft.config import PatchFile, SkillId

TDD = SkillId("mp", "tdd")
LINES = "".join(f"line {i}\n" for i in range(1, 11))


def upstream_with(tmp_path: Path, files: dict[str, str]) -> Path:
    folder = skill(tmp_path / "src" / "tdd", files.pop("SKILL.md", LINES))
    for path, text in files.items():
        (folder / path).parent.mkdir(parents=True, exist_ok=True)
        (folder / path).write_text(text)
    return folder


def work_in(tmp_path: Path) -> Path:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return work


def test_patch_changes_the_text(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {})
    data = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 5\n", "line five\n")},
    )

    copy = patch.apply(
        TDD, upstream, [PatchFile("patches/tdd.patch", data)], work_in(tmp_path)
    )

    assert (copy / "SKILL.md").read_text() == LINES.replace("line 5\n", "line five\n")
    assert (upstream / "SKILL.md").read_text() == LINES
    assert copy.name == "tdd"


def test_patches_in_order(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {})
    added = LINES.replace("line 5\n", "line five\n")
    a = make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": added})
    b = make_patch(
        tmp_path, {"SKILL.md": added}, {"SKILL.md": added.replace("five", "FIVE")}
    )
    patches = [PatchFile("a.patch", a), PatchFile("b.patch", b)]

    copy = patch.apply(TDD, upstream, patches, work_in(tmp_path))

    assert "line FIVE\n" in (copy / "SKILL.md").read_text()


def test_patch_to_a_sibling_file(tmp_path: Path) -> None:
    files = {"refs/loop.md": "loop\n", "refs/old.md": "old\n"}
    upstream = upstream_with(tmp_path, dict(files))
    data = make_patch(
        tmp_path,
        files,
        {"refs/loop.md": "loop, changed\n", "refs/new.md": "new\n"},
    )

    copy = patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    assert (copy / "refs" / "loop.md").read_text() == "loop, changed\n"
    assert (copy / "refs" / "new.md").read_text() == "new\n"
    assert not (copy / "refs" / "old.md").exists()


def test_every_failing_hunk_named(tmp_path: Path) -> None:
    long = "".join(f"line {i}\n" for i in range(1, 41))
    edited = long
    for n in (5, 20, 35):
        edited = edited.replace(f"line {n}\n", f"line {n} edited\n")
    data = make_patch(tmp_path, {"SKILL.md": long}, {"SKILL.md": edited})
    moved = long.replace("line 4\n", "line 4 upstream\n").replace(
        "line 34\n", "line 34 upstream\n"
    )
    upstream = upstream_with(tmp_path, {"SKILL.md": moved})

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    assert failed.value.lines == [
        "p.patch: SKILL.md: hunk @@ -2,7 +2,7 @@ does not apply",
        "p.patch: SKILL.md: hunk @@ -32,7 +32,7 @@ does not apply",
    ]


def test_patch_refused_whole(tmp_path: Path) -> None:
    data = make_patch(tmp_path, {"refs/old.md": "old\n"}, {"refs/old.md": "new\n"})
    upstream = upstream_with(tmp_path, {})

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    [line] = failed.value.lines
    assert line.startswith("p.patch: git apply refused it: ")
    assert "refs/old.md" in line


def test_later_patch_not_tried(tmp_path: Path) -> None:
    bad = make_patch(tmp_path, {"refs/old.md": "old\n"}, {"refs/old.md": "new\n"})
    good = make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": LINES + "more\n"})
    upstream = upstream_with(tmp_path, {})
    patches = [PatchFile("a.patch", bad), PatchFile("b.patch", good)]

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, patches, work_in(tmp_path))

    assert failed.value.lines[-1] == "b.patch: not tried"


def test_upstream_ships_a_reject_file(tmp_path: Path) -> None:
    shipped = "--- notes.md\n+++ notes.md\n@@ -1 +1 @@\n-a\n+b\n"
    upstream = upstream_with(
        tmp_path, {"notes.md.rej": shipped, "SKILL.md.rej": shipped}
    )
    gone = make_patch(tmp_path, {"refs/old.md": "old\n"}, {"refs/old.md": "new\n"})
    moved = make_patch(
        tmp_path,
        {"SKILL.md": LINES},
        {"SKILL.md": LINES.replace("line 2\n", "line two\n")},
    )
    (upstream / "SKILL.md").write_text("new\n" + LINES)

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", gone)], work_in(tmp_path))
    assert failed.value.lines[0].startswith("p.patch: git apply refused it: ")

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", moved)], tmp_path / "work2")
    assert failed.value.lines == [
        "p.patch: SKILL.md: hunk @@ -1,5 +1,5 @@ does not apply"
    ]


@pytest.mark.parametrize(
    "before, after",
    [
        ("---\nname: tdd\n---\n# tdd\n", "---\nname: tdd2\n---\n# tdd\n"),
        ("# tdd\n", "---\nname: other\n---\n# tdd\n"),
    ],
    ids=["name-changed", "name-added"],
)
def test_name_changed(tmp_path: Path, before: str, after: str) -> None:
    data = make_patch(tmp_path, {"SKILL.md": before}, {"SKILL.md": after})
    upstream = upstream_with(tmp_path, {"SKILL.md": before})

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    [line] = failed.value.lines
    assert line.startswith("p.patch: changes the skill's name to ")
    assert "[rename]" in line


def test_unsupported_name_form(tmp_path: Path) -> None:
    before = "---\nname: tdd\n---\n"
    after = "---\nname: >\n  tdd\n---\n"
    data = make_patch(tmp_path, {"SKILL.md": before}, {"SKILL.md": after})
    upstream = upstream_with(tmp_path, {"SKILL.md": before})

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    assert failed.value.lines == ["p.patch: SKILL.md: unsupported form of `name:`"]


def test_skill_md_deleted(tmp_path: Path) -> None:
    files = {"SKILL.md": LINES, "notes.md": "notes\n"}
    data = make_patch(tmp_path, files, {"notes.md": "notes\n"})
    upstream = upstream_with(tmp_path, dict(files))

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    [line] = failed.value.lines
    assert line.startswith("p.patch: SKILL.md: cannot be read")
    assert str(tmp_path / "work") not in line


def new_link(path: str, target: str) -> bytes:
    """A git patch creating `path` as a symlink to `target`."""
    return (
        f"diff --git a/{path} b/{path}\nnew file mode 120000\n--- /dev/null\n"
        f"+++ b/{path}\n@@ -0,0 +1 @@\n+{target}\n\\ No newline at end of file\n"
    ).encode()


def test_symlink_leaving_the_skill(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {})
    data = new_link("link.md", "/etc/hostname")

    with pytest.raises(patch.PatchFailed) as failed:
        patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    [line] = failed.value.lines
    assert line.startswith("p.patch: link.md points outside the skill")
    assert str(tmp_path / "work") not in line


def test_symlink_within_the_skill(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {})
    data = new_link("link.md", "SKILL.md")

    copy = patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    assert (copy / "link.md").read_text() == LINES


def test_path_outside_the_skill(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {})
    data = (
        b"diff --git a/../outside.md b/../outside.md\nnew file mode 100644\n"
        b"--- /dev/null\n+++ b/../outside.md\n@@ -0,0 +1 @@\n+out\n"
    )

    with pytest.raises(patch.PatchFailed):
        patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    assert not list(tmp_path.rglob("outside.md"))


def test_mode_change(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {"run.sh": "echo hi\n"})
    data = b"diff --git a/run.sh b/run.sh\nold mode 100644\nnew mode 100755\n"

    copy = patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    assert os.access(copy / "run.sh", os.X_OK)


def test_read_only_upstream(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {"refs/loop.md": "loop\n"})
    data = make_patch(
        tmp_path,
        {"SKILL.md": LINES, "refs/loop.md": "loop\n"},
        {"SKILL.md": LINES + "more\n", "refs/new.md": "new\n"},
    )
    for path in [upstream / "refs" / "loop.md", upstream / "SKILL.md"]:
        path.chmod(0o444)
    for folder in [upstream / "refs", upstream]:
        folder.chmod(0o555)
    try:
        copy = patch.apply(
            TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path)
        )
    finally:
        for folder in [upstream, upstream / "refs"]:
            folder.chmod(0o755)

    assert (copy / "SKILL.md").read_text() == LINES + "more\n"
    assert (copy / "refs" / "new.md").read_text() == "new\n"
    assert (upstream / "SKILL.md").read_text() == LINES
    assert (upstream / "SKILL.md").stat().st_mode & 0o777 == 0o444


def test_source_is_a_repository(tmp_path: Path) -> None:
    upstream = upstream_with(tmp_path, {})
    subprocess.run(["git", "init", "-q", str(upstream)], check=True)
    data = make_patch(tmp_path, {"SKILL.md": LINES}, {"SKILL.md": LINES + "more\n"})

    copy = patch.apply(TDD, upstream, [PatchFile("p.patch", data)], work_in(tmp_path))

    assert (copy / "SKILL.md").read_text() == LINES + "more\n"
    assert not (copy / ".git").exists()
