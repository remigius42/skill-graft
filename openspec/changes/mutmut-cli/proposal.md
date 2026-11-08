# Proposal

## Why

`mutmut-src` set up mutmut and moved `cli.py`'s help texts into `_TEXT`; `mutmut-infra` and `mutmut-commands` left their
layers with no unexplained survivor. This is `cli`'s change, the last of the four. A run of `skill_graft.cli.*` (on
`46385538`) leaves 105 of 874 mutants alive: 37 in `_parser`, usage wording `mutmut-src` triaged, and 68 others. No
in-process test notices `main` letting native Windows through, or a failed flush of stdout no longer failing a command:
the tests that would, run `skill-graft` in a subprocess, where mutmut's mutant never loads. None notices help wrapped at
70 columns whatever the terminal. No survivor is a bug.

## What Changes

- Every surviving mutant in `cli.py` outside `_parser` is killed by a test, dropped, or is known noise (a message's
  wording, a change mypy refuses), as `CONTRIBUTING.md`'s Mutation testing section sets out.
- Following its pragma rule, an equivalent mutant is dropped first: all 17 go by removing a redundancy or naming a value
  in a module-level constant (`_Command`'s unused `*args` and its `setdefault`s, `--version`'s `default`, the
  distribution name, the `Version` field, `_flat`'s pattern, `_origin`'s fallback `"{}"`, the prune check's `getattr`
  default, `_Formatter._fill_text`'s indent, which no description gets); no pragma.
- `_review_options`' and `_diff_file_option`'s help texts move into `_TEXT`, beside the others, so their 8 wording
  mutants go: `_diff_file_option` takes its help text, not a phrase to put in it.
- In-process tests, in `tests/cli/test_cli.py`, through `main`: native Windows refused; a failed flush of stdout after a
  command, `--help` and a usage error; help wrapped at the terminal's width; a git install's upper-case commit. In
  `tests/cli/test_cache.py`, beside the other prune tests: `init` prunes nothing.
- `CONTRIBUTING.md`'s baseline row for `cli`, and the total of survivors, get the new count.

## Capabilities

### New Capabilities

None: mutation testing binds the tests, not what a user sees.

### Modified Capabilities

None (`skip_specs: true`): no survivor is a bug.

## Impact

- `src/skill_graft/cli.py`: three module-level constants, `_Command`'s and `_Version`'s constructors, `_origin`'s read,
  `_main`'s prune check, the two option helpers' texts into `_TEXT`, `_fill_text` through `_split_lines`. What a user
  sees stays the same, help text included.
- `tests/cli/test_cli.py`, `tests/cli/test_cache.py`.
- `CONTRIBUTING.md`: the `cli` row of the baseline, and its total.
- No `CHANGELOG.md` entry: nothing a user sees changes.
