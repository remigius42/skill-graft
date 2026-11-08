# Tasks

One commit per task. Every mutmut run is `nice -n 19 ionice -c 3 uv run mutmut run "skill_graft.cli.*"`. Group 2 is
test-first: each test fails against its mutant (`mutmut apply <mutant>`, reverted after) before it passes on the code.
Per task there: first rerun the module, as numbers shift; verify the rerun leaves only known noise (wording, mypy
refusals) and `_parser`'s, and `uv run pytest` passes. Counts are from `46385538`; see `design.md` for each survivor's
kind.

## 1. Refactors: equivalent mutants dropped, help texts into `_TEXT`

- [x] 1.1 `refactor(cli): drop what mutmut's equivalent mutants show redundant`: `_Command.__init__` with
  `formatter_class` and `allow_abbrev` as keywords of `super().__init__`, no `*args`; `_Version` without
  `default=argparse.SUPPRESS`; `_origin` returning `""` when `direct_url.json` is missing, before `json.loads`;
  `_main`'s prune check through `vars(args).get("dry_run")`; `--format` without its default and pragma; the module-level
  constants `_DISTRIBUTION`, `_VERSION` and `_WHITESPACE`; verify `uv run pytest` passes before any new test, and
  `skill-graft --help` and each command's help print the same as before
- [x] 1.2 `refactor(cli): option help texts in _TEXT`: `_review_options`' description suffix and `--dry-run` help, and
  both `--diff-file` helps, as `_TEXT` entries (`"resolve: review"`, `"resolve --dry-run"`, `"resolve --diff-file"`,
  `"update --diff-file"`); `_diff_file_option(parser, text)`; verify each command's help prints the same as before
- [x] 1.3 `refactor(cli): wrap descriptions as help texts, then indent them`: `_Formatter._fill_text` joins
  `_split_lines`' lines and indents them with `textwrap.indent` (first 2 pragmas, which silenced mutants of the call
  that tests kill: see `design.md`); verify each command's help prints the same as before, and the rerun lists no
  `_fill_text` mutant

## 2. Survivors killed

- [x] 2.1 `main` (16) and `_fails_on_flush` (1), in `tests/cli/test_cli.py`: native Windows refused in-process; a stdout
  whose flush fails, after `help` (exit 1, the error line), `--help` (exit 1) and a usage error (exit 2, no error line
  of the flush)
- [x] 2.2 `_Formatter` (2), `_origin` (1), `_main` (3): help of each command with `COLUMNS=50` has no line after the
  usage longer than 48, and a git install's upper-case commit, in `tests/cli/test_cli.py`; `init` leaves a stale export
  and `deploy` removes one, in `tests/cli/test_cache.py`

## 3. The baseline

- [x] 3.1 Rerun `skill_graft.cli.*`; the `cli` row of `CONTRIBUTING.md`'s baseline to its new count, triaged as
  `_parser`'s usage wording and known noise, and the total of survivors with it; verify the markdown hooks pass
