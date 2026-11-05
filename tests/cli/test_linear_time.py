"""Every regex over Upstream text runs in linear time (ADR 0011): a pumped input
per pattern, timed, and a guard that every module-level pattern has one."""

import ast
import importlib
import inspect
import re
from collections.abc import Iterable
from types import ModuleType

# The modules whose module-level patterns read Upstream text, or sit beside those
# that do, by the short name an entry uses.
MODULES = {
    module.rsplit(".", 1)[1]: module
    for module in [
        "skill_graft.pipeline.discovery",
        "skill_graft.pipeline.references",
        "skill_graft.pipeline.vet",
        "skill_graft.pipeline.hidden",
        "skill_graft.infra.text",
        "skill_graft.pipeline.patch",
        "skill_graft.pipeline.rename",
        "skill_graft.pipeline.deployed",
        "skill_graft.pipeline.config",
        "skill_graft.infra.apm",
    ]
}


def module(name: str) -> ModuleType:
    return importlib.import_module(MODULES[name])


def patterns() -> list[list[str]]:
    """Every pattern the guard sees, each as all of its names: a module-level
    `re.Pattern`, one object under every name it is bound to, and each string
    pattern of `vet._PATTERNS`."""
    by_object: dict[int, list[str]] = {}
    for short in MODULES:
        for attribute, value in vars(module(short)).items():
            if isinstance(value, re.Pattern):
                by_object.setdefault(id(value), []).append(f"{short}.{attribute}")
    found = [sorted(names) for names in by_object.values()]
    found += [
        [f"vet._PATTERNS:{flag}"]
        for flag, test in module("vet")._PATTERNS.items()
        if isinstance(test, str)
    ]
    return found


def _builds_a_pattern(entry: str) -> bool:
    """Whether `entry`, as `<module>.<function>(<literal arguments>)`, calls a
    function of the module that returns a pattern."""
    call = re.fullmatch(r"(\w+)\.(\w+)\((.*)\)", entry)
    if not call or call[1] not in MODULES:
        return False
    function = getattr(module(call[1]), call[2], None)
    arguments = ast.literal_eval(f"({call[3]},)") if call[3] else ()
    if not callable(function):
        return False
    try:
        inspect.signature(function).bind(*arguments)
    except TypeError:
        return False
    return isinstance(function(*arguments), re.Pattern)


def problems(entries: Iterable[str]) -> list[str]:
    """Each pattern no entry names under any of its names, then each entry that
    names neither a pattern nor a function call building one."""
    entries = list(entries)
    found = patterns()
    names = {name for group in found for name in group}
    return [
        f"no entry for {' = '.join(group)}"
        for group in found
        if not set(group) & set(entries)
    ] + [
        f"entry {entry} names no pattern"
        for entry in entries
        if entry not in names and not _builds_a_pattern(entry)
    ]


# All the module-level patterns of the modules the guard reads, by name.
ALL_NAMES = [
    "apm.COMMENT",
    "config.BUDGET",
    "config.COUNT",
    "config.NAME",
    "config.REF",
    "config.SCP",
    "config.SEGMENT",
    "config.URL",
    "discovery.COMMENT",
    "discovery.NAME",
    "discovery.SEGMENT",
    "hidden.CRITICAL_CHARS",
    "hidden.WARNING_CHARS",
    "patch.GIT_FORMAT",
    "patch.HUNK",
    "references.BACKTICK_RUN_OR_NEWLINE",
    "references.QUOTED_NAME",
    "references.REFERENCE",
    "references.SENTENCE_END",
    "references.SKILL_TOOL",
    "rename.PLAIN",
    "text.CRITICAL_CHARS",
    "vet._CHMOD",
    "vet._DESTRUCTIVE",
    "vet._DISCARDS",
    "vet._KEY",
    "vet._OCTAL",
    "vet._OUTSIDE",
    "vet._RM",
    "vet._SYMBOLIC",
    "vet._TOKEN",
    "vet._WRITES",
    "vet._PATTERNS:persistence.agent-config",
    "vet._PATTERNS:persistence.hooks",
    "vet._PATTERNS:persistence.scheduler",
    "vet._PATTERNS:persistence.shell-rc",
    "vet._PATTERNS:permission.no-ask",
    "vet._PATTERNS:permission.skip-prompts",
    "vet._PATTERNS:privilege.chown-root",
    "vet._PATTERNS:privilege.doas",
    "vet._PATTERNS:privilege.pkexec",
    "vet._PATTERNS:privilege.runas",
    "vet._PATTERNS:privilege.su",
    "vet._PATTERNS:privilege.sudo",
    "vet._PATTERNS:read.secret-store",
    "vet._PATTERNS:run.eval",
    "vet._PATTERNS:run.pipe-to-shell",
    "vet._PATTERNS:run.shell-block",
    "vet._PATTERNS:send.mail",
    "vet._PATTERNS:send.network-call",
    "vet._PATTERNS:send.network-tool",
    "vet._PATTERNS:send.push",
    "vet._PATTERNS:send.url",
    "vet._PATTERNS:send.web-tool",
    "vet._PATTERNS:unreviewable.encoded-blob",
    "vet._PATTERNS:unreviewable.long-line",
]


def test_guard_names_every_pattern_without_an_entry() -> None:
    named = [
        name
        for problem in problems([])
        for name in problem.removeprefix("no entry for ").split(" = ")
    ]

    assert sorted(named) == sorted(ALL_NAMES)


def test_guard_counts_a_pattern_imported_by_name_once() -> None:
    found = problems([])

    assert "no entry for config.NAME = discovery.NAME" in found
    assert "no entry for hidden.CRITICAL_CHARS = text.CRITICAL_CHARS" in found
    assert problems([n for n in ALL_NAMES if n != "discovery.NAME"])[:1] == []


def test_guard_names_an_entry_that_is_no_pattern() -> None:
    entries = [*ALL_NAMES, "vet._GONE", "deployed._hunks(False)", "vet._PATTERNS:x"]

    assert problems(entries) == [
        "entry vet._GONE names no pattern",
        "entry deployed._hunks(False) names no pattern",
        "entry vet._PATTERNS:x names no pattern",
    ]
