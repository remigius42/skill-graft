"""Vets one skill as deployed: the lines worth reading before trusting it, as flags.

Patterns, never a verdict: a flag is no fault, and no flag is no pass. Line-wise
regular expressions, approximate by design: easy to evade, and noisy.
"""

import posixpath
import re
from dataclasses import dataclass

from skill_graft.pipeline import hidden
from skill_graft.pipeline.deployed import View

# Each category's risk IDs: the OWASP Top 10 for LLM Applications 2025 (LLM) and
# for Agentic Applications 2026 (ASI).
OWASP = {
    "read": ("LLM02",),
    "write": ("ASI02",),
    "send": ("LLM02", "ASI02"),
    "run": ("ASI05",),
    "privilege": ("ASI03",),
    "persistence": ("ASI06",),
    "permission": ("ASI02",),
    "unreviewable": ("LLM03",),
}

# Each pattern a line is matched against, by name: `<category>.<what>`.
_PATTERNS = {
    "read.secret-store": (
        r"(?<![\w.])\.(?:ssh|aws|gnupg|env|netrc|npmrc|pypirc)\b"
        r"|\bid_(?:rsa|ed25519)\b|\bkeychain\b|\bcredentials\b"
    ),
}
_COMPILED = [
    (name, re.compile(regex, re.IGNORECASE)) for name, regex in _PATTERNS.items()
]

# A path-like token; `${HOME}` holds braces, which end any other.
_TOKEN = re.compile(r"""(?:\$\{HOME\}|[^\s'"`()<>|;,=\[\]{}])+""")
# A token outside the project by its start: absolute with a folder, as a lone
# `/name` is a slash command; the home folder.
_OUTSIDE = re.compile(r"/[^/]+/|~(?:/|[A-Za-z_][\w.-]*/|$)|\$(?:HOME|\{HOME\})(?:/|$)")
# A redirection that discards output, or joins one stream to another: no write,
# and `/dev/null` no path outside the project.
_DISCARDS = re.compile(r"(?<!\d)\d*>(?:>?\s*/dev/null\b|&\d)")
# What writes: a redirection, a command or a word.
_WRITES = re.compile(
    r"(?<![-=<>])>|\b(?:tee|cp|mv|install|ln|mkdir|touch|sed\s+-i"
    r"|(?:write|save|append)s?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Flag:
    """A pattern found at a line of a file; line 0 is the file as a whole."""

    file: str
    line: int
    pattern: str  # `<category>.<what>`

    @property
    def category(self) -> str:
        return self.pattern.split(".", 1)[0]


def scan(view: View) -> list[Flag]:
    """Each flag of the skill whose deployed files `view` holds, file by file in
    the view's order, then by line and pattern.

    Each file is read as resolution reads it; one read in another encoding than
    strict UTF-8 is flagged as a whole, and still scanned. Lines are split at line
    feeds and numbered from 1, as the hidden character check numbers them.
    """
    found = []
    for path, (data, _) in view.items():
        decoded = hidden.decode_as(data, path.lower().endswith(".md"), "replace")
        if decoded is None:
            found.append(Flag(path, 0, "unreviewable.binary"))
            continue
        text, encoding = decoded
        if encoding != "UTF-8":
            found.append(Flag(path, 0, "unreviewable.encoding"))
        for number, line in enumerate(text.split("\n"), 1):
            found += [Flag(path, number, name) for name in sorted(_line(line))]
    return found


def _line(line: str) -> set[str]:
    """The patterns `line` matches."""
    found = {name for name, regex in _COMPILED if regex.search(line)}
    kept = _DISCARDS.sub(" ", line)
    if any(_outside(token) for token in _TOKEN.findall(kept)):
        found.add("write.outside-path" if _WRITES.search(kept) else "read.outside-path")
    return found


def _outside(token: str) -> bool:
    """Whether path-like `token` leads outside the project: by its start, or by
    climbing above it. A URL's path is no path."""
    if "://" in token:
        return False
    return (
        bool(_OUTSIDE.match(token)) or posixpath.normpath(token).split("/")[0] == ".."
    )
