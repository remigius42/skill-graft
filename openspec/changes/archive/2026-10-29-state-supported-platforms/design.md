# Design

## Context

`cli.py` imports `commands` at load, which imports `infra/cache.py`, whose first line is `import fcntl`. On native
Windows the import fails before `main` runs, so no check inside `main` alone is reached. `cli.py` uses the command
modules only in `_main`, after parsing. Besides `commands`, it imports only the standard library and `infra/errors.py`,
which runs on Windows. CI runs pre-commit, and with it pytest, on `ubuntu-latest` only.

## Goals / Non-Goals

**Goals:**

- One error line, exit 1, on native Windows, before argparse, for every command line.
- Nothing below `cli` loaded on Windows, so no POSIX-only import there, present or future, can bring a traceback back.
- The test suite run on macOS in CI before the README or the package metadata claims macOS.

**Non-Goals:**

- Supporting native Windows: file locking, symlink creation and `O_NOCTTY` would each need a port.
- Refusing the install itself on Windows: a pure-Python wheel is `py3-none-any`, and pip honours no OS restriction.
- Other POSIX systems (BSDs, Cygwin): neither stated nor refused.
- A Windows CI job: the only Windows behavior is the refusal, which the stand-in test covers.

## Decisions

### Refuse in `main`, import the commands in `_main`

`main` refuses native Windows before `_main`: it prints
`skill-graft: native Windows is unsupported: run skill-graft in WSL` and returns 1. `_main` imports
`skill_graft.commands`' modules in its body, not `cli.py` at load, with a comment saying why. So on Windows only the
standard library and `infra/errors.py` load, and `fcntl` stays a top-level import in `cache.py`.

The platform is read into a local before it is compared (`platform = sys.platform`). mypy narrows a direct
`sys.platform == "win32"` and, on Linux, skips the branch as unreachable without saying so; through a local, it checks
the branch.

Alternatives, rejected:

- `import fcntl` inside `cache.lock`. It fixes the one import there is, but any later top-level POSIX-only import
  anywhere below `commands`, or a module-level `os.O_NOCTTY`, brings the traceback back.
- The check at the top of `cli.py`, before its imports. It runs on import (any test importing `cli`), and the imports
  after it break ruff's E402.

### The test stands in for Windows in a subprocess

A subprocess sets `sys.modules["skill_graft.commands"] = None` and, as on Windows, `sys.modules["fcntl"] = None`,
imports `skill_graft.cli`, then sets `sys.platform = "win32"` and calls `main`. Blocking the whole package fails the
test if `cli` loads any command module at import or before its check, so it covers every module below `cli`, not only
`fcntl`. `win32` comes after the import: set before, the standard library's own modules (`shutil`, `subprocess`) take
their Windows branches and fail importing a Windows-only module. One test per scenario of the spec's "Supported
platforms".

Alternative: patching `sys.platform` in process. `cli` is already imported there, so it cannot show the import works
without the commands. Rejected.

### One macOS run, on Python 3.11

`ci.yml` gains a `test-macos` job on `macos-latest`: checkout and setup-uv pinned as the other jobs pin them, then the
suite once, as the `pytest-py311` hook runs it. The Linux job already runs both the newest Python and 3.11; one macOS
run shows the platform, at a tenth of the runner minutes two would cost. Not the whole pre-commit run: its other hooks
are platform-independent.

CI runs on pull requests to `main`, not on a push to a feature branch, so the job is first seen on a draft pull request
for this branch. No new trigger.

### A file a patch empties is deleted

The macOS run showed it: `git apply` deletes a file of a plain `diff` patch only when its `+++` line carries the epoch
timestamp GNU `diff -N` writes for the missing side. With any other date, as the BSD `diff` of macOS writes, it applies
"cleanly" and leaves the file empty, without a warning (checked on Linux by rewriting only that timestamp).

For a plain `diff` patch, one with no `diff --git` line, `patch.apply` records before it the copy's regular files that
are not empty, by one `lstat` each, links not followed; after the patch applies, it deletes each of them that is now
empty, and each folder above it that this leaves empty, up to the copy, as git's own deletion does (checked: GNU `diff`
deleting a folder's only file removes the folder). Then it checks the name as before, so a deleted `SKILL.md` is
refused, as with GNU `diff`. A file empty upstream, or one a patch adds empty, is left alone. A git-format patch says in
its headers what it deletes (`deleted file mode`), and git keeps a file one empties without it (checked), so it applies
as git applies it.

Alternatives, rejected:

- Refuse a patch that empties a file, telling the user to write it with GNU `diff`. Deterministic too, but every macOS
  user must install `diffutils` before deleting a file, and the README's recipe stops working there as written.
- Rewrite the `+++` timestamp to the epoch before `git apply`. It reads `diff`'s header formats, which differ by
  platform and version.
- Parse git's output for which files it emptied: git prints nothing for it, and its messages are localized.
- Rewrite a plain patch's whole-file removal (`@@ -1,N +0,0 @@`) to `+++ /dev/null` before `git apply`, so git deletes
  the file itself. It needs a parser that counts each hunk's lines, as a removed line `-- x` reads `--- x`, like a
  header; git is that parser already.

Trade-off: a plain `diff` patch that empties a file on purpose deletes it, and a later patch in the series then creates
it. Under `diff -N` emptying and deleting are one, and an empty file in a **Skill** reaches no agent. `git diff` keeps
the two apart, and its patches apply as written. The check is per patch file: one that joins `git diff` and plain `diff`
output reads as git-format, and a BSD-written deletion in its plain part leaves the file empty. Neither recipe writes
such a file.

### The statement last

The README and the classifiers change only after the macOS job passes: stating support first would leave it untested if
the macOS task stops.

## Risks / Trade-offs

- \[The suite has never run on macOS; tests may fail there, as `/var` is `/private/var` and APFS ignores case by
  default\] → Its task fixes what fails. A failure that shows a real bug in skill-graft is fixed test-first in that
  task; one too large for it stops the change before the statement, and is raised with the user, not skipped.
- \[APFS refuses a file name that is not UTF-8 (`Illegal byte sequence`)\] → The one test building such a name skips on
  macOS: no such name can exist there to check.
- \[`apm` may be missing on the runner\] → `test_integration.py` already skips without `apm` on `PATH`; `uv run` puts
  the dev group's `apm-cli` there.
- [A function-local import is unusual in this codebase] → One, commented; `lint-imports` still sees it, so the layer
  contracts hold.
