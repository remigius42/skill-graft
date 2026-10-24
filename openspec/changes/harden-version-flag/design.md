# Design

## Context

`_Version.__call__` runs inside `parser.parse_args`, before `main`'s `try`, so no handler of `main` catches what it
raises. `_origin` catches only `ValueError`. `importlib.metadata`'s `read_text` swallows a missing file but not
`ELOOP` or `EIO`; `json.loads` raises `RecursionError` on deep nesting; `metadata.distribution` raises
`PackageNotFoundError` without installed metadata; `distribution.version` raises `UnicodeDecodeError` on a METADATA
that is not UTF-8, and on 3.12+ warns that a missing `Version` will raise `KeyError`. `requested_revision` and
`commit_id` are only checked for being non-empty strings.

## Goals / Non-Goals

**Goals:**

- `--version` exits 0 with one line of printable ASCII for any installation, whatever the terminal's encoding.

**Non-Goals:**

- Telling the user why the origin or version is missing: `--version` reports, it does not diagnose.
- A version read some other way (`pyproject.toml`, a `__version__`): `unknown` is enough for a source checkout.
- Code run from `src/` beside another installed skill-graft: `importlib.metadata` finds that installation and reports
  its version. Checking that the distribution owns the running module is a developer's edge case, not a user's.

## Decisions

- **Catch named exceptions, not `Exception`.** `_origin` catches `OSError`, `ValueError` and `RecursionError` around
  the read and parse; the version lookup catches `metadata.PackageNotFoundError`, `OSError` and `ValueError`
  (`UnicodeDecodeError`). A bare `except` would hide a bug in our own code behind a shorter line.
  `PackageNotFoundError` is an `ImportError`, so it is named.
- **Index `Version` only when `"Version" in distribution.metadata`.** `distribution.version` indexes the metadata,
  which CPython deprecates for a missing key and will make a `KeyError`. The typed `PackageMetadata` protocol has no
  `.get`, but has `__contains__`.
- **`unknown` for the version, origin kept.** Keeps the `skill-graft <version>` shape a script may split on. Applies
  when no distribution is found, its metadata cannot be read or decoded, or its version is missing or not printable
  ASCII. When the distribution was found, `_origin` still runs: the commit is what a bug report needs most. Reverses
  `add-version-flag`'s "no fallback for a missing installation": running from `src/` with `PYTHONPATH` is rare, but a
  traceback for `--version` is worse than a word.
- **A revision must be printable ASCII** (`isascii() and isprintable()`). It rejects control characters (newline,
  escape), format characters (bidi overrides, zero-width), and anything a non-UTF-8 standard output cannot encode, so
  `print` cannot raise `UnicodeEncodeError`. One that fails drops to `(<commit>)`: the commit still pins the code.
  Alternatives: escape the characters (`repr`), noise in a bug report for a record no honest installer writes; or
  print with `errors="backslashreplace"`, which keeps non-ASCII names but adds a second write path for a rare case.
- **A commit must match `[0-9a-fA-F]{7,}`.** PEP 610's `commit_id` is a hash; anything else (`abc) x`) would break the
  `(<revision> @ <commit>)` shape. One that fails is as unexpected as a missing one, so the version only.
- **Tests run the script in `sysconfig.get_path("scripts")`.** That is where the installer put `skill-graft` for the
  interpreter running the suite, in a venv or a system scheme; `PATH` may lack it or lead elsewhere (a `uv tool`
  install, another worktree's venv). One helper in `tests/cli/test_cli.py` serves the version and help tests. The
  version test compares the first two words, `["skill-graft", metadata.version("skill-graft")]`, so `0.2.01` fails
  for `0.2.0`.

## Risks / Trade-offs

- [A real branch or tag with a non-ASCII name] → shows as `(<commit>)`; the commit identifies the code, and the
  user typed the name.
- \[A `pip install --user` puts scripts in the user scheme, not `get_path("scripts")`\] → the suite runs from the
  project's venv, where both agree.
- \[A Windows venv names it `skill-graft.exe`\] → CI runs the suite on Linux only; revisit with Windows CI.
