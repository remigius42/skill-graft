# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. `pre-commit run --all-files` stays green.

## 1. Nothing to apply

- [x] 1.1 `commands/transaction.py`: `resolving` renders the lock before `if not write: return` and stores it on
  `Resolution` as `lock_text`; the lock it writes is that text. Test in `tests/commands/test_transaction.py`,
  `test_no_write_keeps_the_lock_it_would_write`: after a dry `resolving` body sets `hashes`, `resolution.lock_text`
  equals what `resolving` then writes to the lock; `test_no_write_renders_and_writes_nothing` becomes
  `test_no_write_writes_nothing`, a dry run now rendering; verify red, then green, and every `transaction`/`update` test
  stays green
- [x] 1.2 `commands/update.py`: a dry run that moves no `ref` and whose `lock_text` parses (`tomllib`) to what the lock
  file parses to prints `nothing to apply` in place of the `apply:` line; checked only when no skill is edited.
  `pipeline/lock.py`'s `read` splits into `load` (the parsed TOML, `None` if unreadable) and `recorded` (its hashes), so
  `_update` loads the lock once for both checks. Tests in `tests/commands/test_update.py`: `test_nothing_to_apply`
  (`build`, then `update mp --dry-run` at the same tip: last lines `nothing to apply`, `dry run: …`,
  `apply_line(out) == []`), `test_unrelated_push_still_applies` (tip moved, no skill changed: `hull unchanged` and an
  `apply:` line), `test_lock_out_of_date_still_applies` (a stale suggestion in the lock, no move: an `apply:` line),
  `test_lock_with_other_line_endings` (the lock rewritten with CRLF and an editor's comment line: still
  `nothing to apply`), and `test_no_apply_line_after_an_edit` also asserting no `nothing to apply`. Verify
  `test_nothing_to_apply` fails first, then all pass, and `test_apply_line` and the other `apply`/`review` tests stay
  green
- [x] 1.3 A dry run that moves no `ref` prints `<n> prose suggestion(s): run skill-graft resolve`:
  `test_dry_run_moving_no_ref_announces_suggestions`, a sibling of `test_update_announces_suggestions` that runs `build`
  first and then `update --dry-run` at the same tip (the existing test moves the tip, so it can't cover this); verify
  red, then green
- [x] 1.4 `docs/design.md`'s `update` entry names the `nothing to apply` case and the suggestions line; verify by
  reading

## 2. Hull digest placeholder

- [x] 2.1 `cli.py`: `--expect`'s metavar `hull-digest`, its help `update only if the new hull has this hull digest, …`,
  `update`'s description `--expect <hull-digest>`; `update.py`'s mismatch error `its hull digest is …`; `docs/design.md`
  and `README.md` (the example at line 82, the usage at 95 and 98) `--expect <hull-digest>`. Verified by
  `grep -rn '<digest>\|DIGEST'` over `README.md`, `docs/` and `src/` finding nothing. Test: `update --help` output holds
  `--expect hull-digest` and no `DIGEST` (`tests/cli/test_cli.py`'s `test_command_help`), and the mismatch test,
  `test_tip_moved_after_vetting`, asserts `hull digest is`; verify red, then green

## 3. Archive prep

- [x] 3.1 At archive, `CHANGELOG.md` `[Unreleased]`: under Changed, that `update --dry-run` with nothing to apply says
  `nothing to apply` in place of an `apply:` line, and its suggestion line says to run `resolve` when no `ref` moves;
  and that `--expect` names its value `<hull-digest>` (0.2.2's entry stays as released); verify by reading
