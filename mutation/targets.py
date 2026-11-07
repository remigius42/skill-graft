"""The security-relevant patterns the harness mutates, as `<module>.<name>`, and
where each is bound."""

import importlib
import pkgutil
import re
from dataclasses import dataclass
from types import ModuleType

import skill_graft

# The modules targets name, by the short name a target uses.
MODULES = {
    "vet": "skill_graft.pipeline.vet",
    "references": "skill_graft.pipeline.references",
    "discovery": "skill_graft.pipeline.discovery",
    "config": "skill_graft.pipeline.config",
    "text": "skill_graft.infra.text",
    "hidden": "skill_graft.pipeline.hidden",
    "explain": "skill_graft.commands.explain",
}
PATTERNS = "vet._PATTERNS:"


@dataclass(frozen=True)
class Target:
    """A pattern, and test files beyond its holders' that use it."""

    name: str
    extra: tuple[str, ...] = ()


# `deployed._escaped` builds its pattern from these two's text, binding neither.
_DEPLOYED = ("tests/pipeline/test_deployed.py", "tests/cli/test_hidden_characters.py")
# `edit` checks a rename through `config.NAME`, binding no name of its own.
_EDIT = ("tests/commands/test_edit.py",)
# The Vet's flags on graft-vet's labelled corpus.
_CORPUS = ("tests/cli/test_vet_corpus.py",)


def _vet_flags() -> list[str]:
    vet = importlib.import_module(MODULES["vet"])
    return [flag for flag, test in vet._PATTERNS.items() if isinstance(test, str)]


TARGETS = (
    [Target(PATTERNS + flag, _CORPUS) for flag in _vet_flags()]
    + [
        Target(f"vet.{name}", _CORPUS)
        for name in "_RM _DESTRUCTIVE _CHMOD _OCTAL _SYMBOLIC _KEY _TOKEN _OUTSIDE"
        " _DISCARDS _WRITES".split()
    ]
    + [
        Target(f"references.{name}")
        for name in "REFERENCE SKILL_TOOL SENTENCE_END QUOTED_NAME"
        " BACKTICK_RUN_OR_NEWLINE".split()
    ]
    + [Target("discovery.COMMENT")]
    + [Target("config.NAME", _EDIT)]
    + [Target(f"config.{name}") for name in "SEGMENT URL SCP REF".split()]
    + [
        Target("text.CRITICAL_CHARS", _DEPLOYED),
        Target("hidden.WARNING_CHARS", _DEPLOYED),
    ]
    + [Target("explain._UNSAFE_URL")]
)


def module(short: str) -> ModuleType:
    return importlib.import_module(MODULES[short])


def resolve(name: str) -> re.Pattern[str]:
    """The pattern target `name` names, as bound now: a `vet._PATTERNS` one
    through `vet._COMPILED`, which holds its bound `search`."""
    if name.startswith(PATTERNS):
        test = dict(module("vet")._COMPILED)[name.removeprefix(PATTERNS)]
        pattern = test.__self__
    else:
        short, attribute = name.split(".", 1)
        pattern = getattr(module(short), attribute)
    assert isinstance(pattern, re.Pattern) and isinstance(pattern.pattern, str)
    return pattern


def all_modules() -> list[ModuleType]:
    """Every module of `skill_graft`, imported."""
    return [
        importlib.import_module(info.name)
        for info in pkgutil.walk_packages(skill_graft.__path__, "skill_graft.")
    ]


def holders(name: str) -> list[str]:
    """The modules holding target `name`'s pattern: each binding it by any name,
    or `vet` for a `vet._PATTERNS` one."""
    if name.startswith(PATTERNS):
        return [MODULES["vet"]]
    pattern = resolve(name)
    return [
        holder.__name__
        for holder in all_modules()
        if any(value is pattern for value in vars(holder).values())
    ]
