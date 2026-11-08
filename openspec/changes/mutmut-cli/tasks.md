# Tasks

One commit per task. Every mutmut run is `nice -n 19 ionice -c 3 uv run mutmut run "skill_graft.cli.*"`. Group 2 is
test-first: each test fails against its mutant (`mutmut apply <mutant>`, reverted after) before it passes on the code.
Per task there: first rerun the module, as numbers shift; verify the rerun leaves only known noise (wording, mypy
refusals), `_parser`'s and the marked equivalents, and `uv run pytest` passes. Counts are from `46385538`; see
`design.md` for each survivor's kind.

## 1. Refactors: equivalent mutants dropped or marked, help texts into `_TEXT`

- [ ] 1.1 `refactor(cli): drop what mutmut's equivalent mutants show redundant`: `_Command.__init__` with
  `formatter_class` and `allow_abbrev` as keywords of `super().__init__`, no `*args`; `_Version` without
  `default=argparse.SUPPRESS`; `_origin` returning `""` when `direct_url.json` is missing, before `json.loads`;
  `_main`'s prune check through `vars(args).get("dry_run")`; the module-level constants `_DISTRIBUTION`, `_VERSION` and
  `_WHITESPACE`; verify `uv run pytest` passes before any new test, and `skill-graft --help` and each command's help
  print the same as before
- [ ] 1.2 `refactor(cli): option help texts in _TEXT`: `_review_options`' description suffix and `--dry-run` help, and
  `"update --diff-file"` and `"review --diff-file"`, as `_TEXT` entries; `_diff_file_option(parser, help)`; verify each
  command's help prints the same as before
- [ ] 1.3 `refactor(cli): mark mutmut's equivalent mutants`: the 2 pragmas on `_Formatter._fill_text`'s `initial_indent`
  and `subsequent_indent`, each reason above; verify `ruff format` leaves each pragma on its line, and the rerun no
  longer lists them

## 2. Survivors killed

- [ ] 2.1 `main` (16) and `_fails_on_flush` (1), in `tests/cli/test_cli.py`: native Windows refused in-process; a stdout
  whose flush fails, after `help` (exit 1, the error line), `--help` (exit 1) and a usage error (exit 2, no error line
  of the flush)
- [ ] 2.2 `_Formatter` (2), `_origin` (1), `_main` (2): help of `resolve` with `COLUMNS=50` has no line longer than 50,
  and a git install's upper-case commit, in `tests/cli/test_cli.py`; `init` leaves a stale export, in
  `tests/cli/test_cache.py`

## 3. The baseline

- [ ] 3.1 Rerun `skill_graft.cli.*`; the `cli` row of `CONTRIBUTING.md`'s baseline to its new count, triaged as
  `_parser`'s usage wording, known noise and marked equivalents, and the total of survivors with it; verify the markdown
  hooks pass
