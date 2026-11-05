"""Vets one skill as deployed: the lines worth reading before trusting it, as flags.

Patterns, never a verdict: a flag is no fault, and no flag is no pass. Line-wise
regular expressions, approximate by design: easy to evade, and noisy.
"""

import posixpath
import re
from collections.abc import Callable
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


def _commands(*names: str) -> str:
    """Any of these command names, as a word: not part of a dotted or hyphenated
    name, so `.ssh` and `ssh-keygen` are no `ssh`; `/usr/bin/ssh` is."""
    return rf"(?<![\w.-])(?:{'|'.join(names)})(?![\w-])"


_SHELLS = "sh|bash|zsh|dash|ksh|fish|pwsh|powershell"
# What runs code piped into it: a shell, or an interpreter reading its stdin.
_PIPED = f"{_SHELLS}|iex|python[23]?|node|perl|ruby"

# Each `rm`'s options: the run of them after the command.
_RM = re.compile(r"\brm((?:\s+-[\w-]+)+)", re.IGNORECASE)
_DESTRUCTIVE = re.compile(
    r"\bdd\s+if=|\bmkfs\b|\bshred\b|:\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
    re.IGNORECASE,
)


def _destructive(line: str) -> bool:
    """Whether `line` removes recursively and by force, or wipes a disk or file."""
    for options in _RM.findall(line):
        words = options.split()
        short = "".join(w[1:] for w in words if not w.startswith("--"))
        if ("--recursive" in words or "r" in short.lower()) and (
            "--force" in words or "f" in short
        ):
            return True
    return bool(_DESTRUCTIVE.search(line))


# Each pattern a line is matched against, by name: `<category>.<what>`.
_PATTERNS: dict[str, str | Callable[[str], bool]] = {
    "read.secret-store": (
        r"(?<![\w.])\.(?:ssh|aws|gnupg|env|netrc|npmrc|pypirc)\b"
        r"|\bid_(?:rsa|ed25519)\b|\bkeychain\b|\bcredentials\b"
    ),
    # Patterns start where a run starts, and scan the line from its start at most
    # once: a backtracking one would take quadratic time over a crafted line.
    "send.url": r"(?<![a-z0-9+.-])[a-z][a-z0-9+.-]*://",
    "send.network-tool": (
        _commands("curl", "wget", "nc", "ncat", "scp", "ssh", "Invoke-WebRequest")
        + r"|^(?=.*\brsync\b).*\s[\w.@-]+:"
    ),
    "send.network-call": (r"\brequests\.|\burllib\b|\bhttpx\b|\bfetch\s*\(|\bsocket\b"),
    "send.web-tool": r"\bWeb(?:Fetch|Search)\b",
    "send.push": r"\bgit\s+push\b|\bgh\s+(?:pr\s+create|gist)\b",
    "send.mail": _commands("sendmail", "mailx?", "smtplib", "smtp"),
    "run.shell-block": rf"^\s*(?:```|~~~)\s*(?:{_SHELLS}|shell|console)\b",
    "run.pipe-to-shell": rf"\|\s*(?:sudo\s+)?(?:{_PIPED})(?![\w-])",
    "run.eval": (
        r"\beval\b|\bexec\s*\(|\bos\.system\b|\bsubprocess\b"
        rf"|\b(?:{_SHELLS})\s+-c\b"
    ),
    "run.destructive": _destructive,
}
_COMPILED: list[tuple[str, Callable[[str], object]]] = [
    (name, re.compile(test, re.IGNORECASE).search if isinstance(test, str) else test)
    for name, test in _PATTERNS.items()
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
    for path, (data, executable) in view.items():
        if executable:
            found.append(Flag(path, 0, "run.executable"))
        decoded = hidden.decode_as(data, path.lower().endswith(".md"), "replace")
        if decoded is None:
            found.append(Flag(path, 0, "unreviewable.binary"))
            continue
        text, encoding = decoded
        if encoding != "UTF-8":
            found.append(Flag(path, 0, "unreviewable.encoding"))
        for number, line in enumerate(text.split("\n"), 1):
            names = _line(line)
            if number == 1 and line.startswith("#!"):
                names.add("run.shebang")
            found += [Flag(path, number, name) for name in sorted(names)]
    return found


def _line(line: str) -> set[str]:
    """The patterns `line` matches."""
    found = {name for name, test in _COMPILED if test(line)}
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
