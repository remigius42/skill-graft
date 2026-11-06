# Design

## Context

skill-graft compiles about 35 regexes. Those over **Upstream** text sit in `pipeline/discovery.py`,
`pipeline/references.py`, `pipeline/vet.py`, `pipeline/hidden.py` (with `infra/text.py`'s `CRITICAL_CHARS`, which it
imports by name), `pipeline/patch.py`, `pipeline/rename.py`, `pipeline/deployed.py` and `pipeline/config.py`, whose
`NAME` and `SEGMENT` discovery applies to **Upstream** names and folders. Some are already written for linear time
(possessive quantifiers in `references.py`, the comment above `vet._PATTERNS`), and `test_vet.py` and
`test_references.py` already pump lines of about 50 000 characters through `scan` against a one-second limit. A probe of
each pattern, with pumped input and the call it is used with, found one quadratic pattern: `COMMENT`, `\s+#.*$`, in
`discovery.py` and `apm.py`. The four test files of the security-relevant modules run in about two seconds together.

## Goals / Non-Goals

**Goals:**

- Every regex over **Upstream** text provably linear on its known worst shape, and a failing test for the next one added
  without that proof.
- A measure of how tightly the tests pin down what each security-relevant pattern matches.

**Non-Goals:**

- Size caps on **Upstream** files or lines, or a match timeout: rejected (ADR 0011).
- Linear time for regexes over the user's own files or arguments (`skill-graft.toml`, `apm.yml`, `--expect`), though the
  fixed `apm.py` pattern gets its test.
- Mutating patterns outside the security-relevant set, or any non-regex code: mutmut, later, if at all.
- Proving linearity: pumped inputs catch the shapes someone thought of, as the probe did.

## Decisions

### The comment pattern starts where a run of whitespace starts

`(?<!\s)\s+#.*`. With `sub`, `\s+#.*$` is tried at every position of a run of whitespace with no `#` after it, and each
try scans to the run's end: quadratic. The lookbehind lets only the run's first character start a try. A possessive
`\s++` would not help: each start still scans to the run's end. Splitting by hand (`find("#")`, check the character
before it) would also do, but changes two call sites' shape for no gain. The probe's cases (`a # c`, `a#b`, `a  #c`,
`a\t# c d`, `# c` after a space, `a # c # d`, `a`) give the same `sub` and `match` results under both patterns. No `$`:
on a text holding a line feed, each `#` after a space, before it, would scan to the line feed and fail there, quadratic
again (2.3 s for 20 000 of them); both callers pass one line, where `.*` ends at the line's end anyway. The registry
times that shape too.

### One registry of pumped inputs, in `tests/cli/test_linear_time.py`

Linear time is a concern across modules, so it gets one file, where `AGENTS.md` puts cross-cutting tests. Each entry
names a module, a pattern in it, how the code calls it (`search`, `match`, `fullmatch`, `findall`, `finditer`, `sub`)
and one or more pumped inputs. The test resolves the pattern by `getattr` when it runs, never at import, so the mutation
harness's patched pattern is the one timed. A `vet._PATTERNS` entry is named `vet._PATTERNS:<flag name>` and resolved
through `_COMPILED`, whose entries hold the pattern's bound `search`: the pattern is its `__self__`.
`deployed._escaped(doubled)` is built on call, from the whole of Unicode (about 0.4 s), and gives two patterns: two
entries, `deployed._escaped(False)` and `deployed._escaped(True)`, each calling it once before the clock starts. Each
entry is a parametrized case of one test, its id `<module>.<name>`, and every timing test, the existing ones included,
carries a `linear_time` marker, registered in `pyproject.toml`: the harness selects and tells apart timing failures by
it.

Each input is about 100 000 characters and must be matched in under one second. The grilling settled on a million;
measuring showed the slowest linear pattern, `vet._TOKEN.findall`, takes about 35 ms per 40 000 characters, near a
second at a million: too close on a shared CI runner. At 100 000, linear patterns take under 0.1 s and a quadratic one
seconds (`COMMENT` takes 26 s): an order of magnitude either way. Fixed limits, not the ratio of two sizes, because a
ratio is noisy on shared runners. The existing `scan`-level tests in `test_vet.py` and `test_references.py` stay: they
time the patterns as a scan combines them.

### A guard over the registry

Patterns are told apart by object. `re` caches what it compiles, so `discovery.COMMENT` and `apm.COMMENT`, the same text
and flags, are one object: the guard counts them once, and the registry still gives each its own entry, with the call
its module makes. An entry naming a call, `<module>.<function>(<literal arguments>)`, is checked by binding the
arguments and calling it.

A second test in the same file collects every module-level `re.Pattern` of the modules above, plus every string pattern
of `vet._PATTERNS`, as distinct objects: a pattern imported by name (`discovery.NAME` is `config.NAME`,
`hidden.CRITICAL_CHARS` is `text.CRITICAL_CHARS`) is one pattern, and an entry under any of its names covers it. It
fails naming each pattern without an entry, and each entry that names neither a pattern nor a function returning one
(`deployed._escaped`). A new module-level pattern in those modules cannot land without a pumped input, and a renamed one
cannot leave a dead entry. A pattern compiled inside a function, or an inline `re.search(...)`, the guard cannot see:
none reads **Upstream** text today but `_escaped`, and ADR 0011 asks for the entry by hand.

### The harness: `mutation/`, a top-level package

`uv run python -m mutation [target…]`, from the repository root. Its own tests go in `tests/test_mutation.py`, as
`scripts/check_pins.py`'s go in `tests/test_check_pins.py`: they run in hooks and CI; the harness itself never does.
They import it, so `[tool.pytest.ini_options]` gains `pythonpath = ["."]`: `tests/` has no `__init__.py`, and pytest
puts only `tests/` on the path.

- `targets.py`: the security-relevant patterns, as `<module>.<name>`: `vet`'s (`_PATTERNS:*`, `_RM`, `_DESTRUCTIVE`,
  `_CHMOD`, `_OCTAL`, `_SYMBOLIC`, `_KEY`, `_TOKEN`, `_OUTSIDE`, `_DISCARDS`, `_WRITES`), `references`' (`REFERENCE`,
  `SKILL_TOOL`, `SENTENCE_END`, `QUOTED_NAME`, `BACKTICK_RUN_OR_NEWLINE`), `discovery.COMMENT`, `config`'s (`NAME`,
  `SEGMENT`, `URL`, `SCP`, `REF`), `text`'s `CRITICAL_CHARS` and `hidden`'s `WARNING_CHARS`. A target may name extra
  test files, for a use the layers cannot show: `deployed._escaped` builds its pattern from `CRITICAL_CHARS.pattern` and
  `WARNING_CHARS.pattern` without binding either, so both name `tests/pipeline/test_deployed.py` and
  `tests/cli/test_hidden_characters.py`. Each `vet` target names `tests/cli/test_vet_corpus.py`, which checks the
  **Vet**'s **Flags** on graft-vet's labelled corpus in under a second.
- `operators.py`: a tokenizer for the Python `re` syntax these patterns use (escapes, classes, group openers,
  quantifiers with their lazy and possessive suffixes, alternation, anchors, lookarounds), and the operators over its
  tokens: a quantifier changed (`+`→`*`, `*`→`+`, `?` dropped, `{n}`→`{n-1}` and `{n+1}`, either bound of `{m,n}` moved
  by one, `{m,n}`→`{m,}`); a class lost one range or character, or negated; an anchor, `\b` or lookaround removed; an
  alternation branch removed; a possessive quantifier or atomic group made plain. The operators are named
  `plus-to-star`, `star-to-plus`, `drop-optional`, `min-1`, `min+1`, `max-1`, `max+1`, `unbounded`, `drop-possessive`,
  `plain-atomic`, `drop-class-item`, `negate-class`, `drop-anchor`, `drop-lookaround` and `drop-branch`. A mutant is the
  pattern's text with one token changed, identified by operator and character offset: a token's, a class item's, or a
  branch's start. One that does not compile, equals the original, or repeats another is dropped. Not `re._parser`: it is
  private, changes between Python versions, and cannot write a pattern back.
- `plugin.py`: a pytest plugin that reads one mutant from `MUTATION_MUTANT` (JSON: target and text) and patches it in at
  `pytest_configure`, compiled with the original's flags: every attribute of a `skill_graft` module bound to the
  original object, so a by-name import (`discovery.NAME`, `explain.SCP`, `hidden.CRITICAL_CHARS`) gets the mutant too,
  or, for a `_PATTERNS:` target, the `_COMPILED` entry, replaced by a tuple holding the mutant's `search`. It writes
  which tests failed, and whether all of them carry `linear_time`, as JSON to the file `MUTATION_REPORT` names.
- `__main__.py`: runs each target's tests once unpatched (a failure there stops the run with exit code 2, as does an
  unknown target, or a pytest run that writes no report), then each mutant in its own
  `python -m pytest -q -p mutation.plugin`, without `-x`, so every failure is known. The tests: the test file of every
  module holding the pattern, as `tests/` mirrors the layers (`tests/pipeline/test_config.py`,
  `tests/pipeline/test_discovery.py`, `tests/commands/test_explain.py` for `config.NAME`; a module holds a pattern when
  any of its attributes is that object, so `discovery.COMMENT` brings `tests/infra/test_apm.py`, and `config.NAME` names
  `tests/commands/test_edit.py` as an extra file, as `edit` reads it through `config`), those that exist; the target's
  extra files; the pattern's own registry cases by node id, not the whole registry. Mutants run in parallel, one per
  CPU; a subprocess per mutant, with its own `--basetemp` and no cache provider, keeps one mutant's patch and files out
  of the next. The registry's entries are read from its file, to name the cases by node id. A process over its timeout
  (ten times its target's unpatched run, at least 30 s) is stopped. A mutant that timed out, or failed only
  `linear_time` tests, may owe that to load from the others: it is run again alone, and counts as killed only if it
  times out or fails again.
- `equivalent.toml`: per target, the mutants that cannot change behavior, each `{ operator, offset, reason }`. The run
  prints each surviving mutant not listed, and each listed one that no longer survives or exists, of a target run or of
  no target at all, and exits 1 on either; else 0.

A pattern holding invisible characters (`CRITICAL_CHARS`) is printed with `ascii()`, so the harness's output never
carries one.

### ADR 0011

"Regexes over **Upstream** text run in linear time": it extends ADR 0007, names the means (possessive quantifiers,
atomic groups, lookbehind anchoring, the registry and guard, an entry by hand for a pattern built in a function) and the
rejected options: size caps on what patterns read (visible to users, and hide a quadratic pattern rather than remove
it), the `regex` module's timeout (a second runtime dependency), a subprocess timeout per match (costly, and a timeout
is still a failure the user sees). The **Deployed diff**'s 1 MB cap stays: it bounds the diff's own work, not a
pattern's.

### Gaps the harness found

The first full run gave 776 mutants of 47 targets, 349 surviving, in about 17 minutes on 8 CPUs. Survivors were killed
by examples: an `EDGES` table in `tests/pipeline/test_vet.py` (a line, a flag, whether the line has it) and in
`tests/pipeline/test_references.py` (a text, the references found, as written), each between `cspell:disable` and
`cspell:enable`, since lines at a pattern's edge are seldom words; and named tests in `test_config.py`,
`test_discovery.py` and `test_explain.py`. 17 are listed in `equivalent.toml`, each with why it cannot change behavior.
One survivor was a real miss: `vet._OCTAL` with `{2,4}` flags `chmod 77`, a world-writable mode, as are `chmod 7` and
`chmod 2`, which the **Vet** spec's "world-writable modes" covers and `0*([0-7]{3,4})` did not. The pattern becomes
`0*([0-7]{1,4})`, a `Fixed` entry beside the `name:` one; `chmod 0` pins its `{0,4}` mutant. The final run kills the
other 758 of 775 in about 16 minutes.

## Risks / Trade-offs

- [A slow CI runner breaks a one-second limit] → about ten times the margin at 100 000 characters; the existing scan
  tests have held the same limit.
- [Pumped inputs miss a backtracking shape] → the guard forces a reviewed input per pattern; the harness's
  possessive-to-greedy mutants show which tests would not notice backtracking coming back.
- \[Offsets in `equivalent.toml` go stale when a pattern changes\] → a stale entry fails the run, so the file is fixed
  where it drifted.
- [A pattern compiled in a function escapes the guard] → ADR 0011 and review; `_escaped` is the one today.
- [A mutant run's timing checks race the other mutants for CPU] → a kill by timeout or by `linear_time` tests alone is
  confirmed by a run on its own; an unpatched run, which stops the harness on failure, runs before the parallel phase.
- [Mutants killed only by end-to-end tests survive] → they show as survivors: the pattern's own test file gets the test,
  or the entry its reason.

## Migration Plan

None: one pattern changes, with the same results; the rest is tests, tooling and documentation.
