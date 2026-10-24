"""A skill's files as deployed, compared: the summary and the Deployed diff. No git."""

import itertools
import os
import re
import stat
from array import array
from pathlib import Path

from skill_graft.infra import files
from skill_graft.pipeline import hidden

# Each file of a skill as deployed, by path relative to it: its bytes, executable bit.
View = dict[str, tuple[bytes, bool]]

# git's letter escapes in a quoted path; any other byte to quote is octal.
_LETTERS = {
    7: "a",
    8: "b",
    9: "t",
    10: "n",
    11: "v",
    12: "f",
    13: "r",
    34: '"',
    92: "\\",
}

# File lines a summary prints per skill, at most.
_LIMIT = 20


def deployed_files(folder: Path, overrides: dict[Path, bytes]) -> View:
    """Each file of `folder` as vendored, sorted by its path's bytes.

    Symlinks are followed, as the copy does; `.git` is skipped, as it is not copied.
    A file in `overrides`, by path relative to `folder`, has its bytes.
    """
    view = {}
    for file in sorted(
        (f for f in files.skill_entries(folder) if not f.is_dir()),
        key=lambda f: os.fsencode(f.relative_to(folder).as_posix()),
    ):
        relative = file.relative_to(folder)
        content = overrides.get(relative)
        if content is None:
            content = file.read_bytes()
        view[relative.as_posix()] = (content, bool(file.stat().st_mode & stat.S_IXUSR))
    return view


def changed(old: View, new: View) -> list[str]:
    """Each path whose bytes or executable bit differ, sorted by its bytes."""
    return sorted(
        (path for path in old.keys() | new.keys() if old.get(path) != new.get(path)),
        key=os.fsencode,
    )


def summary(old: View, new: View) -> list[str]:
    """A line per file that differs, at most 20 of them; no diff, no text."""
    lines = []
    for path in changed(old, new):
        name = quote(path)
        if path not in new:
            lines.append(f"{name} (removed)")
            continue
        size, executable = len(new[path][0]), new[path][1]
        if path in old:
            line = f"{name} (changed, {len(old[path][0])} -> {size} bytes)"
        else:
            line = f"{name} (new, {size} bytes)"
        if executable != (path in old and old[path][1]):
            line += " (now executable)" if executable else " (no longer executable)"
        lines.append(line)
    if len(lines) > _LIMIT:
        return [*lines[:_LIMIT], f"\u2026 {len(lines) - _LIMIT} more"]
    return lines


def quote(path: str, prefix: str = "") -> str:
    """`prefix + path` as git's `core.quotePath` quotes it, a space quoted too, so
    it is printable ASCII and no two names print alike: `"a/x\\n"`, never `a/"x\\n"`."""
    data = os.fsencode(prefix + path)
    if all(0x20 < byte < 0x7F and byte not in _LETTERS for byte in data):
        return prefix + path
    return '"' + "".join(_escape(byte) for byte in data) + '"'


def _escape(byte: int) -> str:
    if byte in _LETTERS:
        return "\\" + _LETTERS[byte]
    if 0x20 <= byte < 0x7F:
        return chr(byte)
    return f"\\{byte:03o}"


class Budget:
    """The steps the diffs of one run may still take, whatever their files hold."""

    def __init__(self, steps: int = 10**7) -> None:
        self.left = steps


class _Overrun(Exception):
    """A diff needs more steps than its budget has left."""


# Lines of context around each change, as `git diff` shows.
_CONTEXT = 3

# Past this, on either side, a file shows as all removed and all added.
_MAX_BYTES = 1_000_000

# What an editor could break a line at or show as nothing, escaped in a line: every
# control character but tab, the line and paragraph separators, hidden characters;
# and each byte that cannot be decoded, which `surrogateescape` maps to U+DC80-DCFF.
_BREAKS = [(0x00, 0x08), (0x0A, 0x1F), (0x7F, 0x9F), (0x2028, 0x2029), (0xDC80, 0xDCFF)]
_ESCAPED = re.compile(
    "[" + "".join(f"{chr(a)}-{chr(b)}" for a, b in _BREAKS) + "]|"
    f"{hidden.CRITICAL_CHARS.pattern}|{hidden.WARNING_CHARS.pattern}"
)
# The same, each backslash doubled too: for a file whose lines would read alike.
_DOUBLED = re.compile(r"\\|" + _ESCAPED.pattern)

# A changed block: old lines [i1, i2) replaced by new lines [j1, j2).
_Block = tuple[int, int, int, int]


def diff(old: View, new: View, budget: Budget) -> str:
    """Each file that differs as a unified diff in git's format, every file as text.

    Steps are counted against `budget`, shared by the run: a file whose diff would
    overrun it, or over 1 MB, shows as all its old lines removed and new ones added.
    """
    return "".join(
        "".join(_file_diff(path, old.get(path), new.get(path), budget))
        for path in changed(old, new)
    )


def _file_diff(
    path: str,
    before: tuple[bytes, bool] | None,
    after: tuple[bytes, bool] | None,
    budget: Budget,
) -> list[str]:
    a_name, b_name = quote(path, "a/"), quote(path, "b/")
    out = [f"diff --git {a_name} {b_name}\n"]
    if before is None and after is not None:
        out.append(f"new file mode {_mode(after[1])}\n")
    elif after is None and before is not None:
        out.append(f"deleted file mode {_mode(before[1])}\n")
    elif before is not None and after is not None and before[1] != after[1]:
        out += [f"old mode {_mode(before[1])}\n", f"new mode {_mode(after[1])}\n"]
    a = _lines(path, before[0]) if before else []
    b = _lines(path, after[0]) if after else []
    if before and after and before[0] != after[0] and a == b:  # re-encoded
        a, b = _split(_raw(before[0])), _split(_raw(after[0]))
        note = "shown byte for byte, as its two sides read alike as text"
        out.insert(0, f"# {quote(path)}: {note}\n")
    escaped = _ESCAPED
    if _alike(a, b):  # a typed `\x80` and a stray byte: only the doubling tells
        escaped = _DOUBLED
        note = "each backslash shown doubled, as its lines would read alike"
        out.insert(0, f"# {quote(path)}: {note}\n")
    too_big = any(f is not None and len(f[0]) > _MAX_BYTES for f in (before, after))
    hunks = _hunks(a, b, _blocks(a, b, too_big, budget), escaped)
    if hunks:
        out.append(f"--- {a_name if before else '/dev/null'}\n")
        out.append(f"+++ {b_name if after else '/dev/null'}\n")
    return out + hunks


def _alike(a: list[str], b: list[str]) -> bool:
    """Whether two different lines of `a` and `b` would read alike, escaped."""
    lines = set(a) | set(b)
    if not any("\\" in line for line in lines):  # no escape can be typed out
        return False
    return len({_ESCAPED.sub(_escape_char, line) for line in lines}) < len(lines)


def _mode(executable: bool) -> str:
    return "100755" if executable else "100644"


def _lines(path: str, data: bytes) -> list[str]:
    """`data` as text, split at line feeds only, each line with its own."""
    text = hidden.decode(data, path.lower().endswith(".md"), "surrogateescape")
    return _split(_raw(data) if text is None else text)


def _raw(data: bytes) -> str:
    """`data` as lenient UTF-8, each byte that cannot be decoded kept apart."""
    return data.decode("utf-8", errors="surrogateescape")


def _split(text: str) -> list[str]:
    """`text` split at line feeds only, each line with its own."""
    *lines, last = text.split("\n")
    return [line + "\n" for line in lines] + ([last] if last else [])


def _blocks(a: list[str], b: list[str], too_big: bool, budget: Budget) -> list[_Block]:
    """The changed blocks from `a` to `b`, in order."""
    whole = [(0, len(a), 0, len(b))] if a or b else []
    if too_big:
        return whole
    codes: dict[str, int] = {}  # one step to compare two lines, whatever their length
    x = [codes.setdefault(line, len(codes)) for line in a]
    y = [codes.setdefault(line, len(codes)) for line in b]
    start, end_x, end_y = 0, len(x), len(y)
    while start < end_x and start < end_y and x[start] == y[start]:
        start += 1
    while end_x > start and end_y > start and x[end_x - 1] == y[end_y - 1]:
        end_x, end_y = end_x - 1, end_y - 1
    if start == end_x or start == end_y:  # only lines added, or only removed
        return [(start, end_x, start, end_y)] if end_x + end_y > 2 * start else []
    try:
        ops = _myers(x[start:end_x], y[start:end_y], budget)
    except _Overrun:
        return whole
    blocks = []
    i = j = start
    for equal, run in itertools.groupby(ops, key=lambda op: op == "="):
        steps = list(run)
        if equal:
            i, j = i + len(steps), j + len(steps)
            continue
        removed, added = steps.count("-"), steps.count("+")
        blocks.append((i, i + removed, j, j + added))
        i, j = i + removed, j + added
    return blocks


def _myers(a: list[int], b: list[int], budget: Budget) -> str:
    """The shortest edit script from `a` to `b`: `=`, `-` or `+` per line.

    Counts each diagonal tried, each pair of lines compared and each entry kept
    against `budget`; keeps only the 2D + 1 diagonals of each D for the backtrack.
    """
    n, m = len(a), len(b)
    left = budget.left
    trace: list[array[int]] = []
    try:
        for d in range(n + m + 1):
            if 2 * d + 1 > left:
                raise _Overrun
            left -= 2 * d + 1
            row = array("i", [-1]) * (2 * d + 1)
            for k in range(-d, d + 1, 2):
                if not left:
                    raise _Overrun
                left -= 1
                x = _start(trace[-1], d, k, n, m)[0] if d else 0
                if x < 0:
                    continue
                room = min(n - x, m - x + k)
                stop = min(room, left)
                s = 0
                while s < stop and a[x + s] == b[x - k + s]:
                    s += 1
                left -= min(s + 1, stop)
                if s == stop < room:
                    raise _Overrun
                row[k + d] = x + s
                if x + s == n and x + s - k == m:
                    trace.append(row)
                    return _backtrack(trace, n, m)
            trace.append(row)
    finally:
        budget.left = left
    raise AssertionError("unreachable: D = n + m reaches the end")


def _start(last: "array[int]", d: int, k: int, n: int, m: int) -> tuple[int, bool]:
    """Where diagonal `k` starts at D = `d`, and whether from `k + 1`, a line added,
    else from `k - 1`, a line removed: the one reaching further inside the grid.

    -1 when neither does. `last` holds D - 1's diagonals, -1 for one not reached.
    """
    down = last[k + d] if k != d else -1
    if down - k > m:
        down = -1
    right = last[k + d - 2] + 1 if k != -d and last[k + d - 2] >= 0 else -1
    if right > n:
        right = -1
    return (down, True) if down >= right else (right, False)


def _backtrack(trace: "list[array[int]]", n: int, m: int) -> str:
    """The edit script of the path `_myers` found, from its end back."""
    ops: list[str] = []
    x, y = n, m
    for d in range(len(trace) - 1, 0, -1):
        k = x - y
        start, down = _start(trace[d - 1], d, k, n, m)
        ops += "=" * (x - start)
        ops.append("+" if down else "-")
        x = start if down else start - 1
        y = x - (k + 1 if down else k - 1)
    ops += "=" * x
    return "".join(reversed(ops))


def _hunks(
    a: list[str], b: list[str], blocks: list[_Block], escaped: re.Pattern[str]
) -> list[str]:
    """The blocks as hunks, merged as `git diff` merges them, with their context."""
    groups: list[list[_Block]] = []
    for block in blocks:
        if groups and block[0] - groups[-1][-1][1] <= 2 * _CONTEXT:
            groups[-1].append(block)
        else:
            groups.append([block])
    out = []
    for group in groups:
        i1 = max(0, group[0][0] - _CONTEXT)
        i2 = min(len(a), group[-1][1] + _CONTEXT)
        j1, j2 = group[0][2] - (group[0][0] - i1), group[-1][3] + (i2 - group[-1][1])
        out.append(f"@@ -{_range(i1, i2)} +{_range(j1, j2)} @@\n")
        i = i1
        for block_i1, block_i2, block_j1, block_j2 in group:
            out += _show(" ", a[i:block_i1], escaped)
            out += _show("-", a[block_i1:block_i2], escaped)
            out += _show("+", b[block_j1:block_j2], escaped)
            i = block_i2
        out += _show(" ", a[i:i2], escaped)
    return out


def _range(start: int, end: int) -> str:
    """A hunk header's range: its first line, then its count unless 1."""
    count = end - start
    if count == 1:
        return str(start + 1)
    return f"{start + 1 if count else start},{count}"


def _show(mark: str, lines: list[str], escaped: re.Pattern[str]) -> list[str]:
    out = []
    for line in lines:
        out.append(f"{mark}{escaped.sub(_escape_char, line.removesuffix(chr(10)))}\n")
        if not line.endswith("\n"):
            out.append("\\ No newline at end of file\n")
    return out


def _escape_char(match: re.Match[str]) -> str:
    char = match.group()
    if char == "\\":
        return "\\\\"
    code = ord(char)
    if 0xDC80 <= code <= 0xDCFF:  # a byte that cannot be decoded
        return f"\\x{code - 0xDC00:02x}"
    if code <= 0xFF:
        return f"\\x{code:02x}"
    return f"\\u{code:04x}" if code <= 0xFFFF else f"\\U{code:08x}"
