"""Every regex over Upstream text runs in linear time (ADR 0011): a pumped input
per pattern, timed, and a guard that every module-level pattern has one."""

import ast
import importlib
import inspect
import re
import time
from collections.abc import Iterable
from types import ModuleType

import pytest

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
    if not callable(function):
        return False
    try:
        arguments = ast.literal_eval(f"({call[3]},)") if call[3] else ()
        inspect.signature(function).bind(*arguments)
    except (TypeError, ValueError, SyntaxError):
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
    entries = [
        *ALL_NAMES,
        "vet._GONE",
        "deployed._hunks(False)",
        "deployed._escaped(x)",
    ]
    entries.append("vet._PATTERNS:x")

    assert problems(entries) == [
        "entry vet._GONE names no pattern",
        "entry deployed._hunks(False) names no pattern",
        "entry deployed._escaped(x) names no pattern",
        "entry vet._PATTERNS:x names no pattern",
    ]


N = 100_000
# Pumped inputs every `vet._PATTERNS` entry is timed on, besides its own.
GENERIC = ["a" * N, "a." * (N // 2), "a-" * (N // 2), "a " * (N // 2), " " * N]

# Each pattern's entry: the call the code makes with it, and inputs of about
# `N` characters shaped to make it backtrack. `deployed._escaped` is built on
# call; its patterns' entries call it.
REGISTRY: dict[str, tuple[str, list[str] | list[bytes]]] = {
    "apm.COMMENT": (
        "sub",
        ["a" + " " * N + "b", " " * N, "x" + " #" * (N // 2) + "\nb"],
    ),
    "discovery.COMMENT": (
        "sub",
        ["a" + " " * N + "b", " " * N, "a #" * (N // 3), "x" + " #" * (N // 2) + "\nb"],
    ),
    "config.NAME": ("fullmatch", ["a" * N + "!", "a-" * (N // 2) + "!"]),
    "config.SEGMENT": ("fullmatch", ["." * N + "!", ".a" * (N // 2) + "!"]),
    "config.REF": ("fullmatch", ["0" * N]),
    "config.URL": ("fullmatch", ["https://" + "a" * N + "\n"]),
    "config.SCP": ("fullmatch", ["a" * N, "a@" * (N // 2), "a@" + "a" * N + "\n"]),
    "config.COUNT": ("fullmatch", ["1" * N + "x"]),
    "config.BUDGET": ("fullmatch", ["1" * (N // 2) + "." + "1" * (N // 2) + "x"]),
    "rename.PLAIN": ("fullmatch", ["a" * N + "!", "a-" * (N // 2) + "!"]),
    "patch.HUNK": (
        "findall",
        [b"@@ -1" + b"1" * N, b"@@ -1,1 +1," + b"1" * N, b"@@ -1\n" * (N // 6)],
    ),
    "patch.GIT_FORMAT": ("search", [b"diff --gi\n" * (N // 10)]),
    "references.REFERENCE": (
        "finditer",
        [
            "`x`/a" * (N // 5),
            "Skill(" + "a" * N,
            "Skill(a," + "a" * N,
            "Skill(skill: " + " " * N,
            "/" + "a" * N + "/",
            "a-" * (N // 2),
            "a" * N + "-",
            "`" + "a" * N,
        ],
    ),
    "references.SKILL_TOOL": ("finditer", ["Skill " * (N // 6), "`Skill`" * (N // 7)]),
    "references.SENTENCE_END": (
        "search",
        [
            "." + ")" * N + "a",
            ". " + " " * N + "a",
            "\n" + " " * N + "x",
            "a." * (N // 2),
            "e.g. " * (N // 5),
        ],
    ),
    "references.BACKTICK_RUN_OR_NEWLINE": ("finditer", ["`" * N, "`a" * (N // 2)]),
    "references.QUOTED_NAME": ("finditer", ['"' + "a" * N, "`a" * (N // 2)]),
    "vet._RM": ("findall", ["rm -" + "r" * N, "rm " + "-r " * (N // 3)]),
    "vet._DESTRUCTIVE": ("search", [":(){ " + " " * N, "dd " + " " * N]),
    "vet._CHMOD": ("findall", ["chmod " * (N // 6), "chmod " + "-a " * (N // 3)]),
    "vet._OCTAL": ("fullmatch", ["0" * N + "8"]),
    "vet._SYMBOLIC": ("fullmatch", ["u" * N + "!", "u+" + "r" * N + "!"]),
    "vet._KEY": ("match", ["a" * N, "a" + " " * N]),
    "vet._TOKEN": ("findall", ["a" * N, "${HOME" * (N // 6), "a " * (N // 2)]),
    "vet._OUTSIDE": ("match", ["~" + "a" * N, "/" + "a" * N, "$HOME" + "a" * N]),
    "vet._DISCARDS": ("sub", ["1" * N, "1" * N + ">", ">" + " " * N]),
    "vet._WRITES": ("search", ["sed " + " " * N, "a" * N]),
    "vet._PATTERNS:read.secret-store": ("search", [".a" * (N // 2), "id_" * (N // 3)]),
    "vet._PATTERNS:send.url": ("search", ["a" * N + ":/"]),
    "vet._PATTERNS:send.network-tool": (
        "search",
        ["rsync " * (N // 6), "rsync " + "a" * N, "rsync " + " a" * (N // 2)],
    ),
    "vet._PATTERNS:send.network-call": ("search", ["fetch" + " " * N]),
    "vet._PATTERNS:send.web-tool": ("search", ["Web" * (N // 3)]),
    "vet._PATTERNS:send.push": ("search", ["git " + " " * N, "gh pr " + " " * N]),
    "vet._PATTERNS:send.mail": ("search", ["mail" * (N // 4)]),
    "vet._PATTERNS:run.shell-block": ("search", ["```" + " " * N]),
    "vet._PATTERNS:run.pipe-to-shell": ("search", ["|" + " " * N, "| sudo " + " " * N]),
    "vet._PATTERNS:run.eval": ("search", ["bash" + " " * N]),
    "vet._PATTERNS:privilege.sudo": ("search", ["sudo-" * (N // 5)]),
    "vet._PATTERNS:privilege.su": ("search", ["su-" * (N // 3)]),
    "vet._PATTERNS:privilege.doas": ("search", ["doas-" * (N // 5)]),
    "vet._PATTERNS:privilege.pkexec": ("search", ["pkexec-" * (N // 7)]),
    "vet._PATTERNS:privilege.runas": ("search", ["runas-" * (N // 6)]),
    "vet._PATTERNS:privilege.chown-root": ("search", ["chown " + "-a " * (N // 3)]),
    "vet._PATTERNS:persistence.agent-config": ("search", [".claude" * (N // 7)]),
    "vet._PATTERNS:persistence.hooks": ("search", ['"hooks"' + " " * N]),
    "vet._PATTERNS:persistence.shell-rc": ("search", [".bashrc" * (N // 7)]),
    "vet._PATTERNS:persistence.scheduler": (
        "search",
        ["systemctl " + " " * N, "systemctl --user " + " " * N],
    ),
    "vet._PATTERNS:permission.skip-prompts": ("search", ["-" * N]),
    "vet._PATTERNS:permission.no-ask": (
        "search",
        ["do " + " " * N, "without" + " " * N],
    ),
    "vet._PATTERNS:unreviewable.encoded-blob": (
        "search",
        [("a" * 199 + "!") * (N // 200)],
    ),
    "vet._PATTERNS:unreviewable.long-line": (
        "search",
        [("a" * 1000 + "\n") * (N // 1001)],
    ),
    "hidden.WARNING_CHARS": ("findall", ["a" * N]),
    "text.CRITICAL_CHARS": ("findall", ["a" * N]),
    "deployed._escaped(False)": ("sub", ["a" * N, "\\" * N]),
    "deployed._escaped(True)": ("sub", ["a" * N, "\\" * N]),
}
for _entry, (_call, _inputs) in REGISTRY.items():
    if _entry.startswith("vet._PATTERNS:"):
        _inputs += GENERIC  # type: ignore[operator]


def resolve(entry: str) -> re.Pattern[str] | re.Pattern[bytes]:
    """The pattern `entry` names, looked up now, so that a patched one is timed:
    a `vet._PATTERNS` entry through `vet._COMPILED`, a call by calling."""
    if entry.startswith("vet._PATTERNS:"):
        flag = entry.removeprefix("vet._PATTERNS:")
        test = dict(module("vet")._COMPILED)[flag]
        pattern = test.__self__
    elif call := re.fullmatch(r"(\w+)\.(\w+)\((.*)\)", entry):
        pattern = getattr(module(call[1]), call[2])(ast.literal_eval(call[3]))
    else:
        short, name = entry.split(".", 1)
        pattern = getattr(module(short), name)
    assert isinstance(pattern, re.Pattern)
    return pattern


def test_every_pattern_has_an_entry() -> None:
    assert problems(REGISTRY) == []


@pytest.mark.linear_time
@pytest.mark.parametrize("entry", REGISTRY)
def test_pumped_input_takes_linear_time(entry: str) -> None:
    call, inputs = REGISTRY[entry]
    pattern = resolve(entry)
    method = getattr(pattern, call)
    for text in inputs:
        start = time.perf_counter()
        if call == "sub":
            method(type(text)(), text)
        elif call == "finditer":
            for _ in method(text):
                pass
        else:
            method(text)
        elapsed = time.perf_counter() - start

        assert elapsed < 1, f"{text[:20]!a}: {elapsed:.1f} s"
