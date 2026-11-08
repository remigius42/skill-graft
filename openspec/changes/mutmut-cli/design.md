# Design

## Context

`nice -n 19 ionice -c 3 uv run mutmut run "skill_graft.cli.*"` on `46385538` left 105 survivors of 874 mutants (769
killed), 12 fewer than the baseline's 117: `_parser`'s 37, usage wording `mutmut-src` triaged, and 68 others. Each one's
diff, read once (`mutmut show`), falls in one of five kinds:

| Function                  | Survivors | To kill | Dropped | To `_TEXT` | mypy refuses | Wording |
| ------------------------- | --------: | ------: | ------: | ---------: | -----------: | ------: |
| `main`                    |        18 |      16 |       0 |          0 |            2 |       0 |
| `_review_options`         |         9 |       0 |       0 |          6 |            1 |       2 |
| `_diff_file_option`       |         8 |       0 |       0 |          2 |            0 |       6 |
| `_main`                   |         8 |       2 |       2 |          0 |            1 |       3 |
| `_Formatter._fill_text`   |         4 |       1 |       2 |          0 |            1 |       0 |
| `_version`                |         4 |       0 |       4 |          0 |            0 |       0 |
| `_Command.__init__`       |         3 |       0 |       3 |          0 |            0 |       0 |
| `_into`                   |         3 |       0 |       0 |          0 |            0 |       3 |
| `_Formatter._split_lines` |         2 |       1 |       0 |          0 |            1 |       0 |
| `_fails_on_flush`         |         2 |       1 |       0 |          0 |            1 |       0 |
| `_origin`                 |         2 |       1 |       1 |          0 |            0 |       0 |
| `_Version.__init__`       |         2 |       0 |       2 |          0 |            0 |       0 |
| `_Version.__call__`       |         2 |       0 |       2 |          0 |            0 |       0 |
| `_flat`                   |         1 |       0 |       1 |          0 |            0 |       0 |
| all                       |        68 |      22 |      17 |          8 |            7 |      14 |

"Dropped" are equivalent mutants a removed redundancy or a module-level constant leaves without a counterpart; "To
`_TEXT`" wording mutants of help texts that move into the table, which mutmut never mutates. The mypy kind is `None` for
a `bool` (`break_on_hyphens`, `_fails_on_flush`'s `failed`), for an `Exception` (`print_error`) and for a `str`
(`_diff_file_option`'s text, `parser.error`'s message). The wording kind: `_main`'s and `_into`'s error messages, and
the `--dry-run` and `--diff-file` options' `help` and `metavar` set to `None` or dropped, as `_parser`'s 37 are. No
survivor is a bug. Mutant numbers are mutmut's at `46385538`; they shift with edits, so each task reruns the module
first.

Most gaps share one cause, as `mutmut-src`'s design foresaw: the tests of native Windows (`ON_WINDOWS`) and of a closed
stdout (`tests/cli/test_warnings.py`) start `skill-graft` in a subprocess, which imports the checkout through the
editable install, not mutmut's mutant.

## Goals / Non-Goals

**Goals:** `cli.py` with no survivor but known noise and `_parser`'s, and no pragma.

**Non-Goals:** `_parser` (triaged in `mutmut-src`); testing message wording; changing what a user sees, help text
included.

## Decisions

### Seams: `main`

`main` is `cli.py`'s one public function; every test goes through it, as the existing ones do. No test calls `_origin`,
`_Formatter` or another private name. The prune test goes in `tests/cli/test_cache.py`, beside
`test_dry_run_prunes_nothing` and `test_failed_command_prunes_too`, which cover the same line; the rest in
`tests/cli/test_cli.py`.

### Gaps

- Native Windows, in-process (8): `main` with `sys.platform` patched to `win32` returns 1, prints `WINDOWS`'s line on
  stderr and nothing on stdout. The subprocess tests stay: only they show no command module loads.
- A failed flush of stdout (9, with `_fails_on_flush`'s `return True`): with a stdout whose writes succeed and whose
  flush fails, and `discards` keeping the real one, a command that succeeds (`help`) returns 1 and prints the error
  line; `--help` exits 1 the same way; a usage error exits 2 with no error line of the flush. The conftest's
  `ClosedStdout` fails on write too, so the command would fail first: the test defines the flush-only stdout.
- Help at the terminal's width (2): `_Formatter` passes `width` to `textwrap`; dropped, it wraps at 70. With `COLUMNS`
  set to 50, no line of any command's help is longer than 48, the width argparse wraps at.
- A git install's upper-case commit (1): `_origin` accepts `[0-9a-fA-F]`; with `commit_id` upper-case, `--version` shows
  its first seven characters as they are.
- `init` prunes nothing (2): `_main` skips `housekeeping.prune` for `init`; with a stale export in the cache, `init`
  leaves it.

### Equivalent mutants: dropped, none marked

`CONTRIBUTING.md`'s rule: remove what an equivalent mutant shows redundant, or restructure so none exists, or name the
value in a module-level constant; only then the equivalent expression alone on a line of its own, a bare
`# pragma: no mutate` on it, `# Equivalent mutants: <reason>` above. No regions.

**Removed or restructured (8):**

- `_Command.__init__` (3): its `kwargs.setdefault`s become keywords of the `super().__init__` call,
  `formatter_class=_Formatter, allow_abbrev=False`, and its `*args` goes: `_Parser` and argparse's `add_parser` pass
  keywords only, never these two. `allow_abbrev=None`, which acted as `False`, is then a `bool` mypy refuses, and a
  dropped one is `True`, which `test_prefix_of_an_option` kills.
- `_Version.__init__`'s `default=argparse.SUPPRESS` (2): it only keeps `version` out of the namespace, which nothing
  reads; `None` there, its mutants' value, changes no output.
- `_origin`'s `or "{}"` (1): with no `direct_url.json`, it returns `""` at once, before `json.loads`; `"XX{}XX"` failed
  to parse and returned `""` as well.
- `_main`'s `getattr(args, "dry_run", False)` (2): `vars(args).get("dry_run")`, whose missing key is `None`, with no
  default to mutate. Its `None` and `True` mutants were the one equivalent and one gap: no test runs a command without
  `--dry-run` that succeeds and prunes; `deploy` in `test_failed_command_prunes_too` never runs, as `resolve` fails
  first. The restructure leaves no mutant for that test to kill, so none is added.

**Named in a module-level constant (7):** mutmut mutates only functions.

- `_DISTRIBUTION = "skill-graft"` (2): `importlib.metadata` normalizes the name, so `SKILL-GRAFT` finds it too; the
  `XX…XX` mutant only the fakes, which ignore the name, missed.
- `_VERSION = "Version"` (4), the metadata field: `email.message.Message` looks headers up regardless of case, so
  `version` and `VERSION` read the same.
- `_WHITESPACE = re.compile(r"\s+")` (1), `_flat`'s pattern: no help text holds a run of whitespace today, so `XX\s+XX`
  collapses nothing less; kept, not dropped, as argparse's own `_split_lines` collapses runs, which the override
  replaces.

**Moved into `_TEXT` (8):** `_review_options`' description suffix and `--dry-run` help, and the two `--diff-file` helps
as `_TEXT` entries; `_diff_file_option(parser, text)` takes the text. The texts the six commands that write the lock
share are keyed by the first, `resolve` (`"resolve: review"`, `"resolve --dry-run"`, `"resolve --diff-file"`), as
`test_every_help_text_shown` finds each key's text in its command's help; `update`'s is `"update --diff-file"`. The help
output stays byte for byte the same.

**No pragma:** `_Formatter._fill_text`'s `initial_indent=indent` and `subsequent_indent=indent` (2) were first marked,
each alone on its line. The review found what the rerun showed: a pragma on an argument's line silences every mutant of
the call it sits in, `_fill_text`'s dropped `width` and `break_on_hyphens=True` among them, mutants a test kills.
argparse passes an indent other than `""` only for an argument group's description, and no parser has one, so
`_fill_text` drops the indent: it joins `_split_lines`' lines, the same text `textwrap.fill` gave. A group's description
added later would wrap unindented, which its own help shows at once.

Applied, the rerun after group 1, the pragmas still in, left 38 survivors outside `_parser` (34 there): 21 to kill, 7
mypy refuses, 10 wording. The `help` mutants of `_review_options` and `_diff_file_option` were killed, not wording:
keyed by `resolve`, their texts are in `test_every_help_text_shown`'s reach.

## Risks / Trade-offs

- \[In-process Windows test sets `sys.platform`\] → `monkeypatch` restores it, and `main` returns before importing any
  command module.
- \[`vars(args)` reads argparse's `Namespace` as a dict\] → its documented use; a `Namespace` holds only the options
  set.
- \[Dropping `*args` from `_Command`\] → a later positional caller fails at once with a `TypeError`, not silently.

## Migration Plan

None: tests and source changes that keep what a user sees.
