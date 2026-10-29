# Proposal

## Why

`warnings_last` flushes standard output before it prints the warnings. When the reader has already closed it
(`skill-graft tree | head -1`), the flush raises `BrokenPipeError`, so no warning prints and a command's own error is
replaced by `[Errno 32] Broken pipe`. Python then prints `Exception ignored` and the `BrokenPipeError` at exit, and
exits 120. In v0.2.2, where nothing flushes before exit, that is the whole outcome whenever the output fits the pipe's
buffer; on `main` it still is for `help`, `--version` and `--help`. Started with standard output closed (`>&-`), a
command's flush raises `AttributeError`, and the user gets a traceback.

## What Changes

- A command whose standard output is closed early still prints its warnings, then its error line.
- A command that failed for its own reason reports that error, not the closed output.
- A command that would otherwise succeed fails with exit 1 and the `Broken pipe` error line, as it already does when its
  output exceeds the pipe's buffer.
- `help`, `--version` and `--help`, which print outside any command, behave the same: the error line and exit 1.
- Python prints nothing of its own (`Exception ignored …`), and no exit 120.
- A command started with standard output closed prints its warnings and exits as it would otherwise, without a
  traceback.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: new requirement "Closed standard output".

## Impact

- `src/skill_graft/infra/errors.py`: `flush_stdout`, used by `warnings_last`.
- `src/skill_graft/cli.py`: `main` flushes through it once the command line returns or exits.
- Tests: `tests/infra/test_errors.py` (new), `tests/cli/test_warnings.py` (end to end, through a closed pipe and a
  closed fd 1, and `main` in process on a closed stdout), `tests/conftest.py` (the closed-stdout double, shared).
- `CHANGELOG.md` at archive: `### Fixed` for the `Exception ignored` and exit 120 that v0.2.2 shows. The lost warnings
  and the masked error never shipped: they came with the unreleased "warnings last", so they get no entry of their own.
