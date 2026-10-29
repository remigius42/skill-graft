# Design

## Context

See proposal.md for why. `errors.warnings_last` runs, in `finally`, `sys.stdout.flush()` and then `warn(warnings)`.
`cli.main` enters it inside its `try`, and its `except (SkillGraftError, OSError)` prints `skill-graft: <error>` to
stderr and returns 1. Python ignores `SIGPIPE`, so writing to a closed pipe raises `BrokenPipeError` (an `OSError`) at
the write or flush that reaches it. When the flush fails, the buffer still holds the data, so Python flushes again at
shutdown, fails again, prints `Exception ignored` and the `BrokenPipeError`, and exits 120. The wording after
`Exception ignored` varies by version (`on flushing sys.stdout` in 3.13, `while flushing sys.stdout` in 3.14); there is
no `Traceback` line. Paths that print outside `warnings_last` hit this today: `help`, `--version`, and argparse's own
`-h`/`--help`, top level and each command's. Started with stdout closed (`>&-`), Python sets `sys.stdout` to `None`:
`print` writes nowhere, and `sys.stdout.flush()` raises `AttributeError`, which `cli` does not catch.

## Goals / Non-Goals

**Goals:**

- The warnings print, the command's own error wins, and Python prints nothing of its own, whether stdout is closed
  before or during the run.

**Non-Goals:**

- Exiting quietly on a closed pipe, as tools killed by `SIGPIPE` do: skill-graft already reports it as an error when the
  output exceeds the buffer; this change makes the small-output case match, not a new policy.
- What a command has written when a `print` fails mid-run, on output larger than the pipe's buffer: `update` or an edit
  piped into `head` may stop before or after writing `skill-graft.toml` and the lock, as it does today. Output a user
  pipes into `head` is a view; the error line and exit 1 say it was cut short.
- Standard error closed: nothing would print anyway.

## Decisions

- **One `errors.flush_stdout()`**: returns at once when `sys.stdout` is `None`. Otherwise flushes; on `OSError`, points
  `sys.stdout.fileno()` at `os.devnull` (`os.dup2`, as Python's documentation recommends for `SIGPIPE`), so any later
  flush, the shutdown one included, writes nowhere and prints nothing, and re-raises.
- **One guard in `cli.main`**, around the whole command line, now `_main`: once it returns or raises `SystemExit`,
  `flush_stdout()`. A flush that fails after an exit 0 prints `skill-graft: <error>` and exits 1, as a command's error
  does; after any other exit code the error is already printed, so the code stands. The `SystemExit` is re-raised (with
  1 in place of 0 on a failed flush), so callers and tests still see argparse's exits as today. This covers `help`,
  `--version` and `-h`/`--help` without touching them, and any later path that prints. Alternative: `flush_stdout()` in
  each of `help` and `_Version`: misses argparse's `-h`, and each new path must remember it.
- **`warnings_last` flushes on its own terms**: it still flushes before the warnings, for their order. In `finally`,
  `flush_stdout()` in its own `try`; then `warn`; then, only when no exception is already in flight, raise the flush's
  error, which `cli` prints as today. An exception in flight (the command's own, or a `BrokenPipeError` from a `print`
  inside the block) propagates unchanged. Its redirect leaves the outer guard's flush nothing to fail on, so the error
  line prints once. Alternative: catching `BrokenPipeError` in `cli.main` alone: the warnings would still be lost, since
  `warnings_last`'s `finally` runs first.
- **Telling "in flight" apart** with `except BaseException: …; raise` and `else:` branches around the `yield`, not
  `sys.exc_info()` in `finally`, which also sees an exception the caller is already handling.
- **Tests**: unit tests in `tests/infra/test_errors.py` with a stdout whose `flush` raises `BrokenPipeError`, and with
  `sys.stdout` `None`. End to end in `tests/cli/test_warnings.py`, beside `test_resolve_through_a_pipe`: run
  `python -m skill_graft.cli` with stdout the write end of an `os.pipe()` whose read end is closed first, so the failure
  is deterministic, not a race with a reader, or with fd 1 closed; one test per spec scenario. The "no Python output"
  check is `Exception ignored` absent from stderr and exit 1, not 120: a `Traceback` check alone passes before the fix,
  and the rest of the message varies by version.

## Risks / Trade-offs

- \[`os.dup2` onto stdout's descriptor inside the process\] → It happens only after stdout failed and right before the
  process exits. In-process tests are another matter: under pytest's default `--capture=fd`, fd 1 is pytest's capture
  file, and an unpatched redirect would silently swallow the rest of the test's output. Every in-process test that
  reaches a failing flush patches the redirect; only the subprocess tests exercise it.

## Migration Plan

None. Rollback is reverting the branch.
