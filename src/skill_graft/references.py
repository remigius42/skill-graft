"""Finds the slash and Skill tool references in a skill's Markdown files."""

import re
from dataclasses import dataclass
from pathlib import Path

from skill_graft import files
from skill_graft.errors import SkillGraftError

# `/name` as its own token: not inside a path, URL or tag, nor a Markdown link
# target (`](/x)`), an attribute (`="/x"`) or an alias (`@/x`). The possessive `*+`
# keeps the name whole, so `/my-dir/file` never yields `my`. Or the Skill tool's
# call form, `Skill(name)`, the name quoted or not, as `skill=` or `skill:`, and
# perhaps followed by further arguments. Or prose: a code span holding just a
# name, or a bare hyphenated name, bounded as a slash name is: never an anchor,
# a query value or a variable (`#x`, `=x`, `?x`, `&x`, `$x`).
REFERENCE = re.compile(
    r"(?<![\w./:~\\<@-])(?<!\]\()(?<!=[\"'])"
    r"/(?P<slash>[A-Za-z0-9][A-Za-z0-9._-]*+)(?!/|:\w)"
    r"|\bSkill\(\s*(?:skill\s*[:=]\s*)?(?P<q>[\"']?)"
    r"(?P<tool>[A-Za-z0-9][A-Za-z0-9._-]*+)(?P=q)\s*[,)]"
    r"|(?<!`)`(?P<code>[A-Za-z0-9][A-Za-z0-9._-]*+)`(?!`)"
    r"|(?<![\w./:~\\<@#=?&$-])(?<!\]\()(?<!=[\"'])"
    r"(?P<prose>[a-z0-9]++(?:-[a-z0-9]++)++)(?![\w/-]|[.:]\w)"
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
        for match in REFERENCE.finditer(text):
            if skip and skip[0] <= match.start() < skip[1]:
                continue  # the skill's own name, never a reference
            group = next(g for g in FORMS if match[g])
            name = match[group].rstrip(".") if group == "slash" else match[group]
            start = match.start(group)
            kind, text_form = FORMS[group]
            found.append(
                Reference(
                    name, kind, text_form.format(name), file, (start, start + len(name))
                )
            )
    return found, warnings


def front_matter(text: str) -> tuple[int, tuple[int, int] | None] | None:
    """Where the front matter opens, as `read_name` finds it: the offset just past
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
    """The offsets of the front matter's `name:` line, as `read_name` finds it."""
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
