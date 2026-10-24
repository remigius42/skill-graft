"""Finds hidden characters, which a reader of the rendered text never sees, in a skill."""

import re
from pathlib import Path

from skill_graft.infra import files
from skill_graft.infra.errors import SkillGraftError

# The critical and warning sets of APM 0.33.0's install check
# (`apm_cli/security/content_scanner.py`), copied as `apm_cli` is no API. Lone
# surrogates are left out: strict decoding refuses them, lenient replaces them.
# Each critical class: its code points, first and last, and what it is called.
CRITICAL = [
    (0xE0001, 0xE007F, "tag character"),
    (0x202A, 0x202E, "bidi control"),  # embeddings, overrides and their pop
    (0x2066, 0x2069, "bidi control"),  # isolates
    (0xE0100, 0xE01EF, "variation selector"),  # supplementary
]

# Copy-paste debris, though it can hide text too: zero-width characters, the word
# joiner, the soft hyphen, BMP variation selectors but the emoji one, bidi marks,
# invisible operators, annotation markers and deprecated formatting characters.
WARNING = [
    (0x200B, 0x200D),
    (0x2060, 0x2064),
    (0x00AD, 0x00AD),
    (0xFE00, 0xFE0E),
    (0x200E, 0x200F),
    (0x061C, 0x061C),
    (0xFFF9, 0xFFFB),
    (0x206A, 0x206F),
]


def _ranges(ranges: list[tuple[int, int]]) -> re.Pattern[str]:
    return re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in ranges) + "]")


CRITICAL_CHARS = _ranges([(a, b) for a, b, _ in CRITICAL])
WARNING_CHARS = _ranges(WARNING)


def scan(folder: Path) -> tuple[list[str], list[str]]:
    """Where in `folder` a hidden character is, and Markdown that is not UTF-8;
    then a warning per file holding debris. Paths are relative to `folder`.

    Reads files, so the skill's symlinks must be checked first.
    """
    found, warnings = [], []
    for entry in files.skill_entries(folder):
        name = show(entry.relative_to(folder).as_posix())
        found += scan_names(folder, [entry])
        if entry.is_dir():
            continue
        markdown = entry.name.lower().endswith(".md")
        try:
            data = entry.read_bytes()
        except OSError as error:
            raise SkillGraftError(f"{entry} cannot be read: {error.strerror}") from None
        text = decode(data, markdown, "replace")
        if text is None:
            if markdown:
                found.append(f"{name}: not UTF-8, so its references cannot be read")
            continue
        found_here, warned = _report(name, text)
        found += found_here
        warnings += warned
    return found, warnings


def scan_names(folder: Path, entries: list[Path]) -> list[str]:
    """As `scan`, for the names alone of these entries of `folder`."""
    return [
        f"{show(entry.relative_to(folder).as_posix())}: its name holds {_describe(c)}"
        for entry in entries
        for c in CRITICAL_CHARS.findall(entry.name)
    ]


def not_utf8(folder: Path, entries: list[Path]) -> list[str]:
    """As `scan`, for these entries of `folder`: each Markdown file that is not UTF-8."""
    return [
        f"{show(entry.relative_to(folder).as_posix())}: not UTF-8, so its references "
        "cannot be read"
        for entry in entries
        if entry.name.lower().endswith(".md")
        and entry.is_file()
        and decode(entry.read_bytes(), True, "replace") is None
    ]


def scan_patch(name: str, data: bytes) -> tuple[list[str], list[str]]:
    """As `scan`, for the lines patch file `name` adds, by its own line numbers:
    the lines it keeps repeat the upstream ones, which `scan` reports. A patch is
    text whatever bytes it holds: each that is not UTF-8 counts as no character."""
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\n")
    added = "\n".join(line if line.startswith("+") else "" for line in lines)
    return _report(name, added)


def _report(name: str, text: str) -> tuple[list[str], list[str]]:
    """Each hidden character in `text`, of file `name`; a warning for its debris."""
    critical, debris = characters(text)
    found = [f"{name}:{number}: {_describe(char)}" for number, char in critical]
    if not debris:
        return found, []
    number, char = debris[0]
    count = f"{len(debris)} invisible character{'s' * (len(debris) > 1)}"
    return found, [f"{name}:{number}: {count}, the first U+{ord(char):04X}"]


def decode(data: bytes, markdown: bool, errors: str) -> str | None:
    """`data`'s text, or None: Markdown not strictly UTF-8, or a binary file.
    Lenient UTF-8 handles each byte it cannot decode as `errors` says.

    Strict UTF-8 takes NUL bytes, so a NUL cannot switch the scan off; lenient
    UTF-8, one bad byte hiding nothing, only a file without them, as scanning
    random bytes would turn up a bidi control about once per 2 MB.
    """
    codecs = ["utf-8"]
    if not markdown:  # UTF-32LE's mark starts with UTF-16LE's: tried first
        if data.startswith((b"\xff\xfe\0\0", b"\0\0\xfe\xff")):
            codecs.insert(0, "utf-32")
        elif data.startswith((b"\xff\xfe", b"\xfe\xff")):
            codecs.insert(0, "utf-16")
    for codec in codecs:
        try:
            return data.decode(codec)
        except UnicodeDecodeError:
            pass
    if markdown or b"\0" in data:
        return None
    return data.decode("utf-8", errors=errors)


def characters(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Each hidden character in `text`, then each piece of debris, by line number."""
    critical: list[tuple[int, str]] = []
    debris: list[tuple[int, str]] = []
    if text.isascii():  # most files: nothing to look for
        return critical, debris
    for number, line in enumerate(text.split("\n"), 1):
        critical += [(number, char) for char in CRITICAL_CHARS.findall(line)]
        debris += [(number, char) for char in WARNING_CHARS.findall(line)]
    return critical, debris


def show(text: str) -> str:
    """`text` with each hidden or unprintable character escaped, as Python would,
    so printing it reorders or hides nothing."""
    return "".join(
        char.encode("unicode_escape").decode()
        if CRITICAL_CHARS.match(char) or not char.isprintable()
        else char
        for char in text
    )


def _describe(char: str) -> str:
    code = ord(char)
    return f"U+{code:04X} ({_class(code)})"


def _class(char: int) -> str:
    return next(name for a, b, name in CRITICAL if a <= char <= b)
