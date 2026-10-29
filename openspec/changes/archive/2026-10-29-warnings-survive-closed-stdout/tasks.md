# Tasks

Apply with the `mp-tdd` skill: each task red-green-refactor, one commit. `pre-commit run --all-files` stays green.

## 1. Flush on its own terms

- [x] 1.1 Tests in a new `tests/infra/test_errors.py`, with the redirect to `os.devnull` patched: with `sys.stdout`
  replaced by one whose `flush` raises `BrokenPipeError`, a block that succeeds prints its warnings, then raises the
  flush's error; a block raising `SkillGraftError` prints its warnings and raises that error, not the flush's; the
  redirect runs once in both. With `sys.stdout` `None`, or closed, a block prints its warnings and raises nothing. With
  a `_discard` that fails, the flush's error is raised still; the real `_discard` on a stdout without a file descriptor
  leaks none. The double, `closed_stdout()` and the `discards` fixture go in `tests/conftest.py`. Verify they fail
  first, then make `warnings_last` pass them as design.md says, through a new `errors.flush_stdout()`
- [x] 1.2 `cli.main` guards `_main` with `errors.flush_stdout()` as design.md says; covered end to end by 1.3's "Help,
  version and argparse's help" tests, written first and failing, and, for a `print` that fails itself (`--version`), by
  an in-process test of `main` on the closed-stdout double in `tests/cli/test_warnings.py`. `tests/cli/test_cli.py`'s
  `SystemExit` tests pass unchanged
- [x] 1.3 End to end in `tests/cli/test_warnings.py`, one test per scenario of the cli spec's "Closed standard output":
  `python -m skill_graft.cli` with the scenario's arguments and stdout the write end of an `os.pipe()` whose read end is
  closed first, or fd 1 closed for "Closed from the start"; assert stderr's order (warning, then error line), which
  error it names, no `Exception ignored`, and the exit code. Verify "No Python output" fails before 1.1's fix (revert it
  locally) and all pass after
