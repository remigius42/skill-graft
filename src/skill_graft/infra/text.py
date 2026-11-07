"""Hidden characters, which a reader of the rendered text never sees, and text
shown with them escaped."""

import re

# The critical set of APM 0.35.0's install check
# (`apm_cli/security/content_scanner.py`), copied as `apm_cli` is no API. Lone
# surrogates are left out: strict decoding refuses them, lenient replaces them.
# Each critical class: its code points, first and last, and what it is called.
CRITICAL = [
    (0xE0001, 0xE007F, "tag character"),
    (0x202A, 0x202E, "bidi control"),  # embeddings, overrides and their pop
    (0x2066, 0x2069, "bidi control"),  # isolates
    (0xE0100, 0xE01EF, "variation selector"),  # supplementary
]


def ranges(code_points: list[tuple[int, int]]) -> re.Pattern[str]:
    return re.compile("[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in code_points) + "]")


CRITICAL_CHARS = ranges([(a, b) for a, b, _ in CRITICAL])


# Python's escapes, as `show` writes them.
ESCAPE = "unicode_escape"


def show(text: str) -> str:
    """`text` with each hidden or unprintable character escaped, as Python would,
    so printing it reorders or hides nothing."""
    return "".join(
        char.encode(ESCAPE).decode()
        if CRITICAL_CHARS.match(char) or not char.isprintable()
        else char
        for char in text
    )
