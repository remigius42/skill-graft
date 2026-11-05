# Tasks

Test-first: each task's test fails before its code, then passes. One commit per task. The `CHANGELOG.md` entry comes
with the archive commit.

## 1. The comment pattern

- [x] 1.1 `discovery.COMMENT` becomes `(?<!\s)\s+#.*$`; verify a test in `tests/pipeline/test_discovery.py` reads a
  `name:` of `a`, 100 000 spaces and `b` within a second as that whole value (red: the old pattern takes about 26 s), a
  test in `tests/commands/test_resolve.py` has `resolve` exit non-zero within seconds on that **Skill** as an **Entry**,
  and the existing comment and quote tests still pass (skill-discovery, "Long run of whitespace")
- [x] 1.2 `apm.COMMENT` the same; verify a test in `tests/infra/test_apm.py` over an `apm.yml` line `- a`, 100 000
  spaces, `b` (an inner run: the scan strips a line's ends before the pattern) finishes within a second, red before the
  fix, and the existing `apm.yml` scan tests pass

## 2. Linear time, kept

- [ ] 2.1 The `linear_time` marker in `pyproject.toml`, on `test_send_and_run_take_linear_time` and
  `test_privilege_takes_linear_time` in `tests/pipeline/test_vet.py` and `test_long_line_scans_in_linear_time` in
  `tests/pipeline/test_references.py`; verify `uv run pytest -m linear_time` selects exactly them and passes
- [ ] 2.2 `tests/cli/test_linear_time.py`: the guard, collecting every module-level `re.Pattern` of `discovery`,
  `references`, `vet` (with each string pattern of `_PATTERNS`), `hidden`, `text`, `patch`, `rename`, `deployed`,
  `config` and `apm` as distinct objects, a by-name import counting once; failing on each without an entry under any of
  its names, and on each entry naming neither a pattern nor a function returning one; verify it fails naming every
  pattern once against an empty registry
- [ ] 2.3 The registry: per pattern, a `linear_time` case with id `<module>.<name>`, the call the code makes and a
  pumped input of about 100 000 characters, timed under one second, the pattern resolved by `getattr` at test time,
  `_PATTERNS:` entries through `_COMPILED`'s bound `search.__self__`, `deployed._escaped(False)` and
  `deployed._escaped(True)` each called once before the clock starts; verify the guard and every case pass, and that
  restoring `\s+#.*$` in either module fails its case
- [ ] 2.4 ADR 0011, "Regexes over **Upstream** text run in linear time", extending 0007: the means, an entry by hand for
  a pattern built in a function, the options considered, the **Deployed diff**'s cap kept; verify the markdown hooks
  pass

## 3. The mutation harness (`mutation/`, `tests/test_mutation.py`)

- [ ] 3.1 `operators.py`: the tokenizer, and `pythonpath = ["."]` in `[tool.pytest.ini_options]` so tests import
  `mutation`; verify tests split escapes, classes with a leading `]` or `^`, group openers, lookarounds, quantifiers
  with lazy and possessive suffixes and `{m,n}`, and alternation, and join back to the original text for every target
  pattern
- [ ] 3.2 The operators (quantifier, `{n}` and `{m,n}` bounds included, class, anchor and lookaround, alternation,
  possessive and atomic), each mutant with its operator and offset, those that do not compile, unchanged and repeated
  ones dropped; verify a test per operator on a small pattern, and `{3,4}` giving `{2,4}`, `{4,4}`, `{3,3}`, `{3,5}` and
  `{3,}`
- [ ] 3.3 `targets.py` and `plugin.py`: the security-relevant targets, with extra test files where the layers miss a use
  (`deployed`'s for `CRITICAL_CHARS` and `WARNING_CHARS`, `tests/cli/test_vet_corpus.py` for `vet`'s); the mutant
  patched in at `pytest_configure` on every `skill_graft` module attribute bound to the original, a `_PATTERNS:` target
  by replacing its `_COMPILED` tuple with the mutant's `search`, with the original's flags; the failed tests and whether
  all carry `linear_time` written out; verify a test runs pytest with the plugin on one mutant of `config.NAME`, sees
  `discovery.NAME` patched too and a test fail that the original passes, one does the same for a `_PATTERNS:` target,
  and every target resolves
- [ ] 3.4 `__main__.py` and `equivalent.toml`: per target, the existing test files of every module holding the pattern,
  its extra files and its registry cases by node id; the unpatched run first; then each mutant in its own pytest process
  without `-x`, one per CPU, stopped past its timeout; a timeout or a kill by `linear_time` tests alone confirmed by a
  run on its own; the report printed with `ascii()`; exit 1 on an unlisted survivor or a stale entry; verify tests of
  the test selection for `config.NAME` and `text.CRITICAL_CHARS` (no `tests/infra/test_text.py`), of the verdict over
  given results (killed, timed out and confirmed or not, timing-only confirmed or not, listed, unlisted, stale), and
  that a failing unpatched run stops it
- [ ] 3.5 `CONTRIBUTING.md` (how and when to run it), a row in `docs/README.md`, a bullet in `AGENTS.md`'s Tests section
  (opt-in, never in hooks or CI; run it after changing a target pattern), new words in `.cspell.yaml`; verify the hooks
  pass

## 4. Gaps the harness finds

Per target module: run `uv run python -m mutation <its targets>`; for each surviving mutant, a test in that module's
test file that kills it, or its entry in `equivalent.toml` with the reason.

- [ ] 4.1 `vet`; verify its run exits 0 and `uv run pytest` passes
- [ ] 4.2 `references`; verify its run exits 0 and `uv run pytest` passes
- [ ] 4.3 `config` and `discovery`; verify their run exits 0 and `uv run pytest` passes
- [ ] 4.4 `text` and `hidden`; verify their run exits 0, the whole `uv run python -m mutation` exits 0, and
  `uv run pytest` passes
