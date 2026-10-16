"""Deployed names: carried into each renamed skill's `name:` and every reference."""

import re
from pathlib import Path

from skill_graft import references
from skill_graft.config import Config, SkillId
from skill_graft.errors import SkillGraftError
from skill_graft.hull import Hull

# Names the harnesses APM deploys to already use: Claude Code's built-in commands,
# bundled skills and their aliases, and Codex's slash commands, from their docs.
SHIPPED = (
    "add-dir advisor agents allowed-tools android app approve apps archive"
    " artifact-capabilities artifact-diagramming artifacts autocompact autofix-pr"
    " auto-mode-setup background batch bg branch btw bug cd checkpoint checkup"
    " chrome claude-api claude-in-chrome clean clear code-review color compact"
    " config context continue copy cost cwd daemon dataviz debug debug-config"
    " deep-research delete design design-login design-sync desktop diff doctor"
    " effort exit experimental export fast feedback fewer-permission-prompts focus"
    " fork goal heapdump help hooks ide import init insights install-github-app"
    " install-slack-app ios keybindings keymap list-agents login logout loop mcp"
    " memories memory mention mobile model new output-style passes permissions pet"
    " pets plan plugin plugin-authoring plugins powerup pr-comments privacy-settings"
    " proactive ps pwd quit radio rate-limit-options raw rc recap release-notes"
    " reload-plugins reload-skills remote-control remote-env rename reset resume"
    " review rewind routines run run-skill-generator sandbox schedule scroll-speed"
    " security-review settings setup-bedrock setup-default-sandbox setup-vertex"
    " share side simplify skill-doctor skills slides stats status statusline"
    " stickers stop subagents subtask tasks team-onboarding teleport terminal-setup"
    " theme title tui ultraplan ultrareview undo update-config upgrade usage"
    " usage-credits verify vim voice warnings web-setup workflow-authoring workflows"
    " worktree"
).split()

# A name YAML reads back as this very string when written plain.
PLAIN = re.compile(r"[a-z][a-z0-9-]*")
# Plain words YAML 1.1 reads as a bool or null.
YAML_WORDS = {"y", "n", "yes", "no", "on", "off", "true", "false", "null"}


def unused(config: Config, skills: dict[SkillId, Path]) -> list[str]:
    """A warning per `[rename]` key naming no hull skill."""
    return [
        f'[rename] "{key}" renames no skill in the hull'
        for key in config.renames
        if key not in skills
    ]


def _hint(config: Config, skill: SkillId) -> str:
    """The `[rename]` line to write, or to change: never a second key."""
    if skill in config.renames:
        return f'change [rename] "{skill}" = "{config.renames[skill]}"'
    return f'[rename] "{skill}" = "{skill.alias}-{skill.name}"'


def check_unique(config: Config, names: dict[SkillId, str]) -> None:
    """No two skills share a deployed name.

    Compared ignoring case: on a case-insensitive file system the folders collide.
    The hint names a skill not yet renamed, if one is.
    """
    by_name: dict[str, list[SkillId]] = {}
    for skill, name in names.items():
        by_name.setdefault(name.casefold(), []).append(skill)
    for clashing in by_name.values():
        if len(clashing) > 1:
            taken = " / ".join(sorted({repr(names[skill]) for skill in clashing}))
            ids = ", ".join(str(skill) for skill in clashing)
            unrenamed = [skill for skill in clashing if skill not in config.renames]
            hint = _hint(config, (unrenamed or clashing)[-1])
            raise SkillGraftError(
                f"deployed name {taken} is taken by several skills: {ids}; "
                f"rename one: {hint}"
            )


def check_reserved(config: Config, names: dict[SkillId, str]) -> list[str]:
    """Errors on a deployed name the user reserved; warnings for shipped ones.

    Compared ignoring case. The suggested rename is offered unless the skill
    already has one: then the user chose the name.
    """
    mine = {name.casefold() for name in config.reserved}
    shipped = {name.casefold() for name in SHIPPED}
    warnings = []
    for skill, name in names.items():
        if name.casefold() in mine:
            raise SkillGraftError(
                f"`{skill}` deploys as `{name}`, which `reserved` lists; "
                f"rename it: {_hint(config, skill)}"
            )
        if name.casefold() in shipped:
            warnings.append(
                f"`{skill}` deploys as `{name}`, a name the harness already uses"
                + ("" if skill in config.renames else f"; {_hint(config, skill)}")
            )
    return warnings


def rewrites(hull: Hull) -> dict[SkillId, dict[Path, bytes]]:
    """Per hull skill, the files whose vendored bytes differ from upstream.

    A reference whose target's deployed name differs from the name written is
    rewritten in place; a renamed skill's `SKILL.md` gets its new `name:`. Keyed
    by the path relative to the skill's folder; unchanged files are left out.
    """
    result: dict[SkillId, dict[Path, bytes]] = {}
    for skill, folder in hull.skills.items():
        by_file: dict[Path, list[tuple[tuple[int, int], str, str]]] = {}
        for ref, target in hull.occurrences.get(skill, []):
            if (new := hull.deployed[target]) != ref.name:
                by_file.setdefault(ref.file, []).append((ref.span, ref.name, new))
        renamed = hull.deployed[skill] != skill.name
        if renamed:
            by_file.setdefault(folder / "SKILL.md", [])
        changed = {}
        for file, spans in by_file.items():
            try:
                text = file.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError) as error:  # changed since the scan
                raise SkillGraftError(f"{file} cannot be rewritten: {error}") from None
            for (start, end), old, new in sorted(spans, reverse=True):  # back to front
                if text[start:end] != old:  # edited since the scan: offsets are stale
                    raise SkillGraftError(f"{file} changed while building; run again")
                text = f"{text[:start]}{new}{text[end:]}"
            if renamed and file == folder / "SKILL.md":
                text = set_name(text, hull.deployed[skill])
            changed[file.relative_to(folder)] = text.encode()
        if changed:
            result[skill] = changed
    return result


def set_name(text: str, name: str) -> str:
    """`text` of a `SKILL.md` whose front matter `name:` is `name`.

    Replaces the `name:` line, else adds one atop the front matter, else adds a
    front matter. Line endings and a BOM are kept.
    """
    value = name if PLAIN.fullmatch(name) and name not in YAML_WORDS else f'"{name}"'
    found = references.front_matter(text)
    if found is None:
        bom = "\ufeff" if text.startswith("\ufeff") else ""
        return f"{bom}---\nname: {value}\n---\n{text.removeprefix(bom)}"
    opened, line = found
    start, end = line or (opened, opened)
    ending = _ending(text[start:end] if line else text[:opened])
    return f"{text[:start]}name: {value}{ending}{text[end:]}"


def _ending(line: str) -> str:
    """The line break `line` ends with."""
    return line[len(line.rstrip("\r\n")) :]
