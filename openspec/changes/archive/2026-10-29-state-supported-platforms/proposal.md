# Proposal

## Why

Nothing says where skill-graft runs. It runs on Linux and, untested, on macOS. On native Windows every command, `help`,
`--help` and `--version` too, dies with a traceback ending in `ModuleNotFoundError: No module named 'fcntl'`, raised on
import by `infra/cache.py`. CI runs only on Linux, so even the macOS claim is unchecked, though the code handles
case-insensitive file systems for it.

Run on macOS, the suite showed a bug there: a **Patch** written as the README says, with `diff -ruN`, that deletes a
file leaves it in place, empty, and one deleting `SKILL.md` is not refused. `git apply` deletes a file only when its
`+++` line carries GNU `diff`'s epoch timestamp, which the BSD `diff` of macOS does not write.

## What Changes

- On native Windows every command line, `help`, `--help`, `--version` and usage errors included, prints one error line
  naming WSL and exits 1, with no traceback.
- A file a **Patch** leaves empty is deleted, whichever `diff` wrote it, so deletions work on macOS as on Linux.
- CI runs the test suite on macOS as well as Linux.
- Once it passes there, the README states the supported platforms: Linux and macOS; on Windows, through WSL. And
  `pyproject.toml` declares them as classifiers (`Operating System :: POSIX :: Linux`, `Operating System :: MacOS`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: new requirement "Supported platforms".
- `patches`: new requirement "A file a patch empties is deleted".

## Impact

- `src/skill_graft/cli.py`: `main` refuses native Windows first; `_main` imports the commands, so nothing below `cli`
  loads on Windows.
- `src/skill_graft/pipeline/patch.py`: for a plain `diff` patch, `apply` deletes each file it emptied and each folder
  that leaves empty; a `git diff` patch applies as git applies it.
- `README.md` (Installation, Writing a patch), `pyproject.toml` (classifiers), `.github/workflows/ci.yml` (a macOS test
  job).
- Tests: `tests/cli/test_cli.py` (Windows refused, in a subprocess that stands in for it),
  `tests/pipeline/test_patch.py` (deletions without GNU timestamps), `tests/cli/test_check.py` (a name APFS cannot hold,
  skipped on macOS).
- `CHANGELOG.md` at archive: `### Added` for the supported platforms, Linux and macOS, Windows through WSL; `### Fixed`
  for native Windows printing one error line in place of a traceback, and for a **Patch** written on macOS that deletes
  a file leaving it empty.
