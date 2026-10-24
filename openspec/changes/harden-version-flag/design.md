# Design

## Context

`_Version.__call__` runs inside `parser.parse_args`, before `main`'s `try`, so no handler of `main` catches what it
raises. `_origin` catches only `ValueError`. `importlib.metadata`'s `read_text` swallows a missing file but not
`ELOOP` or `EIO`; `json.loads` raises `RecursionError` on deep nesting; `metadata.distribution` raises
`PackageNotFoundError` without installed metadata. `requested_revision` and `commit_id` are only checked for being
non-empty strings.

## Goals / Non-Goals

**Goals:**

- `--version` exits 0 with one printable line for any installation.

**Non-Goals:**

- Telling the user why the origin or version is missing: `--version` reports, it does not diagnose.
- A version read some other way (`pyproject.toml`, a `__version__`): `unknown` is enough for a source checkout.

## Decisions

- **Catch named exceptions, not `Exception`.** `_origin` catches `OSError`, `ValueError` and `RecursionError` around
  the read and parse; the version lookup catches `metadata.PackageNotFoundError` and `OSError`. A bare `except` would
  hide a bug in our own code behind a shorter line. `PackageNotFoundError` is an `ImportError`, so it is named.
- **`unknown` for the version.** Keeps the `skill-graft <version>` shape a script may split on. Applies too when the
  metadata names no version (`distribution.version` is `None`) or one that is not printable, so the line stays one.
  Reverses `add-version-flag`'s "no fallback for a missing installation": running from `src/` with `PYTHONPATH` is
  rare, but a traceback for `--version` is worse than a word.
- **Printable means `str.isprintable()`.** It rejects control characters (newline, escape), format characters (bidi
  overrides, zero-width) and line separators, and keeps space; `pipeline/hidden.py` uses it the same way. A revision
  that fails drops to `(<commit>)`: the commit still pins the code. A commit that fails is as unexpected as a missing
  one, so the version only. Alternative: escape the characters (`repr`), rejected as noise in a bug report for a
  record no honest installer writes.
- **Tests run `Path(sys.executable).parent / "skill-graft"`.** The script the installer put beside the interpreter
  running the suite is the installation under test; `PATH` may lack the venv or lead elsewhere (a `uv tool` install,
  another worktree's venv). One helper in `tests/cli/test_cli.py` serves the version and help tests. The version test
  compares the first two words, `["skill-graft", metadata.version("skill-graft")]`, so `0.2.01` fails for `0.2.0`.

## Risks / Trade-offs

- \[A Windows venv names it `Scripts/skill-graft.exe`\] → CI runs the suite on Linux only; revisit with
  Windows CI.
- [A legitimate revision with a non-ASCII printable name] → kept: `isprintable()` accepts letters of any script.
