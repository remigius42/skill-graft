# Proposal

## Why

`skill-graft --version`, added by `add-version-flag`, breaks its own spec: it must not fail and must print one line,
yet it dies with a traceback on an unreadable `direct_url.json` or a missing installation, and prints the installer's
`requested_revision` raw, newlines and terminal escapes included. Its end-to-end tests run whichever `skill-graft` comes
first on `PATH`, not the one under test.

## What Changes

- `--version` never fails: a `direct_url.json` that cannot be read (a symlink loop, a disk error) or is nested too
  deeply to parse adds nothing, as a malformed one already does; without installed metadata, or with metadata that
  cannot be read or names no version, it prints `skill-graft unknown`. Reverses `add-version-flag`'s "no fallback for
  a missing installation".
- A revision holding a character that is not printable (a newline, an escape) is dropped: `(<commit>)`. A commit
  holding one adds nothing.
- The end-to-end tests in `tests/cli/test_cli.py` run the `skill-graft` script beside the interpreter running the
  suite, and the version test compares the whole version, not a prefix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `cli`: the Version requirement drops a revision or commit that is not printable; a new requirement says what
  `--version` prints on a damaged or missing installation.

## Impact

- `src/skill_graft/cli.py`: `_Version` and `_origin`.
- `tests/cli/test_cli.py`.
- `CHANGELOG.md` at archive: `--version` is unreleased, so its `### Added` entry gains `skill-graft unknown`; no
  `### Fixed` entry for a bug no release shipped.
