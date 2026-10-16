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
# perhaps followed by further arguments.
REFERENCE = re.compile(
    r"(?<![\w./:~\\<@-])(?<!\]\()(?<!=[\"'])"
    r"/(?P<slash>[A-Za-z0-9][A-Za-z0-9._-]*+)(?!/|:\w)"
    r"|\bSkill\(\s*(?:skill\s*[:=]\s*)?(?P<q>[\"']?)"
    r"(?P<tool>[A-Za-z0-9][A-Za-z0-9._-]*+)(?P=q)\s*[,)]"
)


@dataclass(frozen=True)
class Reference:
    name: str
    kind: str  # "slash" or "skill-tool"
    text: str  # as written: `/name` or `Skill(name)`
    file: Path


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
        for match in REFERENCE.finditer(text):
            if match["slash"]:
                name = match["slash"].rstrip(".")
                found.append(Reference(name, "slash", f"/{name}", file))
            else:
                name = match["tool"]
                found.append(Reference(name, "skill-tool", f"Skill({name})", file))
    return found, warnings


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
