"""A tokenizer for the Python `re` syntax skill-graft's patterns use, and the
mutation operators over its tokens.

Not `re._parser`: it is private, changes between Python versions, and cannot
write a pattern back.
"""

import re
import warnings
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


@dataclass(frozen=True)
class Mutant:
    """A pattern's text with one token changed: by which operator, where."""

    operator: str
    offset: int
    text: str
    flags: int

    def compile(self) -> re.Pattern[str]:
        return re.compile(self.text, self.flags)


def _class_items(token: Token) -> list[tuple[int, int]]:
    """The start and end, in the pattern, of each item of a class token: a
    character, an escape or a range."""
    text = token.text
    j = 2 if text.startswith("[^") else 1
    items = []
    while j < len(text) - 1:
        start = j
        j = _escape(text, j) if text[j] == "\\" else j + 1
        if text[j] == "-" and j + 1 < len(text) - 1:  # a range, not a last `-`
            j += 1
            j = _escape(text, j) if text[j] == "\\" else j + 1
        items.append((token.offset + start, token.offset + j))
    return items


def _quantifier(token: Token) -> list[tuple[str, str]]:
    """Each operator's replacement for a quantifier token."""
    text = token.text
    base = text[: text.index("}") + 1] if text[0] == "{" else text[0]
    suffix = text[len(base) :]
    found = []
    if base == "+":
        found.append(("plus-to-star", "*" + suffix))
    elif base == "*":
        found.append(("star-to-plus", "+" + suffix))
    elif base == "?":
        found.append(("drop-optional", ""))
    else:
        bounds = _BOUNDS.fullmatch(base)
        assert bounds is not None
        low, high = (bounds[1], bounds[1]) if bounds[1] else (bounds[2], bounds[3])
        exact = bool(bounds[1])

        def written(low: str, high: str | None) -> str:
            if exact:
                return f"{{{low}}}{suffix}"
            return f"{{{low},{'' if high is None else high}}}{suffix}"

        if low:
            if int(low) > 0:
                found.append(("min-1", written(str(int(low) - 1), high)))
            found.append(("min+1", written(str(int(low) + 1), high)))
        if high and not exact:
            if int(high) > 0:
                found.append(("max-1", written(low, str(int(high) - 1))))
            found.append(("max+1", written(low, str(int(high) + 1))))
            found.append(("unbounded", written(low, None)))
    if suffix == "+":
        found.append(("drop-possessive", base))
    return found


def _groups(tokens: list[Token]) -> tuple[dict[int, int], dict[int, list[int]]]:
    """Each opener's matching close, and the alternation tokens of each group
    holding any, by its opener, -1 for the whole pattern: all by token index."""
    closes: dict[int, int] = {}
    stack: list[int] = [-1]
    bars: dict[int, list[int]] = {-1: []}
    for index, token in enumerate(tokens):
        if token.kind in ("open", "lookaround", "atomic"):
            stack.append(index)
            bars[index] = []
        elif token.kind == "close":
            closes[stack.pop()] = index
        elif token.kind == "alternation":
            bars[stack[-1]].append(index)
    return closes, {opener: b for opener, b in bars.items() if b}


def _edits(pattern: str, tokens: list[Token]) -> list[tuple[str, int, int, int, str]]:
    """Each mutation as operator, offset, and the span it replaces with text."""
    closes, alternations = _groups(tokens)
    edits = []
    for index, token in enumerate(tokens):
        start, end = token.offset, token.offset + len(token.text)
        if token.kind == "quantifier":
            for operator, text in _quantifier(token):
                edits.append((operator, start, start, end, text))
        elif token.kind == "class":
            for item_start, item_end in _class_items(token):
                edits.append(("drop-class-item", item_start, item_start, item_end, ""))
            negated = token.text.startswith("[^")
            edits.append(
                (
                    "negate-class",
                    start,
                    start,
                    start + 1 + negated,
                    "[" if negated else "[^",
                )
            )
        elif token.kind == "anchor":
            edits.append(("drop-anchor", start, start, end, ""))
        elif token.kind == "atomic":
            edits.append(("plain-atomic", start, start, end, "(?:"))
        elif token.kind == "lookaround":
            close = tokens[closes[index]]
            edits.append(("drop-lookaround", start, start, close.offset + 1, ""))
    for opener, group in alternations.items():
        begin = 0 if opener < 0 else tokens[opener].offset + len(tokens[opener].text)
        finish = len(pattern) if opener < 0 else tokens[closes[opener]].offset
        starts = [begin] + [tokens[b].offset + 1 for b in group]
        ends = [tokens[b].offset for b in group] + [finish]
        for number, (branch_start, branch_end) in enumerate(zip(starts, ends)):
            if number < len(group):
                edits.append(
                    ("drop-branch", branch_start, branch_start, branch_end + 1, "")
                )
            else:
                edits.append(
                    ("drop-branch", branch_start, branch_start - 1, branch_end, "")
                )
    return edits


def mutants(pattern: re.Pattern[str]) -> list[Mutant]:
    """Every mutant of `pattern` that compiles with its flags and differs from it
    and from each mutant before it, by offset."""
    text = pattern.pattern
    seen = {text}
    found = []
    for operator, offset, start, end, new in _edits(text, tokenize(text)):
        mutant = Mutant(
            operator, offset, text[:start] + new + text[end:], pattern.flags
        )
        if mutant.text in seen:
            continue
        seen.add(mutant.text)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mutant.compile()
        except re.error:
            continue
        found.append(mutant)
    return sorted(found, key=lambda m: m.offset)
