"""Finds the slash and Skill tool references in a skill's Markdown files."""

import re
from dataclasses import dataclass
from pathlib import Path

from skill_graft.infra import files
from skill_graft.infra.errors import SkillGraftError

# `/name` as its own token: not inside a path, URL or tag, nor a Markdown link
# target (`](/x)`), an attribute (`="/x"`) or an alias (`@/x`), nor a quoted first
# argument or list item (`('/x'`, `["/x"`), nor a path after an interpolation
# (`${x}/y`); `scan` also drops one right after a code span closes
# (`` `package.json`/x ``). The possessive `*+` keeps the name whole, so
# `/my-dir/file` never yields `my`. Or the Skill tool's
# call form, `Skill(name)`, the name quoted or not, as `skill=` or `skill:`, and
# perhaps followed by further arguments. Or prose: a code span holding just a
# name, or a bare hyphenated name, bounded as a slash name is: never an anchor,
# a query value or a variable (`#x`, `=x`, `?x`, `&x`, `$x`).
REFERENCE = re.compile(
    r"(?<![\w./:~\\<@}-])(?<!\]\()(?<!=[\"'])"
    r"(?<![(\[][\"'])"
    r"/(?P<slash>[A-Za-z0-9][A-Za-z0-9._-]*+)(?!/|:\w)"
    r"|\bSkill\(\s*(?:skill\s*[:=]\s*)?(?P<q>[\"']?)"
    r"(?P<tool>[A-Za-z0-9][A-Za-z0-9._-]*+)(?P=q)\s*(?:\)|,[^)\n]*+\)?)"
    r"|(?<!`)`(?P<code>[A-Za-z0-9][A-Za-z0-9._-]*+)`(?!`)"
    r"|(?<![\w./:~\\<@#=?&$-])(?<!\]\()(?<!=[\"'])"
    r"(?P<prose>[a-z0-9]++(?:-[a-z0-9]++)++)(?![\w/%+-]|[.:]\w)"
)

# The Skill tool named in a sentence (`Call the Skill tool with "grilling".`): the
# names after it, in double quotes or backticks, up to the sentence's end. That is
# the next `Skill tool`, a blank line, a line opening a list item, heading, code
# fence or table row, or `.`, `!` or `?` (perhaps closing quotes, emphasis or
# brackets) before whitespace and the start of a sentence (a capital letter, a code
# span, emphasis or a bracket) or the end of the text. `e.g.`, `i.e.` and a
# lowercase continuation do not end it.
SKILL_TOOL = re.compile(r"(?<!\w)(?:`Skill`|Skill) tool\b")
SENTENCE_END = re.compile(
    r"\n[ \t]*\n|\n[ \t]*(?:(?:[-*+]|\d+\.|#+)[ \t]|```|~~~|\|)"
    r"|(?<!\be\.g)(?<!\bi\.e)(?P<stop>[.!?][\"'`*)\]]*)"
    r"(?:\s+(?=[A-Z`*(\[\"'])|\s*\Z)"
)
BACKTICK_RUN = re.compile(r"`+")
QUOTED_NAME = re.compile(
    r'(?P<open>["`])(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*+)(?P=open)'
)

# Each named group of REFERENCE: the kind it gives, and how it is written.
FORMS = {
    "slash": ("slash", "/{}"),
    "tool": ("skill-tool", "Skill({})"),
    "code": ("prose", "`{}`"),
    "prose": ("prose", "{}"),
}


@dataclass(frozen=True)
class Reference:
    name: str
    kind: str  # "slash", "skill-tool" or "prose"
    text: str  # as written: `/name`, `Skill(name)`, `` `name` `` or `name`
    file: Path
    span: tuple[int, int]  # the name's offsets in the file's decoded text
    sentence: bool = False  # named in a Skill tool sentence: counts only if it resolves


def scan(folder: Path) -> tuple[list[Reference], list[str]]:
    """The references in `folder`'s Markdown files, in order, and warnings.

    Reads files, so the skill's symlinks must be checked first: a link to a
    device or FIFO would never end. A file that is not UTF-8 is skipped.
    """
    found, warnings = [], []
    for file in _markdown_files(folder):
        try:
            text = file.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            warnings.append(f"{file} is not UTF-8: references in it are not followed")
            continue
        except OSError as error:
            raise SkillGraftError(f"{file} cannot be read: {error}") from None
        skip = name_line(text) if file == folder / "SKILL.md" else None
        tool_words = [m.span() for m in SKILL_TOOL.finditer(text)]  # `` `Skill` tool ``
        named = [
            ref
            for ref in _sentence_names(text, file, tool_words)
            if not (skip and skip[0] <= ref.span[0] < skip[1])
        ]
        taken = {ref.span for ref in named}
        here, calls = [], []
        for match in REFERENCE.finditer(text):
            if skip and skip[0] <= match.start() < skip[1]:
                continue  # the skill's own name, never a reference
            group = next(g for g in FORMS if match[g])
            if group == "prose" and _yaml_key(text, match):
                continue
            if group == "slash" and _after_code_span(text, match.start()):
                continue
            name = match[group].rstrip(".") if group == "slash" else match[group]
            start = match.start(group)
            kind, text_form = FORMS[group]
            span = (start, start + len(name))
            if kind == "prose" and (
                span in taken or any(_inside(span, w) for w in tool_words)
            ):
                continue  # the sentence names it, or it is the tool's own name
            if kind != "prose":
                calls.append(match.span())
            here.append(Reference(name, kind, text_form.format(name), file, span))
        # A call keeps the names inside it: `Skill("x")` in a Skill tool sentence.
        named = [r for r in named if not any(_inside(r.span, c) for c in calls)]
        found += sorted(here + named, key=lambda ref: ref.span)
    return found, warnings


def _sentence_names(
    text: str, file: Path, tool_words: list[tuple[int, int]]
) -> list[Reference]:
    """The names a Skill tool sentence quotes after `Skill tool` (`tool_words`, its
    spans), one trailing `.` dropped; each window ends where its sentence does, or
    where the next `Skill tool` starts."""
    names = []
    for i, (_, start) in enumerate(tool_words):
        limit = tool_words[i + 1][0] if i + 1 < len(tool_words) else len(text)
        end = SENTENCE_END.search(text, start, limit)
        stop = limit if end is None else end.start() + len(end["stop"] or "")
        for match in QUOTED_NAME.finditer(text, start, stop):
            name = match["name"].removesuffix(".")
            begin = match.start("name")
            quote = match["open"]
            names.append(
                Reference(
                    name,
                    "skill-tool",
                    f"Skill tool {quote}{name}{quote}",
                    file,
                    (begin, begin + len(name)),
                    sentence=True,
                )
            )
    return names


def _after_code_span(text: str, slash: int) -> bool:
    """Whether the `/` at `slash` follows backticks that close a code span: an odd
    number of backtick runs (`` ` `` or ``` `` ```) before them on their line."""
    if text[slash - 1 : slash] != "`":
        return False
    line_start = text.rfind("\n", 0, slash - 1) + 1
    before = text[line_start:slash].rstrip("`")
    return len(BACKTICK_RUN.findall(before)) % 2 == 1


def _inside(span: tuple[int, int], outer: tuple[int, int]) -> bool:
    return outer[0] <= span[0] and span[1] <= outer[1]


def _yaml_key(text: str, match: re.Match[str]) -> bool:
    """Whether the match opens its line, past indent or `- `, followed by `:`."""
    before = text[text.rfind("\n", 0, match.start()) + 1 : match.start()]
    return text[match.end() : match.end() + 1] == ":" and before.strip() in ("", "-")


def front_matter(text: str) -> tuple[int, tuple[int, int] | None] | None:
    """Where the front matter opens, for `read_name` too: the offset just past
    its opening `---` line, and the offsets of its `name:` line if any. None when
    `text` has no front matter: no opening fence, or none closing it.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].lstrip("\ufeff").rstrip() != "---":
        return None
    start = opened = len(lines[0])
    found = None
    for line in lines[1:]:
        if line.rstrip() == "---":
            return opened, found
        if found is None and line.startswith("name:"):
            found = (start, start + len(line))
        start += len(line)
    return None


def name_line(text: str) -> tuple[int, int] | None:
    """The offsets of the front matter's first `name:` line, if any."""
    found = front_matter(text)
    return found[1] if found else None


def _markdown_files(folder: Path) -> list[Path]:
    """Every `*.md` under `folder`, `.git` skipped: `SKILL.md`, then by path."""
    markdown = [
        f
        for f in files.skill_entries(folder)
        if f.name.lower().endswith(".md") and not f.is_dir()
    ]
    return sorted(
        markdown, key=lambda f: (f != folder / "SKILL.md", f.relative_to(folder).parts)
    )
