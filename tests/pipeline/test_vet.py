"""The `vet` spec's patterns: one skill's deployed files in, its flags out."""

import pytest

from skill_graft.pipeline import vet


def flags(text: str, name: str = "SKILL.md") -> set[tuple[str, int, str]]:
    """The flags of a skill holding `text` in file `name`."""
    return {
        (flag.file, flag.line, flag.pattern)
        for flag in vet.scan({name: (text.encode(), False)})
    }


def patterns(line: str, name: str = "notes.md") -> set[str]:
    """The patterns flagged on `line`, alone in file `name`."""
    return {pattern for _, _, pattern in flags(line + "\n", name)}


def test_categories_and_their_owasp_ids() -> None:
    assert vet.OWASP == {
        "read": ("LLM02",),
        "write": ("ASI02",),
        "send": ("LLM02", "ASI02"),
        "run": ("ASI05",),
        "privilege": ("ASI03",),
        "persistence": ("ASI06",),
        "permission": ("ASI02",),
        "unreviewable": ("LLM03",),
    }


def test_plain_prose_flags_nothing() -> None:
    assert flags("# tdd\n\nWrite the test first.\n") == set()


def test_binary_file() -> None:
    view = {"SKILL.md": (b"# x\n", False), "bin/tool": (b"\x7fELF\0\0\xff\xfe", False)}

    assert vet.scan(view) == [vet.Flag("bin/tool", 0, "unreviewable.binary")]


def test_utf16_file() -> None:
    view = {"notes.txt": ("plain\n".encode("utf-16"), False)}

    assert vet.scan(view) == [vet.Flag("notes.txt", 0, "unreviewable.encoding")]


def test_lenient_utf8_file() -> None:
    view = {"notes.txt": (b"caf\xe9\n", False)}

    assert vet.scan(view) == [vet.Flag("notes.txt", 0, "unreviewable.encoding")]


def test_utf16_file_still_scanned_by_line() -> None:
    view = {"notes.txt": ("plain\r\ncat /etc/passwd\r\n".encode("utf-16"), False)}

    assert vet.scan(view) == [
        vet.Flag("notes.txt", 0, "unreviewable.encoding"),
        vet.Flag("notes.txt", 2, "read.outside-path"),
    ]


@pytest.mark.parametrize(
    "line", ["cat references/guide.md", "cat ./a/../b.md", "Run /grilling first"]
)
def test_inside_the_project(line: str) -> None:
    assert patterns(line) == set()


@pytest.mark.parametrize(
    "line",
    [
        "cat ../../notes.md",
        "cat /etc/passwd",
        "ls ~",
        "cat ~/notes.md",
        "cat ~alice/notes.md",
        "cat $HOME/notes.md",
        "cat ${HOME}/notes.md",
        "cd ..",
        "cat /etc/passwd 2>/dev/null",
        "cat ~/notes.md >/dev/null 2>&1",
    ],
)
def test_climbing_out(line: str) -> None:
    assert patterns(line) == {"read.outside-path"}


@pytest.mark.parametrize(
    "line",
    [
        "Wait... then go on",
        "about ~5 minutes",
        "cat $HOMEDIR/notes.md",
        "// a comment",
        "x = a/b",
        "ls notes 2>/dev/null",
    ],
)
def test_no_path_outside(line: str) -> None:
    assert patterns(line) == set()


def test_url_path_is_no_path() -> None:
    assert "read.outside-path" not in patterns("see https://x.example/etc/passwd")


@pytest.mark.parametrize(
    "line",
    [
        "echo done >> ~/log.txt",
        "echo done > /tmp/log.txt",
        "tee ../../log.txt",
        "cp notes.md ~/notes.md",
        "sed -i s/a/b/ /etc/hosts",
        "Save the summary to ~/summary.md",
    ],
)
def test_writing_outside(line: str) -> None:
    assert patterns(line) == {"write.outside-path"}


@pytest.mark.parametrize(
    "line",
    [
        "cat .ssh/config",
        "cp .env.example .env",
        "read the AWS keys in .aws",
        "ls .gnupg",
        "cat .netrc .npmrc .pypirc",
        "show id_rsa",
        "keys in id_ed25519",
        "unlock the Keychain",
        "load the credentials",
    ],
)
def test_secret_store(line: str) -> None:
    assert patterns(line) == {"read.secret-store"}


@pytest.mark.parametrize(
    "line", ["set up the environment", "credential", "my.sshd", "keychains.md"]
)
def test_no_secret_store(line: str) -> None:
    assert patterns(line) == set()


def test_secret_store_outside() -> None:
    assert patterns("cat ~/.aws/credentials") == {
        "read.outside-path",
        "read.secret-store",
    }
