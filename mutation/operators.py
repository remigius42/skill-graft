"""A tokenizer for the Python `re` syntax skill-graft's patterns use, and the
mutation operators over its tokens.

Not `re._parser`: it is private, changes between Python versions, and cannot
write a pattern back.
"""

import re
from dataclasses import dataclass

# A bounded quantifier: `{n}`, `{m,n}`, `{m,}`, `{,n}` or `{,}`, which is `{0,}`;
# `{}` is text.
_BOUNDS = re.compile(r"\{(\d+)\}|\{(\d*),(\d*)\}")
# The escapes longer than one character after the backslash.
_LONG_ESCAPE = re.compile(
    r"x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|N\{[^}]*\}|[0-9]{1,3}"
)
_ANCHORS = {"^", "$", r"\b", r"\B", r"\A", r"\Z"}
_LOOKAROUNDS = ("(?<=", "(?<!", "(?=", "(?!")


@dataclass(frozen=True)
class Token:
    """One piece of a pattern: its kind, its text as written, and its offset."""

    kind: str  # literal, any, escape, anchor, class, open, lookaround, atomic,
    # close, quantifier, alternation, backref, flags or comment
    text: str
    offset: int


def _escape(pattern: str, i: int) -> int:
    """The end of the escape starting with the backslash at `i`."""
    if long := _LONG_ESCAPE.match(pattern, i + 1):
        return long.end()
    return i + 2


def _class_end(pattern: str, i: int) -> int:
    """The end of the character class opening at `i`: a leading `^`, then a
    leading `]`, is part of it, not its end."""
    j = i + 1
    if pattern[j : j + 1] == "^":
        j += 1
    if pattern[j : j + 1] == "]":
        j += 1
    while pattern[j] != "]":
        j = _escape(pattern, j) if pattern[j] == "\\" else j + 1
    return j + 1


def _group(pattern: str, i: int) -> tuple[str, int]:
    """The kind and end of what opens with the `(` at `i`."""
    rest = pattern[i:]
    if not rest.startswith("(?"):
        return "open", i + 1
    for opener in _LOOKAROUNDS:
        if rest.startswith(opener):
            return "lookaround", i + len(opener)
    if rest.startswith("(?>"):
        return "atomic", i + 3
    if rest.startswith("(?:"):
        return "open", i + 3
    if rest.startswith("(?P<"):
        return "open", pattern.index(">", i) + 1
    if rest.startswith("(?P="):
        return "backref", pattern.index(")", i) + 1
    if rest.startswith("(?#"):
        return "comment", pattern.index(")", i) + 1
    flags = re.match(r"\(\?[a-zA-Z-]+(\)|:)", rest)
    if flags is None:
        raise ValueError(f"unknown group at {i}: {pattern!a}")
    return ("flags" if flags[1] == ")" else "open"), i + flags.end()


def tokenize(pattern: str) -> list[Token]:
    """`pattern` as tokens, which join back to it."""
    tokens = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\":
            end = _escape(pattern, i)
            text = pattern[i:end]
            if text in _ANCHORS:
                kind = "anchor"
            elif text[1:].isdigit() and not text.startswith("\\0"):
                kind = "backref"
            else:
                kind = "escape"
        elif char == "[":
            kind, end = "class", _class_end(pattern, i)
        elif char == "(":
            kind, end = _group(pattern, i)
        elif char == ")":
            kind, end = "close", i + 1
        elif char == "|":
            kind, end = "alternation", i + 1
        elif char in "^$":
            kind, end = "anchor", i + 1
        elif char in "*+?" or (char == "{" and _BOUNDS.match(pattern, i)):
            bounds = _BOUNDS.match(pattern, i)
            end = bounds.end() if bounds and char == "{" else i + 1
            if pattern[end : end + 1] in ("?", "+"):
                end += 1
            kind = "quantifier"
        elif char == ".":
            kind, end = "any", i + 1
        else:
            kind, end = "literal", i + 1
        tokens.append(Token(kind, pattern[i:end], i))
        i = end
    return tokens
